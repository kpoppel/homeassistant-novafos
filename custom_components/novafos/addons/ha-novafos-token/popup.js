// popup.js

// Setup the UI
console.log("Popup UI setup begin")
const setupContainer = document.getElementById("setup-container");
const outputContainer = document.getElementById("output-container");
const developerContainer = document.getElementById("developer-container");

chrome.runtime.sendMessage({message: "getOptions"}, function(options) {
  // Run every time the popup is shown.
  if (chrome.runtime.lastError) {
      console.error(chrome.runtime.lastError);
      return;
  }

  console.log("Options:")
  console.log(options);

  if (options.setup_toggle) {
      setupContainer.style.display = 'none';
      outputContainer.style.display = 'block';
      developerContainer.style.display = 'none';
  } else {
      setupContainer.style.display = 'block';
      outputContainer.style.display = 'none';
      developerContainer.style.display = 'none';
      if (options.debug_mode_toggle) {
        developerContainer.style.display = 'block';
      }
    }
});
console.log("Popup UI setup end")

// Send a message to the extension with a callback which in turn updates the popup content using
// the reponse from the listener in background.js.
// We'll use this to update the window once the wanted token is found.
chrome.runtime.sendMessage({message: "getToken"}, function(response) {
    // Run every time the popup is shown.
    if (chrome.runtime.lastError) {
        console.error(chrome.runtime.lastError);
        return;
    }
    if (response && response.token) {
        document.getElementById("token-url").innerText = "URL: " + response.url;
        document.getElementById("output-token").innerText = response.token;

        // Developer mode thing - add "Bearer" or not
        chrome.runtime.sendMessage({message: "getOptions"}, function(response) {
           if(response.include_bearer_toggle) {
              element = document.getElementById("output-token");
              element.innerText = "Bearer "+element.innerText;
           }
        });
    } else {
        document.getElementById("output-token").innerText = "No Bearer token found.";
    }
});

const webhookButton = document.getElementById("ha-button");
webhookButton.addEventListener("click", () => {
    // Send the token to the HA instance defined by having "developer mode" on or off
    chrome.runtime.sendMessage({message: "getOptions"}, function(options) {
        chrome.runtime.sendMessage({message: "getToken"}, function(response) {
            if(options.debug_mode_toggle) {
                // Use DEV configuration instead
                callHomeAssistantService(options.ha_url_dev, options.ha_token_dev, response.token)
            } else {
                // Use normal config
                callHomeAssistantService(options.ha_url, options.ha_token, response.token)
            }
        });
    });
    
    const notificationContainer = (document.getElementById(
        "notification-container",
    ).innerHTML = "Token sent to Home Assistant.");
    setTimeout(() => {
        notificationContainer.innerHTML = "";
    }, 3000);
});


function callHomeAssistantService(ha_url, ha_token, access_token) {
  // Call this function to access the HA Novafox update token action service.
  // Using a Service/custom action:
  // Docs:
  // https://developers.home-assistant.io/docs/api/rest/
  // https://developers.home-assistant.io/docs/dev_101_services/
  // Example: 
  //   https://github.com/phanmemkhoinghiep/homeassistant/blob/0ee37638cb05ae6c6ae0aa7522d51adf042cf487/custom_components/tts_ggcloud/__init__.py#L30
  const data = {
    access_token: access_token
  };

  let headers = new Headers();
  headers.append('Content-Type', 'application/json');
  headers.append('Accept', 'application/json');
  headers.append('Authorization', 'Bearer ' + ha_token);

  fetch(ha_url + "/api/services/novafos/update_token", {
      mode: 'cors',
      method: 'POST',
      headers: headers,
      body: JSON.stringify(data)
  })
  .then(response => response.json())
  .then(json => console.log(json))
  //.catch(error => console.log('Authorization failed: ' + error.message));
  .catch(error => {
    const notificationContainer = document.getElementById("notification-container");
    notificationContainer.classList = "uk-text-warning"
    notificationContainer.innerHTML = "Something went wrong: " + error.message;
    setTimeout(() => {
      notificationContainer.innerHTML = "";
      notificationContainer.classList = "uk-text-success";
    }, 3000);
  });
}
