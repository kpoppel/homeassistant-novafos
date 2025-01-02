# INSTALLING ADDONS

## ha-novafos-token

This add-on is a Chrome extension (and compatible browsers probably) which scrapes the token automatically and basically enables a one-click update of your home Assistant dataset.
You can inspect the code (why it is unpacked) to verify it does not transmit your access token, nor any information out of your home.  Please do yourself a favor and make a habit of checking such things.

Please check out the README in this directory for more information.

## traefik-proxy

If you are unsure how to serve Home Assistant via HTTPS (which is a requirement for the Chrome extension), you can find and example here using Traefik as a docker-compose file and static setup.
There are several other ways to do this of course.

## novafos-login

This is a vey experimental add-on to fire up a Selenium container which will load up the homepage and perform the login procedure in the browser.

Copy the novafos-login directory to /config/addons/ .

  * In Home Assistant go to "Configuration", click the "Add-ons", click "add-on-store" in the bottom right corner.
  * Next in the top right oveflow menu click the "Check for updates" button.  Select from the "Local addons" this add-on.  
  * Install the add-on
  * Start the add-on
  * Check the logs that it is started

  NOTE: This is very experimental, and any help in making it work as an add-on in Home Assistant is appreciated.
    The code runs as-is in an external docker host, so it "should" work (famous last words)...

### **Latest news on this:**

While is was fun and very time consuming to  try out using Selenium for loggin into the website, it does not survive for long in a ReCAPTCHA world.
Novafos (KMD probably) introduced ReCAPCHAs before I got to try this add-on in production, and first deployment went well for a week or so, then
the robots were trained enough to block further progress here.

I recommend trying the `ha-novafos-token` Chrome add-on instead.  It does not rely on automated login (which is the problem to overcome), but makes tokes scraping automatic.