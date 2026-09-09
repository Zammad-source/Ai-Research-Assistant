"use client";

import { useState, useEffect } from "react";
import { WifiOff } from "lucide-react";

export function ConnectionStatusBar() {
 const [isOnline, setIsOnline] = useState(() =>
  typeof window !== "undefined" ? navigator.onLine : true
);

  useEffect(() => {
    function handleOnline() { setIsOnline(true); }
    function handleOffline() { setIsOnline(false); }

    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);

    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, []);

  if (isOnline) return null;

  return (
    <div
      role="status"
      aria-live="polite"
      className="animate-connection-bar-in bg-destructive text-destructive-foreground px-4 py-2 text-xs font-medium flex items-center justify-center gap-2 shadow-md transition-all"
    >
      <WifiOff className="h-4 w-4 shrink-0 animate-status-dot-pulse" aria-hidden="true" />
      <span>You are currently offline. Check your internet connection. AI responses may fail.</span>
    </div>
  );
}
