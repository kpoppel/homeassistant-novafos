'''
Primary public module for novafos.dk API wrapper.
'''
from __future__ import annotations

from datetime import datetime
from datetime import timedelta
import logging
import json
import requests
import hashlib
import re
import string
import random
import base64
import uuid

# Automate recaptcha
from seleniumwire import webdriver

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.options import Options
import time


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
        self._username = username
        self._password = password
        self._supplierid = supplierid
        self._api_url = "https://minforsyningplugin2webapi.kmd.dk"

        self._access_token = ""
        self._customer_id = ""
        self._active_meters = []
        self._meter_data = {}
        self._last_valid_day = None

        # NOTE: Added because of reCAPCTHA login screen
        self._access_token_date_updated = ""

        # TODO: Add docker host config here instead of directly on the authentication function.
        # ...

        # Zoom level is the granuarity of the retrieved data
        self._zoom_level = {
         "Year"    : 0,
         "Month"   : 1,
         "Day"     : 2,
         "Hour"    : 3,
         "Billing" : 4
        }

    def _print_json(self, map):
        print(json.dumps(map, indent=4, sort_keys=True, ensure_ascii=False))

    def _generate_random_string(self, size):
        rand = random.SystemRandom()
        return ''.join(rand.choices(string.ascii_letters + string.digits, k=size))

    def _generate_code(self) -> tuple[str, str]:
        rand = random.SystemRandom()
        code_verifier = ''.join(rand.choices(string.ascii_letters + string.digits, k=67))

        code_sha_256 = hashlib.sha256(code_verifier.encode('utf-8')).digest()
        b64 = base64.urlsafe_b64encode(code_sha_256)
        code_challenge = b64.decode('utf-8').replace('=', '')

        return (code_verifier, code_challenge)

    def authenticate_using_selenium(self, selenium_host_url):
        """ This function relies on a remote browser controlled by selenium.  While the recaptcha will eventually
            figure out this is an automated login, it might just work most of the time.
            The code varies the time from data is entered (as a password manager vould do) to the point where
            <ENTER> is 'pressed'.
            If using selenium/standalone-firefox, access the VNC terminal to check up on things.
        """
        self._access_token_date_updated = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        data = {
             "username": self._username,
             "password": self._password,
             "supplierid": self._supplierid[0:3]
        }
        # The selenium response is copying the reponse from the oidc endpoint.
        response = requests.post(selenium_host_url, json=data)
        try:
            response_dict = json.loads(response.json())
            if response_dict['access_token'] == "":
                _LOGGER.error('Failed to retrieve bearer token (maybe you are a robot?)')
                self._access_token = ""
                return False
            self._access_token = f"{response_dict['token_type']} {response_dict['access_token']}"
            _LOGGER.debug('Got bearer token (access to API was Ok) valid for %ss: %s', response_dict['expires_in'], self._access_token)
            return True
        except:
            _LOGGER.error('Failed to retrieve bearer token (no JSON returned)')
            return False

    def authenticate_using_access_token(self, access_token, access_token_date_updated):
        """ The only reason for this function is due to to a reCAPTCHA challenge on the Novafos login page.
            The date is used to verify the token is not too old when getting data.
        """
        self._access_token_date_updated = access_token_date_updated
        # Make a simple validation of the access_token length and only update if it has the correct length
        if len(access_token) >= 1505:
            self._access_token = "Bearer "+access_token
        else:
            self._access_token = ""
            _LOGGER.error(f"Token update does not seem to have a valid length. Please check again. (This message is normal the first time the integration starts)")
        _LOGGER.debug("Access token set to: '%s' at date: '%s'", self._access_token, self._access_token_date_updated)

        return True

    def authenticate(self):
        """
        The OIDC login procedure automated.
        Use the username/password/supplierid credentials to login and get a code token from which to retrieve the Bearer token.
        """
        nonce = self._generate_random_string(size=42)
        state = self._generate_random_string(size=42)
        code_verifier, code_challenge = self._generate_code()
        # Tokens generated during the handshake:
        request_verification_token = None
        code = None

        # ID determined between Novafos and the OIDC service at KMD
        client_id = '1DA5CFAF-F67F-4DA1-A1A6-513A7768F994'
        # Our identification - generate e new one everytime we update data
        app = uuid.uuid4()

        # The capabilities of the OIDC service can be fetched here:
        # https://easy-energy-identity.kmd.dk/.well-known/openid-configuration
        # This is useful for a dynamic setup where different services must be contacted.
        # Here we know which one and how to do it.

        # The first step is to actually load the login webpage.  KMD made sure to include a hidden form value
        # probably to ensure the one who submits the form is also the one who loaded it in the first place.
        ######################
        # A session is needed for the login part as cookies are exchanged as well.
        session = requests.Session()

        headers = {}

        params = {
            'ReturnUrl': f'/oidc/authorize?client_id={client_id}&redirect_uri=https%3A%2F%2Fminforsyning-2.kmd.dk%2Flogin&response_type=code&scope=openid%20profile%20pluginapi_int&nonce={nonce}&state={state}&code_challenge={code_challenge}&code_challenge_method=S256&utility={self._supplierid}&login_type=mf&post_logout_redirect_uri=https%3A%2F%2Fminforsyning-2.kmd.dk%2Flogin&app={app}',
        }

        response = session.get('https://easy-energy-identity.kmd.dk/Identity/Account/Sign/Login', params=params, headers=headers)

        # Get the 'RequestVerificationToken' out of response TEXT:
        #<input name="__RequestVerificationToken" type="hidden" value="CfDJ8BtjbcM0azZLgmK58SCaJRwb4UK7iGEmt5ENx8EhXvgpt3GFKIwLR4svDgNa0sHp9mNOemf4df0IYV25vmqQD-QFI7Dh7sVcM-D5U-smZpjnu7xajAQEHWx-fT_pzj-jXhOskLj4G22355Z2JysR_tM" /></
        # It is always 155 characters as well it seems..
        # If this code is not present, authentication will fail.
        rvt = re.search(r'(?<=__RequestVerificationToken" type="hidden" value=")([\w-]+)', response.text)
        request_verification_token = rvt.group(0)
        _LOGGER.debug('Got login form request_verification_token = %s', request_verification_token)

        # Second step is to submit the login form with the username and password.
        # In the response from the server we get a secret code to be used later
        ######################
        headers = {
            'content-type': 'application/x-www-form-urlencoded',
        }

        params = {
            'returnUrl': f'/oidc/authorize?client_id={client_id}&redirect_uri=https%3A%2F%2Fminforsyning-2.kmd.dk%2Flogin&response_type=code&scope=openid%20profile%20pluginapi_int&nonce={nonce}&state={state}&code_challenge={code_challenge}&code_challenge_method=S256&utility={self._supplierid}&login_type=mf&post_logout_redirect_uri=https%3A%2F%2Fminforsyning-2.kmd.dk%2Flogin&app={app}',
        }

        data = f'Input.Email={self._username}&Input.Password={self._password}&__RequestVerificationToken={request_verification_token}'

        response = session.post('https://easy-energy-identity.kmd.dk/Identity/Account/Sign/Login', params=params, headers=headers, data=data)

        # At this point user/password should have been accepted. (if "forkert" is in text then login did not succeed)

        # url field contains the next code we need.
        #  https://minforsyning-2.kmd.dk/login?code=0gRigEdqZKwcB_fdPqaiW3t410UrXLXXEC-eT6vrXuw&state=b%27SP0DKBBZ5YX4L8W4S70E08SD2Q5MSUOIHC05W90D0Y%27
        code = response.url[41:84]

        # Something is wrong if the code contains the word "Account".  Too many wrong login attempts causes account lockout condition
        if "Account" in code:
            raise LoginFailed('Code not retrieved correctly. Plugin will not continue login process.  Check user/pass/supplierID')
        if "Lockout" in code:
            raise('The Novafos account is subject to lockout due to too many failed login attempts. You may be subject to a 30 min lockout.')

        _LOGGER.debug('Got one-time session code (supplierid and user/pass was ok): %s', code)

        # Third step is to use the code from the authentication service to verify we are the right one
        # The correct code and the state issued from the beginning must be correct.
        # Interestingly enough it seems this step can be omitted entirely - keeping it anyway.
        #####################
        headers = {}

        params = {
            'code': code,
            'state': state,
        }

        response = requests.get('https://minforsyning-2.kmd.dk/login', params=params, headers=headers)

        # Finally the Bearer token can be retrieved from the oicd token endpoint.
        # The code is reused to verify we can get the token.
        #####################
        headers = {}

        data = {
            'grant_type': 'authorization_code',
            'client_id': client_id,
            'code_verifier': code_verifier, 
            'code': code,
            'redirect_uri': 'https://minforsyning-2.kmd.dk/login',
        }

        response = requests.post('https://easy-energy-identity.kmd.dk/oidc/token', headers=headers, data=data)
        self._access_token = f"{response.json()['token_type']} {response.json()['access_token']}"

        _LOGGER.debug(f'Got bearer token (access to API was Ok) valid for %ss: %s', response.json()['expires_in'], self._access_token)

        return True

    def _get_customer_id(self):
        # Need to retrieve the customer ID from the user profile to fetch data.
        headers = {
            'Authorization': self._access_token,
        }

        url = f'{self._api_url}/api/profile/get'

        response = requests.get(url, headers=headers)        
        #self._print_json(response.json())
        self._customer_id = f"{response.json()['Customers'][0]['Id']}"
        _LOGGER.debug("Retrieved customer_id: %s", self._customer_id)

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
            'Customer-Id': self._customer_id,
            "Authorization" : self._access_token
        }

        data = {
            "IncludeUnits":"true"
        }

        url = f"{self._api_url}/api/meter/customerActiveMeters"

        response = requests.post(url, data=data, headers=headers)

        #self._print_json(response.json())
        response_json = response.json()
        self._active_meters = []
        for meter in response_json:
            """ Pick up active water measuring meters """
            if meter["IsActive"] == True and meter["ConsumptionTypeId"] == 6:
                active = {
                    "InstallationId" : meter["InstallationId"],
                    "MeasurementPointId" : meter["MeasurementPointId"],
                    "Unit" : meter["Units"][0],
                }
                self._active_meters.append(active)
        _LOGGER.debug('Got active (water) meters : %s', self._active_meters)
        # TODO: Novafos also measures oil and gas?

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
            'Customer-Id': self._customer_id,
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

            url = f"{self._api_url}/api/consumption/consumptionTimeSeries"

            result = requests.post(url, json=data, headers=headers)
            result_json = result.json()

            # Enable this to see all returned data from the API:
            _LOGGER.debug(json.dumps(result_json, sort_keys = False, indent = 4))

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

    def _get_year_data(self):
        dateFrom = datetime.now().replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        dateTo = datetime.now().replace(month=12, day=31, hour=23, minute=59, second=59, microsecond=0).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        _LOGGER.debug(f"Getting Year data from {dateFrom} to {dateTo}")
        time_series = self._get_consumption_timeseries(dateFrom=dateFrom, dateTo=dateTo, zoomLevel=self._zoom_level['Year'])
        self._meter_data["year"] = time_series[0]
        if self._last_valid_day:
            self._meter_data["year"]["LastValidDate"] = self._last_valid_day

        if time_series[0]['Data']:
            #_LOGGER.debug(json.dumps(time_series, sort_keys = False, indent = 4))
            _LOGGER.debug(f"Year Total: {time_series[0]['Total']['Value']}")
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
        time_series = self._get_consumption_timeseries(dateFrom=dateFrom, dateTo=dateTo, zoomLevel=self._zoom_level['Month'])
        self._meter_data["month"] = time_series[0]
        if self._last_valid_day:
            self._meter_data["month"]["LastValidDate"] = self._last_valid_day

        #_LOGGER.debug(json.dumps(time_series, sort_keys = False, indent = 4))
        if time_series[0]['Data']:
            for month_data in time_series[0]['Data']:
                _LOGGER.debug(f"{month_data['DateFrom']} - {month_data['DateTo']} - {month_data['Value']}")
            _LOGGER.debug(f"Month Total/Avg/Min/Max: {time_series[0]['Total']['Value']} / {time_series[0]['Average']['Value']} / {time_series[0]['Minimum']['Value']} / {time_series[0]['Maximum']['Value']}")
        else:
            _LOGGER.warning("The KMD API returned no monthly data.  Expect sensors to signal 'unavailable'")

    def _get_day_data(self):
        now = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        dateFrom = now.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        dateTo = (now.replace(now.year + int(now.month/12), now.month%12+1, 1)-timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        _LOGGER.debug(f"Getting Day data from {dateFrom} to {dateTo}")
        time_series = self._get_consumption_timeseries(dateFrom=dateFrom, dateTo=dateTo, zoomLevel=self._zoom_level['Day'])
        self._meter_data["day"] = time_series[0]

        #self._last_valid_day = self._meter_data["day"]["Data"][-1]["DateFrom"]
        self._last_valid_day = self._meter_data["day"]["LastValidDate"]

        #_LOGGER.debug(json.dumps(time_series, sort_keys = False, indent = 4))
        if time_series[0]['Data']:
            for day_data in time_series[0]['Data']:
                _LOGGER.debug(f"{day_data['DateFrom']} - {day_data['DateTo']} - {day_data['Value']}")
            _LOGGER.debug(f"Day Total/Avg/Min/Max/ValidDate: {time_series[0]['Total']['Value']} / {time_series[0]['Average']['Value']} / {time_series[0]['Minimum']['Value']} / {time_series[0]['Maximum']['Value']} / {self._last_valid_day}")
        else:
            _LOGGER.warning("The KMD API returned no daily data.  Expect sensors to signal 'unavailable'")

    def _get_hour_data(self, days_back = None, from_date = None):
        """
        If days_back is set, the function returns valid data this many days back.  A 1 could result in no valid data returned.
           If it is not set, data returned is from the last valid day.

        from_date can be set instead to the day in the month from which to start getting data.  All days until present day will be retrieved.
           this is a datetime object
        """
        if days_back:
            start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            duration = range(days_back, 0, -1)
        elif from_date:
            start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
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
        if time_series[0]['Data']:
            for hour_data in self._meter_data["hour"]["Data"]:
                _LOGGER.debug(f"{hour_data['DateFrom']} - {hour_data['DateTo']} - {hour_data['Value']}")
            _LOGGER.debug(f"Total/Avg/Min/Max: {self._meter_data['hour']['Total']['Value']} / {self._meter_data['hour']['Average']['Value']} / {self._meter_data['hour']['Minimum']['Value']} / {self._meter_data['hour']['Maximum']['Value']}")
        else:
            _LOGGER.warning("The KMD API returned no hourly data.  Expect sensors to signal 'unavailable'")


    def get_latest(self):
        # NOTE: This part is all due to login screen reCAPTCHA down to ^^
        now = datetime.now()
        # Allow 45 minutes since the last token update.  If updating after this point, return dummy data.
        if self._access_token == "" or datetime.strptime(self._access_token_date_updated, '%Y-%m-%dT%H:%M:%S') + timedelta(minutes=45) < now:
            _LOGGER.debug("access_token too old or not set correctly:")
            dateTo =  now.strftime("%Y-%m-%dT%H:%M:%S+00:00")
            dateTwo =  now.strftime("%Y-%m-%dT%H:%M:%S")
            return {
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
        ###^^^^^
        self._get_customer_id()

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
