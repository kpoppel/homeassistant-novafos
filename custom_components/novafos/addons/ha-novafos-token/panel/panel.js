// panel.js
// UIkit: https://getuikit.com/docs/

// uses "options" from options.js
const outputContainer = document.getElementById("output-container");

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

function updateHomeAssistantEntity(entityId, newState) {
  // Curl line:
  // curl -X POST -H "Authorization: Bearer TOKEN" \
  //              -H "Content-Type: application/json" \
  //              -d "{\"state\": \"2024-09-05T23:59:59+02:00\", 
  //                   \"attributes\": {\"token\": \"I am the value\"}}"
  //              http://x.x.x.x:8123/api/states/sensor.novafos_valid_date_for_data
  // For HASS test
  //const HAUrl = 'http://x.x.x.x:8123/api/states/'+entityId;
  //const HAtoken = 'eyyadayada';
  // For production instance:
  //const HAUrl = 'https://hass.mydomain.lan/api/states/'+entityId;
  //const HAUrl = 'https://hass.mydomain.lan/api/states/sensor.novafos_valid_date_for_data'
  //const HAtoken = 'eyyadayada';
  //
  // entityId can be dropped when I expand the Novafos plugin in HA to have a service call endpoint.
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

  fetch(options.ha_url, {
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
  const outputContainer = document.getElementById("output-container");
  tokens.forEach((token) => {
    const container = document.createElement("div");
    container.classList.add("uk-margin");
    const card = document.createElement("div");
    card.classList.add("uk-card", "uk-card-default", "uk-card-body");

    const urlTitle = document.createElement("h6");
    urlTitle.classList.add("uk-card-title", "uk-text-default");
    urlTitle.innerText = token.url;

    const tokenValue = document.createElement("textarea");
    tokenValue.classList.add(
      "uk-textarea",
      "uk-form-small",
//      "uk-width-1-1",
      "uk-width-2xlarge"
    );
    tokenValue.innerText = getToken(token);

    const buttonContainer = document.createElement("div");
    const inspectButton = document.createElement("button");
    inspectButton.classList.add(
      "uk-button",
      "uk-margin-right",
      "uk-button-primary",
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

    // Create a button to send the token to Home Assistant
    // Manual for now - it could be done automatically as the token is found
    // whenever the Novafos page is updated.
    const curlValue = document.createElement("textarea");
    curlValue.classList.add(
      "uk-textarea",
      "uk-form-small",
//      "uk-width-1-1",
      "uk-width-2xlarge"
    );
    curlValue.innerText = getCurlCommand(token);

    const webhookButton = document.createElement("button");
    webhookButton.classList.add(
      "uk-button",
      "uk-button-secondary",
      "uk-text-default",
      "uk-text-capitalize",
      "uk-margin-top",
    );
    webhookButton.innerText = "Send token to Home Assistant";
    webhookButton.addEventListener("click", () => {
      updateHomeAssistantEntity('sensor.novafos_valid_date_for_data', getToken(token));

      const notificationContainer = (document.getElementById(
        "notification-container",
      ).innerHTML = "Token sent to Home Assistant.");
      setTimeout(() => {
        notificationContainer.innerHTML = "";
      }, 3000);
    });

    container.appendChild(card);
    card.appendChild(urlTitle);
    card.appendChild(tokenValue);
    card.appendChild(curlValue);
    buttonContainer.appendChild(inspectButton);
    buttonContainer.appendChild(copyButton);
    buttonContainer.appendChild(webhookButton);
    card.appendChild(buttonContainer);
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
         '" -H "Content-Type: application/json" -d "{\\"state\\": \\"' + isoDate +
         '\\", \\"attributes\\": {\\"token\\": \\"' +
         token.authorizationHeader.replace("Bearer ", "") +
         '\\"}}" ' + options.ha_url
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
  outputContainer.innerHTML = "";

  chrome.devtools.network.getHAR(function (requests) {
    const tokens = extractTokensFromHAR(requests);
    displayTokens(tokens);
    /*
    Here update Home Assistant with token using a sensor update in the Novafos plugin:
    rest_command:
      update_webhook_sensor:
        url: https://my_home_assistant_url/api/states/{{sensor_id}}
        method: POST
        headers:
          authorization: !secret ha_secret_bearer_token
        payload: '{"state":"{{state}}", "attributes":{{attributes_json}} }'
        content_type:  'application/json; charset=utf-8'
        verify_ssl: true

      A state update could have the key in the attributes so it does not get stored
      in the state database.

      Using a Service/custom action:
      Docs:
      https://developers.home-assistant.io/docs/api/rest/
      https://developers.home-assistant.io/docs/dev_101_services/
      Example: 
         https://github.com/phanmemkhoinghiep/homeassistant/blob/0ee37638cb05ae6c6ae0aa7522d51adf042cf487/custom_components/tts_ggcloud/__init__.py#L30

      If I can get the Novafos plugin to have a service hook:
      curl \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer TOKEN" \
        -d '{"token": "NOVAFOS-TOKEN"}' \
        http://localhost:8123/api/services/novafos/token

      curl -H "Authorization: Bearer eyyadayada" -H "Content-Type: application/json" http://x.x.x.x:8123/api/services
    */
  });
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
updatePanel();
