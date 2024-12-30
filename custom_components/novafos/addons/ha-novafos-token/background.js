// Can this be used to not even having to open DevTools?
// https://developer.mozilla.org/en-US/docs/Mozilla/Add-ons/WebExtensions/Background_scripts

// File loaded from configuration in manifest.json file.
function setDebugMode(mode) { 
    console.log("Debug mode changed " + mode );
 }

// Watch for changes to the user's options & apply them
chrome.storage.onChanged.addListener((changes, area) => {
  if (area === 'local' && changes.options?.newValue) {
    console.log(changes.options.newValue);
    const debugMode = Boolean(changes.options.newValue.debug_mode_toggle);
    console.log('enable debug mode?', debugMode);
    setDebugMode(debugMode);
    updatePanel();
  }
});