import { Bell, LogOut, Menu, Search } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/app/auth-context";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { LinkAsButton } from "@/components/link-as-button";
import { getStoredWorkspaceId, setStoredWorkspaceId } from "@/lib/api-client";

export function AppTopbar({
  onOpenMobileNav,
  onOpenCommandPalette,
}: {
  onOpenMobileNav: () => void;
  onOpenCommandPalette: () => void;
}) {
  const queryClient = useQueryClient();
  const { user, logout, refreshMe } = useAuth();
  const initials =
    user?.username
      .split(/[^a-zA-Zа-яА-ЯёЁ0-9]+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((s) => s[0]?.toUpperCase() ?? "")
      .join("") || user?.username.slice(0, 2).toUpperCase() || "—";

  const workspaces = user?.workspaces ?? [];
  const storedWid = getStoredWorkspaceId();
  const rawWorkspaceId =
    storedWid !== null && workspaces.some((w) => w.id === storedWid)
      ? storedWid
      : (user?.active_workspace_id ?? workspaces[0]?.id);
  const selectValue = rawWorkspaceId !== undefined && rawWorkspaceId !== null ? String(rawWorkspaceId) : "";

  return (
    <header className="border-b bg-background px-4 py-3" data-testid="topbar-main">
      <div className="flex flex-wrap items-center gap-2">
        <Button
          type="button"
          variant="outline"
          className="shrink-0 lg:hidden"
          onClick={onOpenMobileNav}
          data-testid="button-mobile-menu"
          aria-label="Открыть меню"
        >
          <Menu className="h-4 w-4" />
        </Button>
        <div className="relative hidden min-w-0 max-w-md flex-1 md:block">
          <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            className="cursor-pointer pl-8"
            placeholder="Поиск… (Ctrl+K)"
            readOnly
            onFocus={onOpenCommandPalette}
            onClick={onOpenCommandPalette}
            data-testid="input-global-search"
          />
        </div>
        <Button
          type="button"
          variant="outline"
          className="md:hidden"
          onClick={onOpenCommandPalette}
          data-testid="button-search-mobile"
          aria-label="Поиск"
        >
          <Search className="h-4 w-4" />
        </Button>
        <Button type="button" variant="outline" onClick={onOpenCommandPalette} className="hidden sm:inline-flex" data-testid="button-open-command-palette">
          Ctrl+K
        </Button>
        <LinkAsButton href="/connections/new" data-testid="button-quick-action">
          Создать подключение
        </LinkAsButton>
        {workspaces.length > 0 ? (
          <label className="flex items-center gap-1 text-xs text-muted-foreground">
            <span className="hidden sm:inline">Workspace</span>
            <select
              className="h-9 max-w-[11rem] truncate rounded-md border border-input bg-background px-2 text-sm text-foreground"
              data-testid="select-workspace"
              aria-label="Текущий workspace"
              value={selectValue}
              onChange={async (e) => {
                const v = Number(e.target.value);
                if (!Number.isFinite(v)) return;
                setStoredWorkspaceId(v);
                await refreshMe();
                void queryClient.invalidateQueries();
              }}
            >
              {workspaces.map((w) => (
                <option key={w.id} value={w.id}>
                  {w.code} — {w.name}
                </option>
              ))}
            </select>
          </label>
        ) : null}
        <span
          className="hidden items-center gap-1.5 rounded-full border bg-card px-2 py-1 text-xs text-muted-foreground xl:inline-flex"
          data-testid="indicator-system-status"
        >
          <span className="h-2 w-2 rounded-full bg-success" />
          Система в норме
        </span>
        <Button variant="outline" data-testid="button-notifications" aria-label="Уведомления">
          <Bell className="h-4 w-4" />
        </Button>
        <span className="hidden max-w-[10rem] truncate text-xs text-muted-foreground sm:inline" title={user?.username}>
          {user?.username}
        </span>
        <Button
          type="button"
          variant="outline"
          className="hidden h-9 min-w-9 rounded-full border px-2 sm:inline-flex"
          data-testid="button-user-menu"
          aria-label="Текущий пользователь"
          title={user?.username}
        >
          {initials}
        </Button>
        <Button type="button" variant="outline" onClick={() => logout()} data-testid="button-logout" aria-label="Выйти">
          <LogOut className="h-4 w-4" />
        </Button>
      </div>
    </header>
  );
}
