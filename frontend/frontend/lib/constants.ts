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

export const WS_URL =
  process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000";