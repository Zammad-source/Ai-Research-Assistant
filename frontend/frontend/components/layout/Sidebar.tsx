"use client";

import Link from "next/link";
import Image from "next/image";
import { useRouter, usePathname } from "next/navigation";
import { Plus, Search, History, Settings, MessageSquare } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { ScrollArea } from "@/components/ui/scroll-area";
import { ConversationsList } from "@/components/layout/ConversationsList";
import { useConversationsStore } from "@/store/conversations";
import { APP_NAME, NAV_ITEMS, SECONDARY_NAV_ITEMS } from "@/lib/constants";

const ICONS = {
  search: Search,
  history: History,
  settings: Settings,
  "messages-square": MessageSquare,
} as const;

export function Sidebar() {
  const router = useRouter();
  const pathname = usePathname();
  const createConversation = useConversationsStore((s) => s.createConversation);

  function handleNewConversation() {
    createConversation();
    router.push("/research");
  }

  return (
    <aside
      className="hidden md:flex md:w-64 md:flex-col border-e border-border bg-card h-dvh sticky top-0"
      aria-label="Sidebar navigation"
    >
     <div className="flex items-center gap-2 px-4 h-16 shrink-0">
  <Image src="/logo.png" alt="" width={28} height={28} className="shrink-0" priority />
  <span className="font-heading font-semibold text-base text-blue-600">{APP_NAME}</span>
     </div>

      <div className="px-3">
        <Button
          variant="outline"
          className="w-full justify-start gap-2"
          size="sm"
          onClick={handleNewConversation}
        >
          <Plus className="h-4 w-4" aria-hidden="true" />
          New Conversation
        </Button>
      </div>

      <nav className="mt-4 px-2 flex flex-col gap-1" aria-label="Main">
        {NAV_ITEMS.map((item) => {
          const Icon = ICONS[item.icon as keyof typeof ICONS];
          const active = pathname?.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              aria-current={active ? "page" : undefined}
              className={cn(
                "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                active
                  ? "bg-primary text-primary-foreground"
                  : "text-foreground hover:bg-muted"
              )}
            >
              {Icon && <Icon className="h-4 w-4 shrink-0" aria-hidden="true" />}
              {item.label}
            </Link>
          );
        })}
      </nav>

      <Separator className="my-3" />

      <div className="px-2">
        <h2 className="px-3 text-xs font-medium text-muted-foreground mb-1" id="recent-conversations-heading">
          Recent Conversations
        </h2>
        <ScrollArea className="h-40 px-1" aria-labelledby="recent-conversations-heading">
          <ConversationsList />
        </ScrollArea>
      </div>

      <div className="mt-auto px-2 pb-3 flex flex-col gap-1">
        <Separator className="mb-2" />
        {SECONDARY_NAV_ITEMS.map((item) => {
          const Icon = ICONS[item.icon as keyof typeof ICONS];
          const active = pathname?.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              aria-current={active ? "page" : undefined}
              className={cn(
                "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                active
                  ? "bg-muted text-foreground"
                  : "text-muted-foreground hover:bg-muted"
              )}
            >
              {Icon && <Icon className="h-4 w-4 shrink-0" aria-hidden="true" />}
              {item.label}
            </Link>
          );
        })}
      </div>
    </aside>
  );
}