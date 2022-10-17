from seleniumwire import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
#from selenium.webdriver.firefox.options import Options
#import requests
#import json
import time
import random
from flask import Flask, request
from flask_restful import Resource, Api

#Firefox - but was very slow!
#options = Options()
#options.headless = True
#executable_path=r'/usr/bin/geckodriver'

# Chrome seems to perform a lot better
executable_path=r'/usr/bin/chromedriver'
options = webdriver.ChromeOptions()
spath="/home/seluser/"

## Setup the Flask endpoint(s)
class NovafosTokenAPI(Resource):
  def get(self):
    """ TODO: Add a little staus here on server status and maybe other things."""
    pass

  def post(self):
    # Requirement: Header: Content-Type:application/json
    #  Also required fields:
    # {
    #   "username": <str>
    #   "password": <str>
    #   "supplierid": <str>
    #   "screenshot": <bool> (optional)
    # }
    post = request.get_json()
    if not "username" in post:
      return { "message": "ERROR: no username specified" }
    if not "password" in post:
      return { "message": "ERROR: no password specified" }
    if not "supplierid" in post:
      return { "message": "ERROR: no supplierid specified" }
    if "screenshot" in post:
      screenshot = True
    else:
      screenshot = False
    username = post['username']
    password = post['password']
    supplierid = post['supplierid']
    login_url = f"https://minforsyning-2.kmd.dk/?plant={supplierid}&utility=0&plus=true"

    dummy_token = {
        'access_token': '',
        'token_type': 'Bearer',
        'expires_in': 3599,
        'scope': 'openid profile pluginapi_int',
        'id_token': ''
      }
    #driver = webdriver.Firefox(options=options, executable_path=executable_path)
    #login_url = "https://duckduckgo.com"
    driver = webdriver.Chrome(chrome_options=options)
    login = driver.get(login_url)
    if screenshot:
      driver.get_screenshot_as_file(spath+"screen_login.png")

    try:
      elem = WebDriverWait(driver, 30).until(
          EC.presence_of_element_located((By.ID, "collapseUserPassword"))
        )
    except:
      driver.quit()
      return dummy_token

    element = driver.find_element(By.ID, "collapseUserPassword")
    driver.execute_script("arguments[0].setAttribute('class','')", element)
    elm_email = driver.find_element(By.ID, "Input_Email")
    elm_pass  = driver.find_element(By.ID, "Input_Password")
    elm_email.send_keys(username)
    elm_pass.send_keys(password)

    if screenshot:
      driver.get_screenshot_as_file(spath+"screen_login_filled.png")

    # Simulate a person taking some time to hit Enter.
    # Maybe some mouse jiggling is needed too.
    time.sleep(round(random.uniform(3.14, 6.42),2))
    #input("Press ENTER once you are finished")
    elm_pass.send_keys(Keys.ENTER)

    try:
      elem = WebDriverWait(driver, 30).until(
          EC.presence_of_element_located((By.ID, "inputName"))
        )
      if screenshot:
        driver.get_screenshot_as_file(spath+"screen_final.png")
    except:
      driver.quit()
      return dummy_token

    _token = ""
    for req in driver.requests:
      # Locate https://easy-energy-identity.kmd.dk/oidc/token in network traffic
      if "/oidc/token" in  req.url: # and request.method == 'POST' and request.response.status_code == 200:
        # Byte stream
        print("Token retrieved:\n")
        print(req.response.body)
        _token = req.response.body.decode('UTF-8')

    driver.quit()
    if _token == "":
      return dummy_token

    # String returned
    return _token

class NovafosTokenAPITest(Resource):
  """ Test endpoint to be used with pynovafos """
  def get(self):
    """ TODO: Add a little staus here on server status and maybe other things."""
    return { 'message': 'TEST MODE' }

  def post(self):
    return {
        'access_token': '<for testing purposes paste a fresh token here.>',
        'token_type': 'Bearer',
        'expires_in': 3599,
        'scope': 'openid profile pluginapi_int',
        'id_token': ''
      }

################################
## Setup the the Flask server
###################################
app = Flask(__name__)
api = Api(app)
## Add endpoints
api.add_resource(NovafosTokenAPI, '/novafos-token/')
api.add_resource(NovafosTokenAPITest, '/novafos-token-test/')

# Run the service on port 5000, listening to all interfaces
if __name__ == "__main__":
  app.run(host='0.0.0.0', port=5000, debug=False)
