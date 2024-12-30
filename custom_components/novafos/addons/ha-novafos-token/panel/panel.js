// panel.js
// UIkit: https://getuikit.com/docs/

// uses "options" from options.js
const outputContainer = document.getElementById("output-container");
const setupContainer = document.getElementById("setup-container");

function extractTokensFromHAR(requests) {
  return requests.entries
  // Filter requests which has the "authorization" header
  .filter((entry) =>
      entry.request.headers.some(
        (header) => header.name.toLowerCase() === "authorization",
      ),
    )
    // Remove duplicate token values regardless of which URL they came from
    // Note: The reduce uses a two element array to temporarily store keys
    // Hence the following [0] to remove the temporary data
    .reduce((total, current) => {
      const authorizationHeader = current.request.headers.find(
        (header) => header.name.toLowerCase() === "authorization",
      ).value;
      if (!total[1].includes(authorizationHeader)) {
        total[0].push(current);
        total[1].push(authorizationHeader);
      }
      return total;
    }, [[],[]])[0]
    // Finally make a map including only url and the auth header
    // For Home Assistant not really needed as the URL is don't care.
    .map((entry) => {
      const url = entry.request.url;
      const authorizationHeader = entry.request.headers.find(
        (header) => header.name.toLowerCase() === "authorization",
      ).value;
      return { url, authorizationHeader };
    });
}

function callHomeAssistantService(access_token) {
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
  headers.append('Authorization', 'Bearer ' + options.ha_token);

  fetch(options.ha_url + "/api/services/novafos/update_token", {
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

function updateHomeAssistantEntity(entityId, newState) {
  // This function just serves as an example to update a (any) entity with new attributes from JavaScript)
  //  I leave it here for myself, but it was used before adding the action service to the HA extension.
  date = new Date();
  isoDate = date.toISOString(); // 2024-09-06T23:27:56.592Z

  const data = {
    state: isoDate,
    attributes: {
      device_class: 'date',
      icon: 'mdi:calendar',
      friendly_name: 'Novafos Valid Date for data',
      token: newState
    }
  };

  let headers = new Headers();
  headers.append('Content-Type', 'application/json');
  headers.append('Accept', 'application/json');
  headers.append('Authorization', 'Bearer ' + options.ha_token);

  fetch(options.ha_url + "/api/states/" + entityId, {
      mode: 'cors',
      method: 'POST',
      headers: headers,
      body: JSON.stringify(data)
  })
  .then(response => response.json())
  .then(json => console.log(json))
  .catch(error => console.log('Authorization failed: ' + error.message));
}

function displayTokens(tokens) {
  tokens.forEach((token) => {
    const container = document.createElement("div");
    container.classList.add("uk-margin");
    const card = document.createElement("div");
    card.classList.add("uk-card", "uk-card-default", "uk-card-body");
    const buttonContainer = document.createElement("div");
    const urlTitle = document.createElement("h6");
    urlTitle.classList.add("uk-card-title", "uk-text-default");
    urlTitle.innerText = token.url;

    container.appendChild(card);
    card.appendChild(urlTitle);
    card.appendChild(buttonContainer);

    // Create a button to send the token to Home Assistant
    const webhookButton = document.createElement("button");
    webhookButton.classList.add(
      "uk-button",
      "uk-button-primary",
      "uk-text-default",
      "uk-text-capitalize",
      "uk-margin-top",
    );
    webhookButton.innerText = "Send token to Home Assistant";
    webhookButton.addEventListener("click", () => {
      // If updating an entity:
      //updateHomeAssistantEntity('sensor.novafos_valid_date_for_data', getToken(token));
      callHomeAssistantService(getToken(token))
      const notificationContainer = (document.getElementById(
        "notification-container",
      ).innerHTML = "Token sent to Home Assistant.");
      setTimeout(() => {
        notificationContainer.innerHTML = "";
      }, 3000);
    });
    buttonContainer.appendChild(webhookButton);

    // Stuff turned on if debug switch is checked.
    if (options.debug_mode_toggle) {
      // Create a field with the token value
      const tokenValue = document.createElement("textarea");
      tokenValue.classList.add(
        "uk-textarea",
        "uk-form-small",
        "uk-width-2xlarge"
      );
      tokenValue.innerText = getToken(token);
      card.appendChild(tokenValue);

      // Create a field with a curl command to sent to Home Assistant for manual testing or if it is not using HTTPS.
      const curlValue = document.createElement("textarea");
      curlValue.classList.add(
        "uk-textarea",
        "uk-form-small",
        "uk-width-2xlarge"
      );
      curlValue.innerText = getCurlCommand(token);
      card.appendChild(curlValue);

      // Create a button to copy the token to clipboard
      const copyButton = document.createElement("button");
      copyButton.classList.add(
        "uk-button",
        "uk-button-secondary",
        "uk-text-default",
        "uk-text-capitalize",
        "uk-margin-top",
      );
      copyButton.innerText = "Copy token";
      copyButton.addEventListener("click", () => {
        copyToClipboard(getToken(token));
        const notificationContainer = (document.getElementById(
          "notification-container",
        ).innerHTML = "Token copied successfully.");
        setTimeout(() => {
          notificationContainer.innerHTML = "";
        }, 3000);
      });

      // Create a button to send the token for some inspection at jwt.io
      const inspectButton = document.createElement("button");
      inspectButton.classList.add(
        "uk-button",
        "uk-margin-right",
        "uk-button-secondary",
        "uk-text-default",
        "uk-text-capitalize",
        "uk-margin-top",
      );
      inspectButton.innerText = "Inspect token in jwt.io";
      inspectButton.addEventListener("click", () => {
        const jwtInspectUrl = `https://jwt.io/?token=${encodeURIComponent(
          getToken(token),
        )}`;
        window.open(jwtInspectUrl, "_blank");
      });

      buttonContainer.appendChild(copyButton);
      buttonContainer.appendChild(inspectButton);
    }

    // Add all elements to the panel
    outputContainer.appendChild(container);
  });
}

function getToken(token) {
  // Return the token with or without the Bearer word.
  return options.include_bearer_toggle
    ? token.authorizationHeader
    : token.authorizationHeader.replace("Bearer ", "");
}

function getCurlCommand(token) {
  const isoDate = new Date().toISOString(); // 2024-09-06T23:27:56.592Z
  return 'curl -X POST -H "Authorization: Bearer ' + options.ha_token +
         '" -H "Content-Type: application/json" -d "{\\"access_token\\": \\"' +
         token.authorizationHeader.replace("Bearer ", "") +
         '\\"}" ' + options.ha_url + "/api/services/novafos/update_token"
}

function copyToClipboard(text) {
  // This is how it should work using the navigator class.  But this is not implemented.
  //  navigator.clipboard.writeText(text);

  // Instead use the execCommand which is deprecated for some time...
  const textField = document.createElement("textarea");
  textField.innerText = text;
  document.body.appendChild(textField);
  textField.select();
  document.execCommand("copy");
  textField.remove();
}

function updatePanel() {
  // Clear panel
  setupContainer.style.display = 'none';
  outputContainer.innerHTML = "";

  // Display setup area if the setup checkbox is unchecked
  if (!options.setup_toggle) {
    //console.log("Setup not completed")
    setupContainer.style.display = 'block';
  } else {
    //console.log("Setup was completed, ready to go.")

    chrome.devtools.network.getHAR(function (requests) {
      const tokens = extractTokensFromHAR(requests);
      displayTokens(tokens);
    });
  }
}

/* Entry point code */
function handleRequestFinished(request) {
  const hasToken = request.request.headers.some((header) => {
    return header.name.toLowerCase() === "authorization";
  });

  if (hasToken) {
    updatePanel();
  }
}

chrome.devtools.network.onRequestFinished.addListener(handleRequestFinished);

