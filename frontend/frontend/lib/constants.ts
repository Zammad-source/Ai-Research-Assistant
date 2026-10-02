export const APP_NAME = "OmniVoice"; // placeholder brand name — rename freely

export const NAV_ITEMS = [
  { label: "Research Assistant", href: "/research", icon: "search" as const },
  { label: "Translator Mode", href: "/translator", icon: "messages-square" as const },
] as const;

export const SECONDARY_NAV_ITEMS = [
  { label: "History", href: "/history", icon: "history" as const },
  { label: "Settings", href: "/settings", icon: "settings" as const },
] as const;

export const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/**
 * Base URL for the translator WebSocket.
 *
 * NEXT_PUBLIC_WS_URL wins when set. Otherwise it is derived from API_URL so
 * there is only one value to configure per environment -- setting the API URL
 * and forgetting this one used to leave the translator silently pointing at
 * localhost in production.
 *
 * The scheme has to be upgraded to wss:// on https pages: browsers block
 * mixed content, so a ws:// socket on a Vercel URL never connects at all.
 */
function deriveWsUrl(apiUrl: string): string {
  if (apiUrl.startsWith("https://")) return `wss://${apiUrl.slice(8)}`;
  if (apiUrl.startsWith("http://")) return `ws://${apiUrl.slice(7)}`;
  return apiUrl;
}

export const WS_URL =
  process.env.NEXT_PUBLIC_WS_URL ?? deriveWsUrl(API_URL);