// background.js
let tokenFound = false;
let currentTabId = null;

function handleTokenFound() {
  // Update the badge on the icon
  if (!tokenFound) {
    tokenFound = true;
    chrome.action.setBadgeText({ text: "Ok" });
    chrome.action.setBadgeBackgroundColor({ color: "#008000" });
  }
}

chrome.webNavigation.onCommitted.addListener(function (details) {
  // Clear the badge on navigation
  if (details.frameId === 0) {
    tokenFound = false;
    chrome.action.setBadgeText({ text: "" }); // Clear badge
  }
});

/* *************************** */
/* Clear the token data if user navigates away from the tab where the token ws found */
/* *************************** */
function clearTokenData() {
  // Clear the token data
  chrome.storage.local.remove(["token", "url"], function () {
    if (chrome.runtime.lastError) {
      console.error("Storage error:", chrome.runtime.lastError);
    } else {
      console.log("Token data cleared.");
    }
  });
  tokenFound = false;
  chrome.action.setBadgeText({ text: "" });
}

// chrome.tabs.onActivated.addListener(function(activeInfo) {
//   // Clear token data when another tab is activated
//   if (currentTabId !== null && activeInfo.tabId !== currentTabId) {
//       clearTokenData();
//       currentTabId = activeInfo.tabId;
//   }
// });

chrome.tabs.onRemoved.addListener(function (tabId) {
  // Clear token data when the tab with the token is closed
  if (currentTabId === tabId) {
    clearTokenData();
    currentTabId = null;
  }
});

/* *************************** */
/* Listeners for headers sent and received from which to extract tokens */
/* *************************** */
chrome.webRequest.onBeforeSendHeaders.addListener(
  async function (details) {
    if (details.tabId === -1) {
      return; // Ignore requests not associated with a tab (e.g., background requests)
    }
    for (const header of details.requestHeaders) {
      if (header.name === "Authorization" && header.value.startsWith("Bearer ")) {
        const token = header.value.substring("Bearer ".length);
        console.log("Found Bearer token (onBeforeSendHeaders):", token, "URL:", details.url);
        if (token) {
          // Store the token, send it to a popup, etc.
          await chrome.storage.local.set({ "token": token, "url": details.url });
          handleTokenFound();
          currentTabId = details.tabId; // Update the current tab ID
          break;
        }
      }
    }
  },
  { urls: ["<all_urls>"] }, // Filter URLs if possible
  ["requestHeaders"]
);

chrome.webRequest.onHeadersReceived.addListener(
  async function (details) {
    if (details.tabId === -1) {
      return; // Ignore requests not associated with a tab (e.g., background requests)
    }
    for (const header of details.responseHeaders) {
      if (header.name.toLowerCase() === "authorization" && header.value.toLowerCase().startsWith("bearer ")) {
        const token = header.value.substring("Bearer ".length);
        console.log("Found Bearer token (onHeadersReceived):", token, "URL:", details.url);
        if (token) {
          // Store the token, send it to a popup, etc.
          await chrome.storage.local.set({ "token": token, "url": details.url });
          handleTokenFound();
          currentTabId = details.tabId; // Update the current tab ID
          break;
        }
      }
    }
  },
  { urls: ["<all_urls>"] },
  ["responseHeaders"]
);

// Listener for the message sent from popup.js
// Then return the proper response to the sender.
chrome.runtime.onMessage.addListener(
  function (request, sender, sendResponse) {
    if (request.message === "getToken") {
      // The reponse uses the data stored by then in HeadersReceived and onBeforeSendHeaders above.
      chrome.storage.local.get(["token", "url"], function (result) {
        sendResponse({ token: result.token, url: result.url });
      });
      return true; // Important: Indicate response sent asynchronously
    }
    if (request.message === "getOptions") {
      chrome.storage.local.get(
        ["setup_toggle", "ha_url", "ha_token", "debug_mode_toggle", "ha_url_dev", "ha_token_dev", "include_bearer_toggle",],
         function (result) {
        sendResponse({
          "setup_toggle": result.setup_toggle,
          "ha_url": result.ha_url,
          "ha_token": result.ha_token,
          "debug_mode_toggle": result.debug_mode_toggle,
          "ha_url_dev": result.ha_url_dev,
          "ha_token_dev": result.ha_token_dev,
          "include_bearer_toggle": result.include_bearer_toggle
        });
      });
      return true; // Important: Indicate response sent asynchronously
    }
  }
);
