import { Link, useLocation } from "wouter";
import { useAuth } from "@/app/auth-context";
import { cn } from "@/lib/utils";
import { navActive, navSections, type NavItem } from "@/lib/nav-config";
import { setStoredWorkspaceId } from "@/lib/api-client";
import { usePermission } from "@/hooks/use-permission";

function navItemVisible(item: NavItem, hasAudit: boolean, hasMembers: boolean): boolean {
  if (item.requiredPermission === "audit.read" && !hasAudit) {
    return false;
  }
  if (item.requiredPermission === "workspace.members.manage" && !hasMembers) {
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
  const { user, refreshMe } = useAuth();
  const hasAudit = usePermission("audit.read");
  const hasMembers = usePermission("workspace.members.manage");
  const workspaces = user?.workspaces ?? [];
  const activeId = user?.active_workspace_id ?? workspaces[0]?.id;

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
          value={activeId ?? ""}
          onChange={(e) => {
            const id = Number(e.target.value);
            if (Number.isFinite(id)) {
              setStoredWorkspaceId(id);
              void refreshMe();
            }
          }}
        >
          {workspaces.map((w) => (
            <option key={w.id} value={w.id}>
              {w.name}
            </option>
          ))}
        </select>
      </div>
      <nav className="space-y-5">
        {navSections.map((section) => {
          const visibleItems = section.items.filter((item) => navItemVisible(item, hasAudit, hasMembers));
          if (visibleItems.length === 0) return null;
          return (
            <div key={section.title}>
              <p className="mb-2 px-2 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">{section.title}</p>
              <div className="space-y-1">
                {visibleItems.map((item) => {
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
                        "flex items-center gap-2 rounded-md px-3 py-2 text-sm",
                        active ? "bg-secondary font-medium text-secondary-foreground" : "hover:bg-muted",
                      )}
                    >
                      <item.icon className="h-4 w-4" />
                      {item.label}
                    </Link>
                  );
                })}
              </div>
            </div>
          );
        })}
      </nav>
      <button
        type="button"
        className="mt-6 w-full rounded-md border px-3 py-2 text-sm hover:bg-muted"
        onClick={onToggleTheme}
      >
        {dark ? "Светлая тема" : "Тёмная тема"}
      </button>
    </>
  );
}
