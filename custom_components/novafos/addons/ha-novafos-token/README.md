# 🚀 What does this do?

Retrieve a Bearer token from Novafos website and inject into Home Assistant

When logging into Novafos using either email/password or MitID (keep devtools closed during the login process),
this extension will inspect headers from network traffic and present the user with a button to send it to
Home Assistant.

The source code is open for verification.

# 🎯 How to Install

## Requirements

Chrome or extension compatible browser.  Access to Home Assistant via HTTPS.  If you don't know how to serve HA through HTTPS, look for help on the forums.  

## Home Assistant first time setup
1. Make sure your Home Assistant is using https.  This is important because
   calling a http (unsecure) site from a secure page is not allowed, nor advisable.
   You can configure caddy, nginx, Traefik, Tailscale, maybe even Home Assistant itself to use SSL/HTTPS.
2. Open your configuration.yaml file.
3. Add a section like this to allow the extension to call the HA REST API.
```
    http:
        cors_allowed_origins:
            - chrome-extension://dmapekhggdbdjoppelapaknlhkmdphbc
```
4. If you setup a https proxy like Traefik, you alwant to put this into the http-section:
```
    http:
        use_x_forwarded_for: true
        trusted_proxies:
            - <your-proxy-IP>
```
5. Restart Home Assistant

## In case you want to try Traefik

In the addons directory you will find a docker-compose file and static setup for proxying Home Assistant.  Try it out.  Then read about Traefik and never ever expose your Home Assistant directly to the Internet.  Use Tailscale or Nabucasa for this.

Some use apache, nginx, caddy, Traefik, NabuCasa.
There is a thread here which may help too: [https://community.home-assistant.io/t/connecting-to-ha-locally-using-https/566441/50](https://community.home-assistant.io/t/connecting-to-ha-locally-using-https/566441/50)

## Chrome installation first time use
1. Download the files for the extension
2. In chrome go to [Chrome extensions](chrome://extensions/)
3. Enable "developer mode"
4. Click "load unpacked"/"indlæs upakket" and browser to the directory `ha-novafos-token`.  Press the okay button.
5. The extension should be added to Chrome now.
6. Click the little 'puzzle piece' and pin the extension.

Will I publish the extension on the Chrome store? No.

## First time configuration
1. Click the extension and a small popup window will appear.
2. Enter your Home Assistant HTTPS URL (no trailing /, please): ```https://homeassist.my.home```
3. Enter your Home Assistant long lived access token: ```eyJhbGciOiJIU....```
4. Click the "Check this box ...".

# 🎯 How to Use

## Daily use
1. Go to novafos.dk, and login as you would normally using user/pass or MitID. I strongly recommend using a password manager like Bitwarden/Vaultwarden.
2. The extension will show a little "OK" badge when a token is detected.
3. Click the extension icon to open the popup
4. Click the "Send token to home assistant" button.
5. Data in Home Assistant should now update directly.

# 🔑 Key Features
- Enables much easier update of Novafos water/heating use data in Home Assistant.
- Enables extraction of Bearer tokens in general, though function is specialised for Home Assistant and the Novafos module.

# 🌐 Browser support
Available for Chrome, maybe Firefox, Edge, Chromium.  I don't know.