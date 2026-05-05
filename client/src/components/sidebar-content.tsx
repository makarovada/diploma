import { Link, useLocation } from "wouter";
import { useAuth } from "@/app/auth-context";
import { cn } from "@/lib/utils";
import { navActive, navSections, type NavItem } from "@/lib/nav-config";

function navItemVisible(item: NavItem, isPlatformAdmin: boolean): boolean {
  if (item.platformAdminOnly && !isPlatformAdmin) {
    return false;
  }
  return true;
}

export function SidebarContent({
  dark,
  onToggleTheme,
  onNavigate,
}: {
  dark: boolean;
  onToggleTheme: () => void;
  onNavigate?: () => void;
}) {
  const [location] = useLocation();
  const { user } = useAuth();
  const isPlatformAdmin = Boolean(user?.roles?.includes("platform_admin"));

  return (
    <>
      <div className="mb-6">
        <p className="text-lg font-semibold">DataNorma</p>
        <p className="text-xs text-muted-foreground">Платформа интеграций</p>
        <label className="mt-3 block text-[11px] font-semibold uppercase tracking-wide text-muted-foreground" htmlFor="workspace-select">
          Рабочее пространство
        </label>
        <select
          id="workspace-select"
          className="mt-1 w-full rounded-md border bg-background px-2 py-1.5 text-sm"
          data-testid="select-workspace"
          defaultValue="main"
        >
          <option value="main">ООО Ромашка</option>
          <option value="demo">Демо-песочница</option>
        </select>
      </div>
      <nav className="space-y-5">
        {navSections.map((section) => (
          <div key={section.title}>
            <p className="mb-2 px-2 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">{section.title}</p>
            <div className="space-y-1">
              {section.items.filter((item) => navItemVisible(item, isPlatformAdmin)).map((item) => {
                const testId =
                  item.href === "/" ? "nav-dashboard" : `nav-${item.href.replace(/^\//, "").replace(/\//g, "-")}`;
                const active = navActive(location, item);
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    data-testid={testId}
                    onClick={onNavigate}
                    className={cn(
                      "flex items-center justify-between rounded-md px-3 py-2 text-sm",
                      active ? "bg-secondary font-medium text-secondary-foreground" : "hover:bg-muted",
                    )}
                  >
                    <span className="flex items-center gap-2">
                      <item.icon className="h-4 w-4" />
                      {item.label}
                    </span>
                    {item.badge ? <span className="rounded-full bg-warning/20 px-2 text-xs">{item.badge}</span> : null}
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </nav>
      <div className="mt-6 flex flex-wrap gap-x-3 gap-y-1 text-xs">
        <Link href="/help" className="text-primary hover:underline" data-testid="link-help" onClick={onNavigate}>
          Помощь
        </Link>
        <Link href="/api-docs" className="text-primary hover:underline" data-testid="link-api-docs" onClick={onNavigate}>
          Документация API
        </Link>
      </div>
      <div className="mt-8 border-t pt-4 text-xs text-muted-foreground" data-testid="sidebar-footer">
        <p>Мария Иванова</p>
        <p>integrator@company.ru</p>
        <p className="mt-1 text-[11px]">Интегратор данных</p>
        <button type="button" className="mt-2 rounded-md border px-2 py-1" onClick={onToggleTheme} data-testid="toggle-theme">
          Тема: {dark ? "Тёмная" : "Светлая"}
        </button>
        <div className="mt-3">
          <Link href="/login" className="text-primary hover:underline" data-testid="link-logout" onClick={onNavigate}>
            Выйти
          </Link>
        </div>
      </div>
    </>
  );
}
