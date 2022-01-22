'''
Primary public module for novafos.dk API wrapper.
'''
from datetime import datetime
from datetime import timedelta
import requests
import logging

_LOGGER = logging.getLogger(__name__)

class Novafos:
    '''
    Primary exported interface for KMD API wrapper.
    '''
    def __init__(self, username, password, supplierid):
        self._username = username
        self._password = password
        self._supplierid = supplierid
        self._auth_url = f'https://webtools.kmd.dk/'
        self._api_url = "https://minforsyningplugin2webapi.kmd.dk/"

        self._session_id = ""
        self._access_token = ""
        self._active_meters = []
        self._meter_data = {}
        self._last_valid_day = None

        """
        Zoom level is the granuarity of the retrieved data
        """
        self._zoom_level = {
         "Year"    : 0,
         "Month"   : 1,
         "Day"     : 2,
         "Hour"    : 3,
         "Billing" : 4
        }

    def _get_session_id(self):
        """
        Use the username/password/supplierid credentials to login and get a sesion ID.
        """
        headers = {"Session-Id":"",
                   "Customer-Database-Number":self._supplierid,
                   "Content-Type":"application/x-www-form-urlencoded; charset=UTF-8"
                  }
        data = {"username":self._username,
                "password":self._password,
                "rememberLogin":"false"
               }
        url = f"{self._auth_url}/wts/loginUserPassword"

        result = requests.post(url, data=data, headers=headers)
        result_json = result.json()
        self._session_id = result_json['sessionId']
        _LOGGER.debug(f"Got session_id (supplierid and user/pass was ok): {self._session_id}")

    def _get_bearer_token(self):
        headers = {
        #        "Accept":"application/json, text/plain, */*"
        }

        data = {
            "grant_type":"WTSession",
            "WTSessionId":self._session_id
        }

        url = f"{self._api_url}/token"

        result = requests.post(url, data=data, headers=headers)
        result_json = result.json()
        self._access_token = f"{result_json['token_type']} {result_json['access_token']}"
        _LOGGER.debug(f"Got bearer token (access to API was Ok): {self._access_token}")

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
          'ConsumptionTypeId': 6,          <--- is '6' water?
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
            "Authorization" : self._access_token
        }

        data = {
            "IncludeUnits":"true"
        }

        url = f"{self._api_url}/api/meter/customerActiveMeters"

        result = requests.post(url, data=data, headers=headers)
        result_json = result.json()
        self._active_meters = []
        for meter in result_json:
            """ Pick up active water measuring meters """
            if meter["IsActive"] == True and meter["ConsumptionTypeId"] == 6:
                active = {
                    "InstallationId" : meter["InstallationId"],
                    "MeasurementPointId" : meter["MeasurementPointId"],
                    "Unit" : meter["Units"][0],
                }
                self._active_meters.append(active)

    def _get_consumption_timeseries(self, dateFrom, dateTo, zoomLevel = 0):
        """Get the timeseries as requested for all meters, based on zoom level and date range.

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
                 'IsComplete': False,  <--- but is incomplete!
                 'IsSettlement': False
                },
                {'DateFrom': '2022-01-12T00:00:00+01:00',
                 'DateTo': '2022-01-12T23:59:59+01:00', 
                 'Value': 0.0,   <--- no measurements
                 'UnitName': 'm³', 
                 'Label': '', 
                 'IsComplete': False,  <--- and incomplete
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
        """
        headers = {
            "Authorization" : self._access_token
        }

        meter_data = []
        for active_meter in self._active_meters:
            # Merge meter data with date range. Commented lines comes from the active_meters dict.
            # active_meters add the following necessary fields:
            #  MeasurementPointId, InstallationId, Unit
            data = {
                **active_meter,
                "ZoomLevel": zoomLevel,
                "PriceData":"false", #optional
                "DateFrom": dateFrom,
                "DateTo": dateTo,
            }

            url = f"{self._api_url}api/consumption/consumptionTimeSeries"

            result = requests.post(url, json=data, headers=headers)
            result_json = result.json()
            #print(json.dumps(result_json, sort_keys = False, indent = 4))
            # Clean data so only valid data is returned and register the valid date
            series_data = []
            last_valid_date = ""
            if result_json["Series"]:
                for data in result_json["Series"][0]["Data"]:
                    # Only add complete data, unless it is the Year or Month zoom levels
                    if data["IsComplete"] == True or zoomLevel < 2:
                        series_data.append({
                            "DateFrom" : data["DateFrom"],
                            "DateTo" : data["DateTo"],
                            "Value" : data["Value"]
                        })
                        # NOTE: Assuming data is sorted by date - which it is
                        last_valid_date = data["DateTo"]

            # Return first data series.  Unknown how more series could come from a single metering device?
            meter_data.append({
                "Data" : series_data,
                "Total" : result_json["Total"],
                "Average": result_json["Average"],
                "Maximum": result_json["Maximum"],
                "Minimum": result_json["Minimum"],
                "LastValidDate" : last_valid_date
                })
        return meter_data

#    def _get_time_series(self, start_time, end_time, zoom_level):
#        #...
#        url = self._base_url + "consumptionView/data"
#        result = requests.post(url, data=data, headers=self._create_headers())
#
#        _LOGGER.debug(f"Response from API. Status: {result.status_code}, Body: {result.text}")
#
#        raw_response = RawResponse()
#        raw_response.status = result.status_code
#        raw_response.body = result.text
#
#        return raw_response

    def _get_year_data(self):
        dateFrom = datetime.now().replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        dateTo = datetime.now().replace(month=12, day=31, hour=23, minute=59, second=59, microsecond=0).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        _LOGGER.debug(f"Getting Year data from {dateFrom} to {dateTo}")
        time_series = self._get_consumption_timeseries(dateFrom=dateFrom, dateTo=dateTo, zoomLevel=self._zoom_level['Year'])
        self._meter_data["year"] = time_series[0]
        if self._last_valid_day:
            self._meter_data["year"]["LastValidDate"] = self._last_valid_day

        #_LOGGER.debug(json.dumps(time_series, sort_keys = False, indent = 4))
        _LOGGER.debug(f"Year Total: {time_series[0]['Total']['Value']}")

    def _get_month_data(self):
        # These get all months of the year
        #dateFrom = datetime.now().replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        #dateTo = datetime.now().replace(month=12, hour=0, minute=0, second=0, microsecond=0).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        # Get just the current month
        now = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        dateFrom = now.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        dateTo = (now.replace(now.year + int(now.month/12), now.month%12+1, 1)-timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S.000Z")

        _LOGGER.debug(f"Getting Month data from {dateFrom} to {dateTo}")
        time_series = self._get_consumption_timeseries(dateFrom=dateFrom, dateTo=dateTo, zoomLevel=self._zoom_level['Month'])
        self._meter_data["month"] = time_series[0]
        if self._last_valid_day:
            self._meter_data["month"]["LastValidDate"] = self._last_valid_day

        #_LOGGER.debug(json.dumps(time_series, sort_keys = False, indent = 4))
        for month_data in time_series[0]['Data']:
            _LOGGER.debug(f"{month_data['DateFrom']} - {month_data['DateTo']} - {month_data['Value']}")
        _LOGGER.debug(f"Month Total/Avg/Min/Max: {time_series[0]['Total']['Value']} / {time_series[0]['Average']['Value']} / {time_series[0]['Minimum']['Value']} / {time_series[0]['Maximum']['Value']}")

    def _get_day_data(self):
        now = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        dateFrom = now.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        dateTo = (now.replace(now.year + int(now.month/12), now.month%12+1, 1)-timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        _LOGGER.debug(f"Getting Day data from {dateFrom} to {dateTo}")
        time_series = self._get_consumption_timeseries(dateFrom=dateFrom, dateTo=dateTo, zoomLevel=self._zoom_level['Day'])
        self._meter_data["day"] = time_series[0]

        #_LOGGER.debug(json.dumps(time_series, sort_keys = False, indent = 4))
        #self._last_valid_day = self._meter_data["day"]["Data"][-1]["DateFrom"]
        self._last_valid_day = self._meter_data["day"]["LastValidDate"]
        for day_data in time_series[0]['Data']:
            _LOGGER.debug(f"{day_data['DateFrom']} - {day_data['DateTo']} - {day_data['Value']}")
        _LOGGER.debug(f"Day Total/Avg/Min/Max/ValidDate: {time_series[0]['Total']['Value']} / {time_series[0]['Average']['Value']} / {time_series[0]['Minimum']['Value']} / {time_series[0]['Maximum']['Value']} / {self._last_valid_day}")

    def _get_hour_data(self, days_back = None, from_date = None):
        """
        If days_back is set, the function returns valid data this many days back.  A 1 could result in no valid data returned.
           If it is not set, data returned is from the last valid day.

        from_date can be set instead to the day in the month from which to start getting data.  All days until present day will be retrieved.
           this is a datetime object
        """
        if days_back:
            start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            #duration = range(1, days_back+1)
            duration = range(days_back, 0, -1)
        elif from_date:
            start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            #duration = range(1, (start_date - from_date).days+1)
            duration = range((start_date - from_date).days, 0, -1)
        else:
            start_date = datetime.strptime(self._last_valid_day, '%Y-%m-%dT%H:%M:%S%z').replace(hour=0, minute=0, second=0, microsecond=0)
            duration = range(1)

        first_day = True
        for day in duration:
            now = (start_date - timedelta(days=day)).replace(hour=0, minute=0, second=0, microsecond=0)
            # I would claim this is a bug in the REST service.  Asking for data for an hour also return the hour after. So we ask for data until 22:59 to
            # not get data from 00:00-00:59 the day after. That throws off the avg/min/max numbers for the day.  So -1 hour on 'from' and 'to'
            dateFrom = (now - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
            dateTo =  now.replace(hour=22, minute=59, second=59, microsecond=0).strftime("%Y-%m-%dT%H:%M:%S.000Z")
            #dateTo = now.replace(hour=23, minute=0, second=0, microsecond=0).strftime("%Y-%m-%dT%H:%M:%S.000Z")
            _LOGGER.debug(f"Getting Hour data {day} day(s) back in time from {dateFrom} to {dateTo}")
            time_series = self._get_consumption_timeseries(dateFrom=dateFrom, dateTo=dateTo, zoomLevel=self._zoom_level['Hour'])
            _LOGGER.debug(f"timeseries = {time_series}")
            if first_day:
                self._meter_data["hour"] = time_series[0]
                first_day = False
            elif time_series[0]["Data"]:
                # If the dataset returned is not empty, move the valid date and mix/max/avg data forward.
                # That will ensure the dataset reflects the latest values in case they are >24h old
                self._meter_data["hour"]["Data"] = self._meter_data["hour"]["Data"] + time_series[0]["Data"]
                self._meter_data["hour"]["Total"] = time_series[0]["Total"]
                self._meter_data["hour"]["Average"] = time_series[0]["Average"]
                self._meter_data["hour"]["Maximum"] = time_series[0]["Maximum"]
                self._meter_data["hour"]["Minimum"] = time_series[0]["Minimum"]
                self._meter_data["hour"]["LastValidDate"] = time_series[0]["LastValidDate"]

        #_LOGGER.debug(json.dumps(time_series, sort_keys = False, indent = 4))
        for hour_data in self._meter_data["hour"]["Data"]:
            _LOGGER.debug(f"{hour_data['DateFrom']} - {hour_data['DateTo']} - {hour_data['Value']}")
        _LOGGER.debug(f"Total/Avg/Min/Max: {self._meter_data['hour']['Total']['Value']} / {self._meter_data['hour']['Average']['Value']} / {self._meter_data['hour']['Minimum']['Value']} / {self._meter_data['hour']['Maximum']['Value']}")

    def get_latest(self):
        '''
        Login and set some numbers needed for the data calls.  Then retrive all data from the API
        '''
        self._get_session_id()
        self._get_bearer_token()
        self._get_active_meters()

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
        # This one retrieves data 7 days back
        self._get_hour_data(days_back=7)

        # Lastly make an entry for the last valid day in the dataset.  Maybe someone can use this.
        self._meter_data["valid_date"] = {}
        self._meter_data["valid_date"]["Value"] = self._last_valid_day

        return self._meter_data