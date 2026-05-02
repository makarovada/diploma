import { useState } from "react";
import { PageHeader } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { MappingTable } from "@/components/mapping-table";
import { mappingRows, normalizationRules } from "@/lib/mock-data";
import { NormalizationRuleCard } from "@/components/normalization-rule-card";

const steps = ["Название", "Источник", "Потоки", "Приемник", "Маппинг", "Нормализация", "Расписание", "Проверка"];

export function ConnectionWizardPage() {
  const [step, setStep] = useState(0);
  return (
    <div className="p-4">
      <PageHeader title="Мастер создания подключения" description="Пошаговая настройка интеграции" breadcrumbs="Интеграции / Подключения / Новый сценарий" />
      <div className="mb-4 grid gap-2 md:grid-cols-4" data-testid="wizard-stepper">
        {steps.map((s, i) => <button key={s} className={`rounded-md border px-3 py-2 text-left text-sm ${i === step ? "bg-secondary" : ""}`} onClick={() => setStep(i)} data-testid={`wizard-step-${i + 1}`}>{i + 1}. {s}</button>)}
      </div>
      {step === 0 && <div className="rounded-lg border bg-card p-4" data-testid="wizard-step-name"><Input placeholder="Название подключения" data-testid="input-connection-name" /><Input className="mt-2" placeholder="Описание" /></div>}
      {step === 1 && <div className="rounded-lg border bg-card p-4" data-testid="wizard-step-source"><Input placeholder="Выберите источник (например Ozon)" data-testid="select-source-connector" /><Button className="mt-3" data-testid="button-test-source-connection">Проверить подключение</Button></div>}
      {step === 4 && <MappingTable rows={mappingRows} />}
      {step === 5 && <div className="grid gap-3 md:grid-cols-2" data-testid="normalization-rule-cards">{normalizationRules.map((rule) => <NormalizationRuleCard key={rule.id} rule={rule} />)}</div>}
      {step === 7 && <div className="rounded-lg border bg-card p-4" data-testid="wizard-step-review"><p className="mb-2 text-sm">Все проверки пройдены. Можно сохранить и запустить.</p><Button data-testid="button-save-and-run">Сохранить и запустить</Button></div>}
      <div className="mt-4 flex justify-between">
        <Button variant="outline" onClick={() => setStep((x) => Math.max(0, x - 1))} data-testid="button-step-back">Назад</Button>
        <Button onClick={() => setStep((x) => Math.min(steps.length - 1, x + 1))} data-testid="button-step-next">Далее</Button>
      </div>
    </div>
  );
}
