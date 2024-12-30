// In-page cache of the user's options
const options = {};
const optionsForm = document.getElementById("optionsForm");

// Immediately persist options changes
optionsForm.include_bearer_toggle.addEventListener("change", (event) => {
    options.include_bearer_toggle = event.target.checked;
    chrome.storage.local.set({ options });
    updatePanel();
    console.log("Include bearer toggle updated to "+options.include_bearer_toggle);
});

optionsForm.debug_mode_toggle.addEventListener("change", (event) => {
    options.debug_mode_toggle = event.target.checked;
    chrome.storage.local.set({ options });
    console.log("Option updated to "+options.debug_mode_toggle);
});

optionsForm.ha_url.addEventListener("change", (event) => {
    options.ha_url = event.target.value;
    chrome.storage.local.set({ options });
 
    console.log("HA URL updated to "+options.ha_url);
});

optionsForm.ha_token.addEventListener("change", (event) => {
    options.ha_token = event.target.value;
    chrome.storage.local.set({ options });
 
    console.log("HA token updated to "+options.ha_token);
});

async function initOptions() {
    // Initialize the form with the user's option settings and update global options variable.
    const data = await chrome.storage.local.get("options");
    Object.assign(options, data.options);
    optionsForm.include_bearer_toggle.checked = Boolean(options.include_bearer_toggle);
    optionsForm.debug_mode_toggle.checked = Boolean(options.debug_mode_toggle);
    optionsForm.ha_url.value = options.ha_url;
    optionsForm.ha_token.value = options.ha_token;
};

initOptions();
