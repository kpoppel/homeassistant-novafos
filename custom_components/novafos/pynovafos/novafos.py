'''
Primary public module for novafos.dk API wrapper.
'''
from datetime import datetime
from datetime import timedelta
import json
import requests
import logging
from .models import RawResponse
from .models import TimeSeries

_LOGGER = logging.getLogger(__name__)

class Novafos:
    '''
    Primary exported interface for KMD API wrapper.
    '''
    def __init__(self, username, password, supplierid):
        self._username = username
        self._password = password
        self._supplierid = supplierid
        self._base_url = f'https://{supplierid}.webtools.kmd.dk/wts/'
        self._session_id = ""

        self._item_group_id = ""
        self._item_id = ""
        self._item_category = ""
        self._prescale_unit_id = ""
        self._view_id = ""

        '''
        Zoom level is the granularity defined by the KMD API.
        '''
        self._zoom_level = (
            'x_settlementperiod_years',
            'day_by_hours',
            'month_by_days',
            'week_by_days',
            'year_by_months',
            'x_days',
            'x_weeks',
            'x_months',
            'x_years'
           )


    def _create_headers(self):
        return {"Session-Id": self._session_id,
                "Customer-Database-Number":self._supplierid,
                "Content-Type":"application/x-www-form-urlencoded; charset=UTF-8"
               }

    def _get_access_token(self):
        data = {"username":self._username,
                "password":self._password,
                "rememberLogin":"false"
               }
        url = self._base_url + "loginUserPassword"

        result = requests.post(url, data=data, headers=self._create_headers())
        result_json = result.json()
        self._session_id = result_json['sessionId']
        _LOGGER.debug(f"Got short lived token: {self._session_id}")
        return self._session_id

    def _get_item_groups(self):
        url = self._base_url + "itemGroups"
   
        result = requests.get(url, headers=self._create_headers())
        result_json = result.json()
        last_item_group = result_json[-1]
        last_meter = last_item_group['items'][-1]

        self._item_group_id = last_item_group['id']
        self._item_id = last_meter['id']
        self._item_category = last_meter['itemCategory']
        self._prescale_unit_id = last_meter['series'][0]['prescaleUnits'][0]['id']

    def _get_view_id(self):
        '''
        Look for the identifier for the dataset related to usage consumption.
        '''
        url = f"{self._base_url}consumptionView/list/?itemId={self._item_id}&itemCategory={self._item_category}&itemGroupId={self._item_group_id}"
        result = requests.get(url, headers=self._create_headers())
        result_json = result.json()

        for view in result_json['views']:
            if view['nameType'] == 'common.series.usageConsumption':
                self._view_id = view['id']
                break


    def _get_time_series(self, start_time, end_time, zoom_level):
        data = {
                "viewId" : self._view_id,
                "itemId" : self._item_id,
                "itemCategory" : self._item_category,
                "itemGroupId": self._item_group_id,
                "zoomLevel":zoom_level,
                "prescaleUnitId":self._prescale_unit_id,
                "start":start_time,
                "end":end_time
               }

        url = self._base_url + "consumptionView/data"
        result = requests.post(url, data=data, headers=self._create_headers())

        _LOGGER.debug(f"Response from API. Status: {result.status_code}, Body: {result.text}")

        raw_response = RawResponse()
        raw_response.status = result.status_code
        raw_response.body = result.text

        return raw_response

    def _get_last_valid_series(self):
        '''
        Get last valid 24 hour period of data.  Data is 24 hours delayed at the data warehouse.
        Data validity is determined by the field "complete" on each datapoint.
        '''
        days_to_subtract = 1
        today = datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)
        # Set a specific date (testing): today = datetime(2021, 2, 9, 0, 0)
        start_time = int( (today - timedelta(days=days_to_subtract)).timestamp() )*1000
        end_time =  int( today.timestamp() )*1000

        return self._get_time_series(start_time, end_time, self._zoom_level[1])

    def _get_year_to_date_series(self):
        '''
        Get this year's data, to get comsumption year-to-date
        '''
        days_to_subtract = 365
        today = datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)
        # Set a specific date (testing): today = datetime(2021, 2, 9, 0, 0)
        start_time = int( (today - timedelta(days=days_to_subtract)).timestamp() )*1000
        end_time =  int( today.timestamp() )*1000

        return self._get_time_series(start_time, end_time, self._zoom_level[0])

    def get_latest(self):
        '''
        Login and get some numbers needed for the data calls.
        '''
        self._get_access_token()
        self._get_item_groups()
        self._get_view_id()

        '''
        Get latest valid data set.
        '''
        raw_data = self._get_last_valid_series()

        if raw_data.status == 200:
            json_response = json.loads(raw_data.body)

            r = self._parse_result("hourly", json_response)

            keys = list(r.keys())

            keys.sort()
            keys.reverse()

            result = r[keys[0]]
        else:
            result = TimeSeries(raw_data.status, None, None, None, raw_data.body)

        '''
        Get consumption year-to-date and amend the Timeseries with the result of this 2nd query.
        '''
        raw_data = self._get_year_to_date_series()
        if raw_data.status == 200:
            json_response = json.loads(raw_data.body)

            r = self._parse_result("yearly", json_response)

            keys = list(r.keys())

            keys.sort()
            keys.reverse()

            result2 = r[keys[0]]

            result.set_total_metering_data(result2.get_total_metering_data())
            _LOGGER.debug(f"Yearly total data set: {result2.get_total_metering_data()} {result.get_total_metering_data()}")
        else:
            result.set_total_metering_data(None)
            _LOGGER.debug(f"Yearly total data failed: {raw_data.status}")

        return result

    def _parse_result(self, series_type, result):
        '''
        Parse result from API call.
        series_type: Select to parse hourly or yearly dataset.
        '''
        parsed_result = {}
        if 'series' in result and len(result['series']) > 0:
            for series in result['series']:
                end = datetime.fromtimestamp(series['serieData']['end']/1000)
                valid_end = end - timedelta(days=1)
                _LOGGER.debug(f"Series end time: {end} - data valid from {valid_end}")
                metering_data = []
                total_metering_data = None
                for datapoint in series['serieData']['datapoints']:
                    fr = datetime.fromtimestamp(datapoint['start']/1000)
                    to = datetime.fromtimestamp(datapoint['end']/1000)
                    val = float(datapoint['value'])
                    valid = datapoint['complete']

                    if series_type == "hourly":
                        # Even though some data point can be tagged as incomplete it is still the best we got.
                        _LOGGER.debug(f"{fr}-{to} {fr.date()==valid_end.date()} : {val} : {valid}")
                        if fr.date() == valid_end.date(): # and valid == True: <- If I one day figure out it is usable
                            _LOGGER.debug(f"{fr}-{to} : {val} : {valid}")
                            metering_data.append(val)

                    else:
                        # Yearly data is not valid until the year ends, so we ignore the valid field
                        # and just use whatever latest data we get.
                        _LOGGER.debug(f"{fr}-{to} : {val} : {valid}")
                        total_metering_data = val

                # TODO:
                # 'valid_end' will be 1 day before the day data was fetched. 'end' is the day data was fetched.
                # HA gets confused if the timeseries day is in the past I think.  But do try both.
                date = end
                #date = valid_end

                time_series = TimeSeries(200, date, metering_data, total_metering_data)
                parsed_result[date] = time_series
        else:
            parsed_result['none'] =  TimeSeries(404,
                                                None,
                                                None,
                                                None,
                                                f"Data most likely not available yet-3: {result}")

        return parsed_result
