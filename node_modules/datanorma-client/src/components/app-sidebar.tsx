import { SidebarContent } from "@/components/sidebar-content";

export function AppSidebar({
  dark,
  onToggleTheme,
}: {
  dark: boolean;
  onToggleTheme: () => void;
}) {
  return (
    <aside className="hidden w-72 shrink-0 overflow-y-auto border-r bg-card p-4 lg:block" data-testid="sidebar-main">
      <SidebarContent dark={dark} onToggleTheme={onToggleTheme} />
    </aside>
  );
}
