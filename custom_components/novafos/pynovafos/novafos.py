'''
Primary public module for novafos.dk API wrapper.
'''
from __future__ import annotations

from datetime import datetime
from datetime import timedelta
from zoneinfo import ZoneInfo
import logging
import json
import requests
import hashlib
import re
import string
import random
import base64
import uuid

_LOGGER = logging.getLogger(__name__)

class LoginFailed(Exception):
    """"Exception class for bad credentials"""

class HTTPFailed(Exception):
    """Exception class for API HTTP failures"""

class Novafos:
    '''
    Primary exported interface for KMD API wrapper.
    '''
    def __init__(self, username, password, supplierid):
        self._username = username  #TODO: REMOVE
        self._password = password  #TODO: REMOVE
        self._supplierid = supplierid #TODO: REMOVE
        self._api_url = "https://easy-energy-plugin-api.kmd.dk"
        self.tz = ZoneInfo("Europe/Copenhagen")

        self._access_token = ""
        self._customer_id = ""
        self._customer_number = ""
        self._active_meters = []
        self._meter_data = {}
        self._last_valid_day = None

        # NOTE: Added because of reCAPCTHA login screen
        self._access_token_date_updated = ""

        # Zoom level is the granuarity of the retrieved data
        self._zoom_level = {
         "Year"    : 0,
         "Month"   : 1,
         "Day"     : 2,
         "Hour"    : 3,
         "Billing" : 4
        }

    def _print_json(self, map, context="JSON dump"):
        _LOGGER.debug("%s:\n %s", context, json.dumps(map, indent=4, sort_keys=True, ensure_ascii=False))

    def authenticate_using_access_token(self, access_token, access_token_date_updated):
        """ The only reason for this function is due to to a reCAPTCHA challenge on the Novafos login page.
            The date is used to verify the token is not too old when getting data.
        """
        self._access_token_date_updated = access_token_date_updated
        # Make a simple validation of the access_token length and only update if it has the correct length
        if len(access_token) >= 1200:
            self._access_token = "Bearer "+access_token
        else:
            self._access_token = ""
            _LOGGER.error(f"Token update does not seem to have a valid length. Please check again. (This message is normal the first time the integration starts)")
            return False
        _LOGGER.debug("Access token set to: '%s' at date: '%s'", self._access_token, self._access_token_date_updated)

        # Check token age
        now = datetime.now()
        # Allow 45 minutes since the last token update.  If updating after this point, disallow API accesses.
        if self._access_token == "" or datetime.strptime(self._access_token_date_updated, '%Y-%m-%dT%H:%M:%S') + timedelta(minutes=45) < now:
            _LOGGER.debug("Access_token too old or not set correctly while authenticating")
            return False
        else:
            # Configure other data necessary for fetching data
            self._get_customer_id()
            self._get_active_meters()
            return True

    def _get_customer_id(self):
        # Need to retrieve the customer ID from the user profile to fetch data.
        headers = {
            'Authorization': self._access_token,
        }

        url = f'{self._api_url}/api/profile/get'

        response = requests.get(url, headers=headers)        
        #self._print_json(response.json(), "Retrieved customer ID JSON response")
        self._customer_id = f"{response.json()['Customers'][0]['Id']}"
        self._customer_number = f"{response.json()['Customers'][0]['Number']}"
        _LOGGER.debug("Retrieved customer_id, number: %s, %s", self._customer_id, self._customer_number)

    def _get_active_meters(self):
        """
        The returned data is a list of installations:
        [{'InstallationPeriodId': <int>,
          'InstallationId': <int>,     <--- this one is important
          'LocationId': <int>, 
          'Location': '<str>', 
          'MeasurementPointId': <int>,  <--- this one is important
          'MeasurementPointType': '', 
          'MeasurementPointNumber': '<str>', 
          'MeterId': <int>,
          'ConsumptionTypeId': 6,          <--- '6'=water, '5'=heating
          'ConsumptionTypeName': 'Vand',   <--- might want to ensure we are looking at water too
          'IsRemoteRead': True, 
          'IsActive': True,                <--- Check this one for True
          'MeterNumber': '<int>', 
          'MeterTypeId': <int>, 
          'MeasurementPointTypeCodeText': '', 
          'Units': [{'Id': <int>,          <-- need to save this dict as well, Id as minimum
                     'Name': 'm³', 
                     'Description': 'Vand',
                     'Decimals': 0, 
                     'Order': 1
                    }]
        }]
        """
        headers = {
            'Customer-Id': self._customer_id,
            'Customer-Number': self._customer_number,
            "Authorization" : self._access_token
        }

        data = {
            "IncludeUnits":"true"
        }

        url = f"{self._api_url}/api/meter/customerActiveMeters"

        response = requests.post(url, data=data, headers=headers)
        # NOTE: Failure may happen right here whenever the API is updated with new headers and what not.
        #self._print_json(response.json(), "Get active meters response")

        response_json = response.json()
        self._active_meters = []
        for meter in response_json:
            """ Pick up active water measuring meters """
            if meter["IsActive"] == True and meter["ConsumptionTypeId"] == 6:
                # Water type
                active = {
                    "type": "water",
                    "InstallationId" : meter["InstallationId"],
                    "MeasurementPointId" : meter["MeasurementPointId"],
                    "Unit" : meter["Units"][0],
                }
                self._meter_data['water'] = {}
                self._active_meters.append(active)
            if meter["IsActive"] == True and meter["ConsumptionTypeId"] == 5:
                # Heating type
                active = {
                    "type": "heating",
                    "InstallationId" : meter["InstallationId"],
                    "MeasurementPointId" : meter["MeasurementPointId"],
                    "Unit" : meter["Units"][0],
                }
                self._meter_data['heating'] = {}
                self._active_meters.append(active)
        _LOGGER.debug('Got active (water/heating) meters : %s', self._active_meters)

    def _get_consumption_timeseries(self, metering_device, dateFrom, dateTo, zoomLevel = 0):
        """Get the timeseries as requested for a single metering device, based on zoom level and date range.

        Zoomlevel:
         0 : Year
         1 : Month
         2 : Day
         3 : Hour
         4 : Billing Period

         Example:
         {'SheetName': None, 
          'Series': [
            {'Data': [
                {'DateFrom': '2022-01-10T00:00:00+01:00', 
                 'DateTo': '2022-01-10T23:59:59+01:00', 
                 'Value': 0.344,  <--- has accurate measurement registered
                 'UnitName': 'm³', 
                 'Label': '', 
                 'IsComplete': True, <--- this one is complete
                 'IsSettlement': False
                },
                {'DateFrom': '2022-01-11T00:00:00+01:00', 
                 'DateTo': '2022-01-11T23:59:59+01:00', 
                 'Value': 0.01,   <--- has one measurement registered
                 'UnitName': 'm³', 
                 'Label': '', 
                 'IsComplete': False,  <--- but is incomplete!  This is ignored in the web interface. Data is displayed regardless.
                 'IsSettlement': False
                },
                {'DateFrom': '2022-01-12T00:00:00+01:00',
                 'DateTo': '2022-01-12T23:59:59+01:00', 
                 'Value': 0.0,   <--- no measurements
                 'UnitName': 'm³', 
                 'Label': '', 
                 'IsComplete': False,  <--- and incomplete.  This is ignored in the web interface. Data is displayed regardless.
                 'IsSettlement': False
                }],
             'Label': None
            }
         ],
         'Total': {
             'Value': 0.354, 
             'DateFrom': '2022-01-10T01:00:00+01:00', 
             'DateTo': '2022-01-15T00:00:00+01:00'
             }, 
         'Average': {
             'Value': 0.344, 
             'DateFrom': '2022-01-10T00:00:00+01:00', 
             'DateTo': '2022-01-10T23:59:59+01:00'
             }, 
         'Maximum': {
             'Value': 0.344, 
             'DateFrom': '2022-01-10T00:00:00+01:00', 
             'DateTo': '2022-01-10T23:59:59+01:00'
             },
         'Minimum': {
             'Value': 0.344, 
             'DateFrom': '2022-01-10T00:00:00+01:00', 
             'DateTo': '2022-01-10T23:59:59+01:00'
             }
        }

        The returned data is flattened a little to only take the first data series for each meter.
        I don't know why this could be a list, so please report a bug or a pull request with a fix
        if this is not the case for you.

        Returned data has this structure:
        [
            {
                "type" : "water|heating" (so far),
                "Data" : []
                "Total": float,
                ...
            },
            ...
        ]
        """
        headers = {
            'Customer-Id': self._customer_id,
            'Customer-Number': self._customer_number,
            "Authorization" : self._access_token
        }

        # Setup query parameters for the API.
        # Necessary fields are installation relevant properties and the date/zoom range.
        data = {
            "InstallationId": metering_device["InstallationId"],
            "MeasurementPointId": metering_device["MeasurementPointId"],
            "Unit": metering_device["Unit"],
            "ZoomLevel": zoomLevel,
            "PriceData":"false", #optional
            "Interval": "PT1H",
            "DateFrom": dateFrom,
            "DateTo": dateTo,
        }

        url = f"{self._api_url}/api/consumption/consumptionTimeSeries"

        response = requests.post(url, json=data, headers=headers)
        result_json = response.json()

        # Enable logging DEBUG to see all returned data from the API:
        self._print_json(result_json, "Retrieved timeseries JSON response")

        # Clean data so only valid data is returned and register the valid date
        series_data = []
        last_valid_date = ""
        if result_json["Series"]:
            for data in result_json["Series"][0]["Data"]:
                # Add data - complete or not!
                series_data.append({
                    "DateFrom" : data["DateFrom"],
#                    FIXME: Not needed
#                    "DateTo" : data["DateTo"],
                    "Value" : data["Value"]
                })
                # NOTE: Assuming data is sorted by date - which it is
                last_valid_date = data["DateTo"]

        # Return first data series.  Unknown how more series could come from a single metering device?
        meter_data = {
            "type" : metering_device['type'],
            "Data" : series_data,
            "Total" : result_json["Total"],
            "Average": result_json["Average"],
            "Maximum": result_json["Maximum"],
            "Minimum": result_json["Minimum"],
            "LastValidDate" : last_valid_date
            }
        _LOGGER.debug(f"Retrieved data from API: {meter_data}")
        return meter_data

    def _get_all_consumption_timeseries(self, dateFrom, dateTo, zoomLevel = 0):
        """ Retrieve data from all active metering devices """
        meter_data = []
        for active_meter in self._active_meters:
            meter_data.append(self._get_consumption_timeseries(active_meter, dateFrom, dateTo, zoomLevel))
        return meter_data

    def _get_year_data(self):
        dateFrom = datetime.now().replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        dateTo = datetime.now().replace(month=12, day=31, hour=23, minute=59, second=59, microsecond=0).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        _LOGGER.debug(f"Getting Year data from {dateFrom} to {dateTo}")
        time_series = self._get_all_consumption_timeseries(dateFrom=dateFrom, dateTo=dateTo, zoomLevel=self._zoom_level['Year'])

        for series in time_series:
            type = series.pop('type')
            self._meter_data[type]["year"] = series

            if self._last_valid_day:
                self._meter_data[type]["year"]["LastValidDate"] = self._last_valid_day

            if series['Data']:
                #_LOGGER.debug(json.dumps(time_series, sort_keys = False, indent = 4))
                _LOGGER.debug(f"Year Total for {type}: {series['Total']['Value']}")
            else:
                _LOGGER.warning("The KMD API returned no yearly data.  Expect sensors to signal 'unavailable'")

    def _get_month_data(self):
        # These get all months of the year
        #dateFrom = datetime.now().replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        #dateTo = datetime.now().replace(month=12, hour=0, minute=0, second=0, microsecond=0).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        # Get just the current month
        now = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        dateFrom = now.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        dateTo = (now.replace(now.year + int(now.month/12), now.month%12+1, 1)-timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S.000Z")

        _LOGGER.debug(f"Getting Month data from {dateFrom} to {dateTo}")
        time_series = self._get_all_consumption_timeseries(dateFrom=dateFrom, dateTo=dateTo, zoomLevel=self._zoom_level['Month'])

        for series in time_series:
            type = series.pop('type')
            self._meter_data[type]["month"] = series

            if self._last_valid_day:
                self._meter_data[type]["month"]["LastValidDate"] = self._last_valid_day

            #_LOGGER.debug(json.dumps(time_series, sort_keys = False, indent = 4))
            if series['Data']:
                for month_data in series['Data']:
                    #FIXME remove _LOGGER.debug(f"{type} {month_data['DateFrom']} - {month_data['DateTo']} - {month_data['Value']}")
                    _LOGGER.debug(f"{type} {month_data['DateFrom']} - {month_data['Value']}")
                _LOGGER.debug(f"Month Total/Avg/Min/Max for {type}: {series['Total']['Value']} / {series['Average']['Value']} / {series['Minimum']['Value']} / {series['Maximum']['Value']}")
            else:
                _LOGGER.warning("The KMD API returned no monthly data.  Expect sensors to signal 'unavailable'")

    def _get_day_data(self):
        now = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        dateFrom = now.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        dateTo = (now.replace(now.year + int(now.month/12), now.month%12+1, 1)-timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        _LOGGER.debug(f"Getting Day data from {dateFrom} to {dateTo}")
        time_series = self._get_all_consumption_timeseries(dateFrom=dateFrom, dateTo=dateTo, zoomLevel=self._zoom_level['Day'])

        for series in time_series:
            type = series.pop('type')
            self._meter_data[type]["day"] = series

            #self._last_valid_day = self._meter_data["day"]["Data"][-1]["DateFrom"]
            self._last_valid_day = self._meter_data[type]["day"]["LastValidDate"]

            #_LOGGER.debug(json.dumps(time_series, sort_keys = False, indent = 4))
            if series['Data']:
                for day_data in series['Data']:
                    # FIXME: remove _LOGGER.debug(f"{type} {day_data['DateFrom']} - {day_data['DateTo']} - {day_data['Value']}")
                    _LOGGER.debug(f"{type} {day_data['DateFrom']} - {day_data['Value']}")
                _LOGGER.debug(f"Day Total/Avg/Min/Max/ValidDate for {type}: {series['Total']['Value']} / {series['Average']['Value']} / {series['Minimum']['Value']} / {series['Maximum']['Value']} / {self._last_valid_day}")
            else:
                _LOGGER.warning("The KMD API returned no daily data.  Expect sensors to signal 'unavailable'")

    def _local_to_utc(self, local_time):
        """ Convert a local time to UTC time including timezone and summer(DST)/winter time ofsets. """
        local_time_with_timezone = local_time.astimezone(self.tz)
        utc_offset = local_time_with_timezone.utcoffset()
        return local_time.astimezone(ZoneInfo("UTC")) - utc_offset

    def _local_str_to_utc_str(self, local_time_str):
        """ Convert a local ISO time string to UTC time strimg."""
        return self._utc_to_isostr(self._local_to_utc(local_time_str.fromisoformat()))

    def _utc_to_isostr(self, utc_time):
        return utc_time.isoformat().replace("+00:00", "Z")

    def _get_hour_data(self, days_back = None, from_date = None):
        """
        If days_back is set, the function returns valid data this many days back.  A 1 could result in no valid data returned.
           If it is not set, data returned is from the last valid day.

        from_date can be set instead to the day in the month from which to start getting data.  All days until present day will be retrieved.
           this is a datetime object with timezone data
        """
        # from_date_input =  datetime.fromtimestamp(1736002800.0).replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=274)
        # end_date_input = from_date_input.replace(hour=23, minute=59, second=59, microsecond=0)
        # from_date = _to_utc(from_date_input).isoformat().replace("+00:00", "Z")
        # end_date  = _to_utc(end_date_input).isoformat().replace("+00:00", "Z")        

        # End date is always present time
        end_date_input = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        if days_back:
            from_date_input = end_date_input - timedelta(days=days_back)
        elif from_date:
            from_date_input = from_date.replace(hour=0, minute=0, second=0, microsecond=0)
            days_back = (end_date_input - from_date_input).days
        duration = range(days_back)

        # TEMPORARY
        #self._meter_data['water'] = { 'hour': { 'Data': [], 'Maximum':{'Value':0}, 'Minimum':{'Value':0}, 'Average':{'Value':0}, 'Total':{'Value':0}}}
        #_LOGGER.debug(f"{self._meter_data} {list(duration)}")
        #### ^^^

        first_day = [True] * len(self._meter_data)
        for day in duration:
            # "DateFrom":"2024-03-31T22:00:00.000Z", "DateTo":"2024-04-02T21:59:59.999Z",  <- sommertid
            # "DateFrom":"2024-10-27T23:00:00.000Z", "DateTo":"2024-10-28T22:59:59.999Z"   <- vintertid
            now = from_date_input + timedelta(days=day)
            dateFrom = self._utc_to_isostr(self._local_to_utc(now))
            dateTo   = self._utc_to_isostr(self._local_to_utc(now.replace(hour=23, minute=59, second=59, microsecond=0)))
            _LOGGER.debug(f"\nGetting Hour data {days_back-day} day(s) back in time from {dateFrom} to {dateTo}")

            time_series = self._get_all_consumption_timeseries(dateFrom=dateFrom, dateTo=dateTo, zoomLevel=self._zoom_level['Hour'])

            for idx, series in enumerate(time_series):
                type = series.pop('type')

                if first_day[idx]:
                    self._meter_data[type]['hour'] = series
                    first_day[idx] = False
                elif series['Data']:
                    # If the dataset returned is not empty, move the valid date and mix/max/avg data forward.
                    # That will ensure the dataset reflects the latest values in case they are >24h old
                    self._meter_data[type]['hour']['Data'] = self._meter_data[type]['hour']['Data'] + series['Data']
                    self._meter_data[type]['hour']['Total'] = series['Total']
                    self._meter_data[type]['hour']['Average'] = series['Average']
                    self._meter_data[type]['hour']['Maximum'] = series['Maximum']
                    self._meter_data[type]['hour']['Minimum'] = series['Minimum']
                    self._meter_data[type]['hour']['LastValidDate'] = series['LastValidDate']

                #_LOGGER.debug(json.dumps(time_series, sort_keys = False, indent = 4))
        for key, series_type in self._meter_data.items():
            if 'hour' in series_type:
                for hour_data in series_type['hour']['Data']:
                    #FIXME: remove _LOGGER.debug(f"{hour_data['DateFrom']} - {hour_data['DateTo']} - {hour_data['Value']}")
                    _LOGGER.debug(f"{hour_data['DateFrom']} - {hour_data['Value']}")
                _LOGGER.debug(f"Total/Avg/Min/Max: {series_type['hour']['Total']['Value']} / {series_type['hour']['Average']['Value']} / {series_type['hour']['Minimum']['Value']} / {series_type['hour']['Maximum']['Value']}")
            #else:
            #    _LOGGER.warning("The KMD API returned no hourly data.  Expect sensors to signal 'unavailable'")

    def get_meter_types(self):
        return self._active_meters

    def get_statistics(self, from_date):
        """ Retrieve statistics data.  Plainly retrieve hourly consumption data since some date.
            Assumes authentication already completed.
            TODO:  Eventually this should replace the get_latest() function and only a single sensor should be exported
        """
        # Fetch each day must be individually because the server only returns values one day at a time.
        # It seems Novafos has valid data varying from 5 days in the past to yesterday.
        self._get_hour_data(from_date=from_date)

        # Lastly make an entry for the last valid day in the dataset.  Maybe someone can use this.
        # NOTE: (relies on _get_day_data() having been called!)
        self._meter_data['water']["valid_date"] = {}
        self._meter_data['water']["valid_date"]["Value"] = self._last_valid_day
        if 'heating' in self._meter_data:
            self._meter_data['heating']["valid_date"] = {}
            self._meter_data['heating']["valid_date"]["Value"] = self._last_valid_day

        # TODO: simply data fetch as 'hour' is the only one needed eventually
        statistics = { 'water' : self._meter_data['water']['hour']['Data'] }
        if 'heating' in self._meter_data:
            statistics['heating'] = self._meter_data['heating']['hour']['Data']

        _LOGGER.debug(f"Statistics: {statistics}")
        return statistics

    def get_dummy_data(self):
        _LOGGER.debug("Returning dummy data")
        now = datetime.now()
        dateTo =  now.strftime("%Y-%m-%dT%H:%M:%S+00:00")
        dateTwo =  now.strftime("%Y-%m-%dT%H:%M:%S")
        return {
            'water' : {
                'day': {
                    'Data': [
                        {'DateFrom': None, 'DateTo': None, 'Value': None},
                    ],
                    'Total':   {'Value': None, 'DateFrom': None, 'DateTo': None},
                    'Average': {'Value': None, 'DateFrom': None, 'DateTo': None},
                    'Maximum': {'Value': None, 'DateFrom': None, 'DateTo': None},
                    'Minimum': {'Value': None, 'DateFrom': None, 'DateTo': None},
                    'LastValidDate': dateTo
                },
                'year': {
                    'Data': [
                        {'DateFrom': None, 'DateTo': None, 'Value': None}
                    ],
                    'Total':   {'Value': None, 'DateFrom': None, 'DateTo': None},
                    'Average': {'Value': None, 'DateFrom': None, 'DateTo': None},
                    'Maximum': {'Value': None, 'DateFrom': None, 'DateTo': None},
                    'Minimum': {'Value': None, 'DateFrom': None, 'DateTo': None},
                    'LastValidDate': dateTo
                },
                'month': {
                    'Data': [
                        {'DateFrom': None, 'DateTo': None, 'Value': None}
                    ],
                    'Total':   {'Value': None, 'DateFrom': None, 'DateTo': None},
                    'Average': {'Value': None, 'DateFrom': None, 'DateTo': None},
                    'Maximum': {'Value': None, 'DateFrom': None, 'DateTo': None},
                    'Minimum': {'Value': None, 'DateFrom': None, 'DateTo': None},
                    'LastValidDate': dateTo
                },
                'hour': {
                    'Data': [
                        {'DateFrom': None, 'DateTo': None, 'Value': None},
                    ],
                    'Total':   {'Value': None, 'DateFrom': None, 'DateTo': None},
                    'Average': {'Value': None, 'DateFrom': None, 'DateTo': None},
                    'Maximum': {'Value': None, 'DateFrom': None, 'DateTo': None},
                    'Minimum': {'Value': None, 'DateFrom': None, 'DateTo': None},
                    'LastValidDate': dateTwo
                },
                'valid_date': {'Value': dateTo }
            }
        }

    def get_latest(self):
        # NOTE: This part is all due to login screen reCAPTCHA down to ^^
        now = datetime.now()
        # Allow 45 minutes since the last token update.  If updating after this point, return dummy data.
        if self._access_token == "" or datetime.strptime(self._access_token_date_updated, '%Y-%m-%dT%H:%M:%S') + timedelta(minutes=45) < now:
            return self.get_dummy_data()
        ###^^^^^

        # NOTE: Returned is the first element in the meters list.
        #       This works for people with one water meter.
        #       If this is a problem, file a feature extension or a pull request to fix.
        #       Look for "time_series[0]"
        # Next up retrieve data series for:
        # - valid days in this month
        #  Daily data can be fetched across years
        #  Total/min/max/avg consumption is calculated over the fetched dataset
        #  This also set the self._last_valid_day field
        self._get_day_data()

        # - year to date
        self._get_year_data()

        # - this month
        self._get_month_data()

        # - valid hours for the last valid day
        # Each day must be fetched individually because the server only returns values from the FromDate day.
        # It seems Novafos has valid data varying from 5 days in the past to yesterday.
        # This one retrieves data from the first day in the month.
        #self._get_hour_data(from_date=datetime.now().replace(day=1))
        # This one retrieves data 'days_back' days back
        self._get_hour_data(days_back=1)

        # Lastly make an entry for the last valid day in the dataset.  Maybe someone can use this.
        self._meter_data['water']["valid_date"] = {}
        self._meter_data['water']["valid_date"]["Value"] = self._last_valid_day
        if 'heating' in self._meter_data:
            self._meter_data['heating']["valid_date"] = {}
            self._meter_data['heating']["valid_date"]["Value"] = self._last_valid_day

        return self._meter_data
