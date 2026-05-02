import { Bell, Menu, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { LinkAsButton } from "@/components/link-as-button";

export function AppTopbar({
  onOpenMobileNav,
  onOpenCommandPalette,
}: {
  onOpenMobileNav: () => void;
  onOpenCommandPalette: () => void;
}) {
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
        <Button variant="ghost" className="hidden h-9 w-9 rounded-full border p-0 sm:inline-flex" data-testid="button-user-menu" aria-label="Меню пользователя">
          МИ
        </Button>
      </div>
    </header>
  );
}
