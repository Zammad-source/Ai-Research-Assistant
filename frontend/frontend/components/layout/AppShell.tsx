import { Sidebar } from "@/components/layout/Sidebar";
import { Header } from "@/components/layout/Header";
import { ConnectionStatusBar } from "@/components/layout/ConnectionStatusBar";

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-dvh">
      <Sidebar />
      <div className="flex flex-1 flex-col min-w-0">
        <Header />
        <ConnectionStatusBar />
        <main className="flex-1 min-w-0">{children}</main>
      </div>
    </div>
  );
}