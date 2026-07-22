import {
  DEFAULT_ORBYTE_DOMAIN,
  CHROME_SPECIFIC_STORAGE_KEYS,
} from "./constants.js";

export async function getOrbyteDomain() {
  const result = await chrome.storage.local.get({
    [CHROME_SPECIFIC_STORAGE_KEYS.ORBYTE_DOMAIN]: DEFAULT_ORBYTE_DOMAIN,
  });
  return result[CHROME_SPECIFIC_STORAGE_KEYS.ORBYTE_DOMAIN];
}

export function setOrbyteDomain(domain, callback) {
  chrome.storage.local.set(
    { [CHROME_SPECIFIC_STORAGE_KEYS.ORBYTE_DOMAIN]: domain },
    callback
  );
}

export function getOrbyteDomainSync() {
  return new Promise((resolve) => {
    getOrbyteDomain(resolve);
  });
}
