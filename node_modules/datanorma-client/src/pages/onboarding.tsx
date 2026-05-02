import { useLocation } from "wouter";
import { Circle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { LinkAsButton } from "@/components/link-as-button";

const steps = [
  { id: 1, title: "Создайте первый источник", done: false, href: "/sources/new" },
  { id: 2, title: "Создайте приёмник", done: false, href: "/destinations/new" },
  { id: 3, title: "Выберите потоки данных", done: false, href: "/connections/new" },
  { id: 4, title: "Настройте маппинг", done: false, href: "/connections/conn-1/mapping" },
  { id: 5, title: "Включите нормализацию", done: false, href: "/normalization" },
  { id: 6, title: "Запустите синхронизацию", done: false, href: "/runs" },
  { id: 7, title: "Проверьте результат", done: false, href: "/issues" },
];

export function OnboardingPage() {
  const [, setLocation] = useLocation();

  return (
    <div className="min-h-screen bg-background px-4 py-10" data-testid="page-onboarding">
      <div className="mx-auto max-w-2xl">
        <h1 className="text-xl font-semibold">Добро пожаловать в DataNorma</h1>
        <p className="mt-1 text-sm text-muted-foreground">Пройдите чеклист, чтобы настроить первую интеграцию.</p>
        <div className="mt-6 space-y-3">
          {steps.map((s) => (
            <Card key={s.id} className="flex items-start gap-3 p-4" data-testid={`onboarding-step-${s.id}`}>
              <Circle className="mt-0.5 h-5 w-5 text-muted-foreground" />
              <div className="flex-1">
                <p className="font-medium">{s.title}</p>
                <LinkAsButton href={s.href} variant="outline" className="mt-2 px-2 py-1 text-xs" data-testid={`onboarding-cta-${s.id}`}>
                  Перейти
                </LinkAsButton>
              </div>
            </Card>
          ))}
        </div>
        <div className="mt-8 flex flex-wrap gap-2">
          <LinkAsButton href="/connections/new" data-testid="button-onboarding-create-connection">
            Создать подключение
          </LinkAsButton>
          <Button type="button" variant="outline" onClick={() => setLocation("/")} data-testid="button-onboarding-skip">
            Перейти в приложение
          </Button>
        </div>
      </div>
    </div>
  );
}
