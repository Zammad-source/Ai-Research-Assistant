"use client";

import Image from "next/image";
import { MobileNav } from "@/components/layout/MobileNav";
import { APP_NAME } from "@/lib/constants";

export function Header() {
  return (
    <header className="h-16 shrink-0 border-b border-border bg-card flex items-center gap-3 px-4 sticky top-0 z-10 relative">
      <MobileNav />
      <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 flex items-center gap-2">
        <Image src="/logo.png" alt="" width={28} height={28} className="shrink-0" priority />
        <span className="font-heading font-bold text-lg text-blue-600">{APP_NAME}</span>
      </div>
    </header>
  );
}