"use client";

import Link from "next/link";
import { useRouter, usePathname } from "next/navigation";
import { Menu, Plus, Search, History, Settings } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import {
  Sheet,
  SheetTrigger,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { useUIStore } from "@/store/ui-store";
import { useConversationsStore } from "@/store/conversations";
import { APP_NAME, NAV_ITEMS, SECONDARY_NAV_ITEMS } from "@/lib/constants";

const ICONS = {
  search: Search,
  history: History,
  settings: Settings,
} as const;

export function MobileNav() {
  const router = useRouter();
  const pathname = usePathname();
  const isMobileNavOpen = useUIStore((s) => s.isMobileNavOpen);
  const setMobileNavOpen = useUIStore((s) => s.setMobileNavOpen);
  const createConversation = useConversationsStore((s) => s.createConversation);

  function handleNewConversation() {
    createConversation();
    setMobileNavOpen(false);
    router.push("/research");
  }

  return (
    <Sheet open={isMobileNavOpen} onOpenChange={setMobileNavOpen}>
      <SheetTrigger
        render={
          <Button variant="ghost" size="icon" className="md:hidden" aria-label="Open menu" />
        }
      >
        <Menu className="h-5 w-5" aria-hidden="true" />
      </SheetTrigger>
      <SheetContent side="left" className="w-72 gap-4">
        <SheetHeader>
          <SheetTitle>{APP_NAME}</SheetTitle>
        </SheetHeader>

        <div className="px-4 flex flex-col gap-4">
          <Button
            variant="outline"
            className="w-full justify-start gap-2"
            size="sm"
            onClick={handleNewConversation}
          >
            <Plus className="h-4 w-4" aria-hidden="true" />
            New Conversation
          </Button>

          <nav className="flex flex-col gap-1" aria-label="Main">
            {NAV_ITEMS.map((item) => {
              const Icon = ICONS[item.icon as keyof typeof ICONS];
              const active = pathname?.startsWith(item.href);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={() => setMobileNavOpen(false)}
                  aria-current={active ? "page" : undefined}
                  className={cn(
                    "flex items-center gap-3 rounded-md px-3 py-3 text-sm font-medium min-h-[44px] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
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

          <Separator />

          <nav className="flex flex-col gap-1" aria-label="Secondary">
            {SECONDARY_NAV_ITEMS.map((item) => {
              const Icon = ICONS[item.icon as keyof typeof ICONS];
              const active = pathname?.startsWith(item.href);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={() => setMobileNavOpen(false)}
                  aria-current={active ? "page" : undefined}
                  className="flex items-center gap-3 rounded-md px-3 py-3 text-sm font-medium min-h-[44px] text-muted-foreground hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  {Icon && <Icon className="h-4 w-4 shrink-0" aria-hidden="true" />}
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </div>
      </SheetContent>
    </Sheet>
  );
}