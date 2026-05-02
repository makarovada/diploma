import { useState } from "react";
import { PageHeader } from "@/components/page-header";
import { PageFooter } from "@/components/page-footer";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { LinkAsButton } from "@/components/link-as-button";
import { cn } from "@/lib/utils";
import { useTheme } from "@/app/providers";

const tabs = [
  { id: "profile", label: "Профиль" },
  { id: "workspace", label: "Рабочее пространство" },
  { id: "security", label: "Безопасность" },
  { id: "notifications", label: "Уведомления" },
  { id: "api", label: "API" },
  { id: "theme", label: "Тема" },
  { id: "system", label: "Системные параметры" },
] as const;

export function SettingsPage() {
  const [tab, setTab] = useState<(typeof tabs)[number]["id"]>("profile");
  const { dark, toggle } = useTheme();

  return (
    <div className="p-4">
      <PageHeader title="Настройки" description="Профиль, API и системные параметры" breadcrumbs="Администрирование / Настройки" />
      <div className="mb-4 flex flex-wrap gap-1 border-b pb-2" data-testid="settings-tabs">
        {tabs.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setTab(t.id)}
            data-testid={`settings-tab-${t.id}`}
            className={cn(
              "rounded-md px-3 py-1.5 text-sm",
              tab === t.id ? "bg-secondary font-medium" : "text-muted-foreground hover:bg-muted",
            )}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === "profile" && (
        <div className="max-w-xl space-y-2 rounded-lg border bg-card p-4" data-testid="settings-panel-profile">
          <label className="text-sm">Имя</label>
          <Input defaultValue="Мария Иванова" data-testid="input-profile-name" />
          <label className="text-sm">Email</label>
          <Input defaultValue="integrator@company.ru" data-testid="input-profile-email" />
        </div>
      )}

      {tab === "api" && (
        <div className="max-w-2xl space-y-2 rounded-lg border bg-card p-4" data-testid="settings-form">
          <label className="text-sm">Base API URL</label>
          <Input className="mb-2 mt-1" defaultValue="https://api.datanorma.local/v1" data-testid="input-api-url" />
          <label className="text-sm">API токен</label>
          <Input className="mb-2 mt-1" defaultValue="dn_live_123456" data-testid="input-api-token" />
          <div className="flex flex-wrap gap-2">
            <Button type="button" data-testid="button-copy-endpoint">
              Скопировать endpoint
            </Button>
            <LinkAsButton href="/api-docs" variant="outline" data-testid="button-open-api-docs">
              Открыть API docs
            </LinkAsButton>
          </div>
        </div>
      )}

      {tab === "theme" && (
        <div className="max-w-xl rounded-lg border bg-card p-4" data-testid="settings-panel-theme">
          <p className="mb-2 text-sm text-muted-foreground">Тема интерфейса синхронизирована с переключателем в боковой панели.</p>
          <Button type="button" onClick={toggle} data-testid="button-settings-toggle-theme">
            Переключить тему (сейчас: {dark ? "тёмная" : "светлая"})
          </Button>
        </div>
      )}

      {tab !== "profile" && tab !== "api" && tab !== "theme" ? (
        <div className="rounded-lg border bg-card p-4 text-sm text-muted-foreground" data-testid={`settings-panel-${tab}`}>
          Раздел «{tabs.find((x) => x.id === tab)?.label}»: заглушка MVP (данные появятся позже).
        </div>
      ) : null}

      <PageFooter />
    </div>
  );
}
