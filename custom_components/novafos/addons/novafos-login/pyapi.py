from seleniumwire import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
#from selenium.webdriver.firefox.options import Options
import time
import random
from flask import Flask, request, make_response
from flask_restful import Resource, Api
import base64
import jinja2

def convert_img_to_stream(img_local_path):
  """ Base64 encode an image"""
  import base64
  img_stream = ''
  with open(img_local_path, 'rb') as img_f:
      img_stream = img_f.read()
      img_stream = base64.b64encode(img_stream).decode()
  return img_stream

def return_images_as_stream(filenames):
  """ Takes a list of paths to images and returns a HTML string with bse64 encoded images."""
  images = []
  for img_path in filenames:
    img_stream = convert_img_to_stream(img_path)
    images.append(img_stream)

  doc= """
        <!DOCTYPE html><html><body>
        {% for img in images %}
          <img src="data:image/jpeg;base64, {{ img }}">
        {% endfor %}
        </body></html>
        """    
  template = jinja2.Template(doc)
  resp = make_response(template.render(images=images))
  resp.headers.set('content-type', 'text/html; charset=utf-8')
  # Ready for returning to caller
  return resp

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
  def get(self, func = None):
    if func == "screenshots":
      filenames = ['screen_login.png', 'screen_login_filled.png', 'screen_login_final.png']
      return return_images_as_stream(filenames)
    else:
      return { "message": "Server is up at /novafos-token/.  If you need to see screenshots access /novafos-token/screenshots"}

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
    driver = webdriver.Chrome(chrome_options=options)
    login = driver.get(login_url)
    if screenshot:
      driver.get_screenshot_as_file(spath+"screen_login.png")

    try:
      elem = WebDriverWait(driver, 30).until(
          EC.presence_of_element_located((By.ID, "collapseUserPassword"))
        )
    except:
      print("Timeout waiting for the login screen. Screenshots available at /novafos-token/screenshots")
      driver.get_screenshot_as_file(spath+"screen_login.png")
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
      print("Timeout waiting for the final screen. Screenshots available at /novafos-token/screenshots")
      driver.get_screenshot_as_file(spath+"screen_final.png")
      driver.quit()
      return dummy_token

    _token = ""
    for req in driver.requests:
      # Locate https://easy-energy-identity.kmd.dk/oidc/token in network traffic
      if "/oidc/token" in  req.url: # and request.methiod == 'POST' and request.response.status_code == 200:
        # Byte stream
        print("Token retrieved:\n")
        print(req.response.body)
        _token = req.response.body.decode('UTF-8')

    driver.quit()
    if _token == "":
      return dummy_token

    # Byte stream returned
    return _token

class NovafosTokenAPITest(Resource):
  """ Test endpoint to be used with pynovafos """
  def get(self, func = None):
    if func == "screenshots":
      driver = webdriver.Chrome(chrome_options=options)
      login_url = "https://duckduckgo.com"
      login = driver.get(login_url)
      driver.get_screenshot_as_file(spath+"screen_login.png")
      driver.get_screenshot_as_file(spath+"screen_login_filled.png")
      driver.get_screenshot_as_file(spath+"screen_login_final.png")
      driver.quit()

      filenames = ['screen_login.png', 'screen_login_filled.png', 'screen_login_final.png']
      return return_images_as_stream(filenames)
    else:
      return { "message": "Server is up at /novafos-token-test/"}

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
api.add_resource(NovafosTokenAPI, '/novafos-token/', '/novafos-token/<string:func>')
api.add_resource(NovafosTokenAPITest, '/novafos-token-test/', '/novafos-token-test/<string:func>')

# Run the service on port 5000, listening to all interfaces
if __name__ == "__main__":
  app.run(host='0.0.0.0', port=5000, debug=False)
