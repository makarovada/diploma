import { useState, type ReactNode } from "react";
import { useTheme } from "@/app/providers";
import { AppSidebar } from "@/components/app-sidebar";
import { AppTopbar } from "@/components/app-topbar";
import { MobileNavDrawer } from "@/components/mobile-nav-drawer";

export function MainShell({ children }: { children: ReactNode }) {
  const { dark, toggle } = useTheme();
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  return (
    <div className="flex h-screen w-full bg-background text-foreground">
      <AppSidebar dark={dark} onToggleTheme={toggle} />
      <MobileNavDrawer open={mobileNavOpen} onClose={() => setMobileNavOpen(false)} dark={dark} onToggleTheme={toggle} />
      <div className="flex min-w-0 flex-1 flex-col">
        <AppTopbar onOpenMobileNav={() => setMobileNavOpen(true)} />
        <main className="min-h-0 flex-1 overflow-auto">{children}</main>
      </div>
    </div>
  );
}
