import { Link, useLocation } from "wouter";
import { cn } from "@/lib/utils";

const tabs: { suffix: string; label: string; testId: string }[] = [
  { suffix: "", label: "Обзор", testId: "tab-connection-overview" },
  { suffix: "/edit", label: "Редактирование", testId: "tab-connection-edit" },
  { suffix: "/streams", label: "Потоки", testId: "tab-connection-streams" },
  { suffix: "/mapping", label: "Маппинг", testId: "tab-connection-mapping" },
  { suffix: "/normalization", label: "Нормализация", testId: "tab-connection-normalization" },
  { suffix: "/runs", label: "Запуски", testId: "tab-connection-runs" },
  { suffix: "/logs", label: "Логи", testId: "tab-connection-logs" },
  { suffix: "/issues", label: "Проблемы", testId: "tab-connection-issues" },
  { suffix: "/settings", label: "Настройки", testId: "tab-connection-settings" },
];

export function ConnectionSubNav({ connectionId }: { connectionId: string }) {
  const [location] = useLocation();
  const base = `/connections/${connectionId}`;

  return (
    <nav className="mb-4 flex flex-wrap gap-1 border-b pb-2" aria-label="Разделы подключения" data-testid="connection-sub-nav">
      {tabs.map((t) => {
        const href = `${base}${t.suffix}`;
        const active =
          t.suffix === ""
            ? location === base || location === `${base}/`
            : location === href || location.startsWith(`${href}/`);
        return (
          <Link
            key={t.suffix || "overview"}
            href={href}
            data-testid={t.testId}
            className={cn(
              "rounded-md px-3 py-1.5 text-sm",
              active ? "bg-secondary font-medium text-secondary-foreground" : "text-muted-foreground hover:bg-muted hover:text-foreground",
            )}
          >
            {t.label}
          </Link>
        );
      })}
    </nav>
  );
}
