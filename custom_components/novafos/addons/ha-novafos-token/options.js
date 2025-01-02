const optionsForm = document.getElementById("optionsForm");
const setupForm = document.getElementById("setupForm");
const developerForm = document.getElementById("developerForm");

// First input form with the checkbox for hiding the setup options
optionsForm.setup_toggle.addEventListener("change", (event) => {
    chrome.storage.local.set({ "setup_toggle": event.target.checked });

    // Toggle forms between setup and token detection
    const setupContainer = document.getElementById("setup-container");
    const outputContainer = document.getElementById("output-container");

    if (event.target.checked) {
        setupContainer.style.display = 'none';
        outputContainer.style.display = 'block';
        developerContainer.style.display = 'none';
    } else {
        setupContainer.style.display = 'block';
        outputContainer.style.display = 'none';
        developerContainer.style.display = 'none';
        if (setupForm.debug_mode_toggle.checked) {
            developerContainer.style.display = 'block';
        }    
    }
    console.log("Setup toggle updated to "+event.target.checked);
});

// Next input form with the setup options
// Immediately persist options changes
setupForm.ha_url.addEventListener("change", (event) => {
    chrome.storage.local.set({ "ha_url": event.target.value });
    console.log("HA URL updated to "+event.target.value);
});

setupForm.ha_token.addEventListener("change", (event) => {
    chrome.storage.local.set({ "ha_token": event.target.value });
    console.log("HA token updated to "+event.target.value);
});

setupForm.debug_mode_toggle.addEventListener("change", (event) => {
    chrome.storage.local.set({ "debug_mode_toggle": event.target.checked });
    console.log("Debug option updated to "+event.target.checked);

    // Toggle forms between setupa and token detection
    const developerContainer = document.getElementById("developer-container");

    if (event.target.checked) {
        developerContainer.style.display = 'block';
    } else {
        developerContainer.style.display = 'none';
    }
});

developerForm.ha_url_dev.addEventListener("change", (event) => {
    chrome.storage.local.set({ "ha_url_dev": event.target.value });
    console.log("HA DEV URL updated to "+event.target.value);
});

developerForm.ha_token_dev.addEventListener("change", (event) => {
    chrome.storage.local.set({ "ha_token_dev": event.target.value });
    console.log("HA DEV token updated to "+event.target.value);
});

developerForm.include_bearer_toggle.addEventListener("change", (event) => {
    chrome.storage.local.set({ "include_bearer_toggle": event.target.checked });
    console.log("Include bearer toggle updated to "+event.target.checked);
});

function initOptions() {
    chrome.runtime.sendMessage({message: "getOptions"}, function(response) {
        // Run every time the popup is shown.
        if (chrome.runtime.lastError) {
            console.error(chrome.runtime.lastError);
            return;
        }

        // Initialize the form with the user's option settings and update global options variable.
        optionsForm.setup_toggle.checked = Boolean(response.setup_toggle);
        setupForm.ha_url.value = response.ha_url;
        setupForm.ha_token.value = response.ha_token;
        setupForm.debug_mode_toggle.checked = Boolean(response.debug_mode_toggle);
        developerForm.ha_url_dev.value = response.ha_url_dev;
        developerForm.ha_token_dev.value = response.ha_token_dev;
        developerForm.include_bearer_toggle.checked = Boolean(response.include_bearer_toggle);
      });
};

initOptions();
console.log("InitOptions completed");
