import { X } from "lucide-react";
import { SidebarContent } from "@/components/sidebar-content";
import { Button } from "@/components/ui/button";

export function MobileNavDrawer({
  open,
  onClose,
  dark,
  onToggleTheme,
}: {
  open: boolean;
  onClose: () => void;
  dark: boolean;
  onToggleTheme: () => void;
}) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 lg:hidden" data-testid="mobile-nav-drawer">
      <button type="button" className="absolute inset-0 bg-black/40" aria-label="Закрыть меню" onClick={onClose} data-testid="mobile-nav-backdrop" />
      <div className="absolute inset-y-0 left-0 flex w-[min(100vw,20rem)] flex-col border-r bg-card shadow-lg">
        <div className="flex items-center justify-end border-b p-2">
          <Button type="button" variant="ghost" className="px-2" onClick={onClose} data-testid="button-close-mobile-nav" aria-label="Закрыть">
            <X className="h-5 w-5" />
          </Button>
        </div>
        <div className="flex-1 overflow-y-auto p-4">
          <SidebarContent dark={dark} onToggleTheme={onToggleTheme} onNavigate={onClose} />
        </div>
      </div>
    </div>
  );
}
