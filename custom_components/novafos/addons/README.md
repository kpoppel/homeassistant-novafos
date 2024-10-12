# INSTALLING ADDONS

## ha-novafos-token

This add-on is a Chrome extension (and compatible browsers probably) which uses the developer tools to scrape the token automatically and basically enables a one-click update of your home Assistant dataset.
You can inspect the code (why it is unpacked) to verify it does not transmit your access token, nor any information out of your home.  Please do yourself a favor and make a habit of checking such things.

The add-on is a brutally made fork of the "token-inspector" addon available on the chrome shop.  Thank-you go to the originator which made it much easier to get this project moving.

### Requirements

Chrome or extension compatible browser.  Access to Home Assistant via HTTPS.  If you don't know how to serve HA through HTTPS, look for help on the forums.  Some use apache, nginx, caddy, Traefik, NabuCasa.
there is a thread here which may help too: [https://community.home-assistant.io/t/connecting-to-ha-locally-using-https/566441/50](https://community.home-assistant.io/t/connecting-to-ha-locally-using-https/566441/50)

### Daily use the add-on

1. Browse to https://novafos.dk and login as you normally would.  I strongly recommend using a password manager like Bitwarden to login faster.
2. Press F12 and find the tab with the add-on
3. Refresh the page (CTRL-R) and your token should appear.
4. Press the button to send an action-service call to Home Assistant.

### Install as follows

1. Copy the directory `ha-novafos-token` to your PC.
2. Open Chrome extensions `chrome://extensions/`
3. Enable "developer mode" to allow loading the extension from your harddrive.
4. Press "load unpacked"/"indlæs upakket" and browser to the directory `ha-novafos-token`.  Press the okay button.
5. The extension now loads into the browser.

### Setup the add-on (one-time)

1. In Home Assistant go to https://homeassistant.local/profile/security, find the long lived token section and create a new token.  you can call it "novafos-chrome" or whatever you like.  Save the value, you will only see it once.
1. Press F12 and find the tab with the extension.
2. Enter your https URL for your home assistant installation.  NOTE: If you are not accessing HA using https, this add-on will not work because calling http URLs from secure places is never ever a good idea, and Chrome blocks it.
3. Input your long lived Home Assistant token in the appropriate field.

The values are saved in your browser local storage.

Setup complete.

### Extras
If you want to play around, you can inspect the scraped token and get a 'curl' command line to copy into a prompt to see what happens.  This is great if you cannot get it to work.

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