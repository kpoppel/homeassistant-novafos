# 🚀 Retrieve a Bearer token from Novafos website and inject into Home Assistant
This extension is used with the DevTools (F12) function of Chrome.  When logging into
Novafos using either email/password or MitID (keep devtools closed during the login process),
this extension will inspect headers from network traffic and present the user with choices
to copy the token, inspect it using jwt.io site, or send it to Home Assistant.

The source code is open for verification.

## 🎯 How to Use

### Home Assistant first time setup
1. Make sure your Home Assistant is using https.  This is important because
   calling a http (unsecure) site from a secure page is not allowed, nor advisable.
   You can configure caddy, nginx, Traefik, Tailscale, maybe even Home Assistant itself to use SSL/HTTPS.
2. Open your configuration.yaml file.
3. Add a section like this to allow the extension to call the HA REST API.
```
    http:
        cors_allowed_origins:
            - chrome-extension://kjgeibilkbfcionaigcomacomgpmjfgh
```
5. If you setup a https proxy like Traefik, you alwant to put this into the http-section:
```
    http:
        use_x_forwarded_for: true
        trusted_proxies:
            - <your-proxy-IP>
```
6. Restart Home Assistant

#### In case you want to try Traefik

In the addons directory you will find a docker-compose file and static setup for proxying Home Assistant.  Try it out.  Then read about Traefik and never ever expose your Home Assistant directly to the Internet.  Use Tailscale or Nabucasa for this.

### Chrome installation first time use
1. Download the files for the extension
2. In chrome go to [Chrome extensions](chrome://extensions/)
3. Enable "developer mode"
4. Click the "Load unpacked" button and navigate to the directory with these files.
5. The extension should be added to Chrome now.

Will I publish the extension on the Chrome store? No.

### Chrome use
1. Go to novafos.dk, and login as you would normally using user/pass or MitID
2. Open Chrome DevTools after the page loads
2. Locate the Novafos Token Inspector panel (similar to Console, Network, or Application panels)
3. Reload the page.
4. The extension only looks for Bearer tokens and present all unique tokens.
5. Find your tokens effortlessly, and send them to Home Assistant

## 🔑 Key Features
- Enables much easier update of Novafos water/heating use data in Home Assistant.
- Enables extraction of Bearer tokens in general, though function is specialised for Home Assistant and the Novafos module.

## 🌐 Browser support
Available for Chrome, maybe Firefox, Edge, Chromium.  I don't know.
