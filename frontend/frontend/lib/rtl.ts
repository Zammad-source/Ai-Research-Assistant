// lib/rtl.ts

/**
 * Checks if a string contains Urdu, Arabic, Persian, or Pashto characters
 * to determine if the text direction should be RTL.
 */
export function isRtlText(text: string): boolean {
  if (!text) return false;
  // Unicode range for Arabic, Urdu, Persian, Pashto scripts
  const rtlRegex = /[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]/;
  return rtlRegex.test(text);
}

/**
 * Returns the appropriate text direction ('rtl' or 'ltr') based on content.
 */
export function getTextDirection(text: string): "rtl" | "ltr" {
  return isRtlText(text) ? "rtl" : "ltr";
}