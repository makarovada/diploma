import { useEffect, useState, type ReactNode } from "react";
import { useTheme } from "@/app/providers";
import { AppSidebar } from "@/components/app-sidebar";
import { AppTopbar } from "@/components/app-topbar";
import { CommandPalette } from "@/components/command-palette";
import { MobileNavDrawer } from "@/components/mobile-nav-drawer";

export function MainShell({ children }: { children: ReactNode }) {
  const { dark, toggle } = useTheme();
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [commandOpen, setCommandOpen] = useState(false);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setCommandOpen(true);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  return (
    <div className="flex h-screen w-full bg-background text-foreground">
      <AppSidebar dark={dark} onToggleTheme={toggle} />
      <MobileNavDrawer open={mobileNavOpen} onClose={() => setMobileNavOpen(false)} dark={dark} onToggleTheme={toggle} />
      <div className="flex min-w-0 flex-1 flex-col">
        <AppTopbar onOpenMobileNav={() => setMobileNavOpen(true)} onOpenCommandPalette={() => setCommandOpen(true)} />
        <main className="min-h-0 flex-1 overflow-auto">{children}</main>
      </div>
      <CommandPalette open={commandOpen} onClose={() => setCommandOpen(false)} />
    </div>
  );
}
