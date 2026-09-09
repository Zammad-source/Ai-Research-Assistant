"use client"

import type { ConnectionStatus } from "@/types/translator"
import { cn } from "@/lib/utils"

interface ConnectionStatusIndicatorProps {
  status: ConnectionStatus
}

const STATUS_CONFIG: Record<ConnectionStatus, { label: string; className: string }> = {
  disconnected: { label: "Disconnected", className: "text-muted-foreground" },
  connecting: { label: "Connecting…", className: "text-yellow-600" },
  connected: { label: "Connected", className: "text-green-600" },
  reconnecting: { label: "Reconnecting…", className: "text-yellow-600" },
  error: { label: "Connection Error", className: "text-destructive" },
}

export function ConnectionStatusIndicator({ status }: ConnectionStatusIndicatorProps) {
  const config = STATUS_CONFIG[status]

  return (
    <div className="flex items-center gap-2 text-xs font-medium" role="status" aria-live="polite">
      <span
        className={cn(
          "w-2.5 h-2.5 rounded-full",
          status === "connected"
            ? "bg-green-500 animate-status-dot-pulse"
            : status === "reconnecting" || status === "connecting"
              ? "bg-yellow-500 animate-pulse"
              : status === "error"
                ? "bg-destructive"
                : "bg-muted-foreground/40"
        )}
      />
      <span className={config.className}>{config.label}</span>
    </div>
  )
}