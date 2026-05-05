import { useMemo, useState } from "react";
import { normalizationRules } from "@/lib/mock-data";
import { NormalizationRuleCard } from "@/components/normalization-rule-card";
import { PageHeader } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { LinkAsButton } from "@/components/link-as-button";

const STRUCTURAL_BEFORE_AFTER: { rule: string; before: string; after: string }[] = [
  { rule: "Даты", before: "03.05.2026", after: "2026-05-03 (календарная дата, UTC/таймзона на этапе типизации)" },
  { rule: "Телефон", before: "8 (912) 555-77-88", after: "+79125557788" },
  { rule: "Email", before: "  User@MAIL.RU ", after: "user@mail.ru" },
  { rule: "ИНН", before: "7707083893 ", after: "7707083893 (10 зн., ЮЛ)" },
  { rule: "ИНН ИП", before: "502400211454", after: "502400211454 (12 зн.)" },
];

function defaultSampleForRule(ruleId: string): string {
  switch (ruleId) {
    case "rule-date":
      return "3.5.2026 14:30";
    case "rule-phone":
      return "8(912)555-77-88";
    case "rule-email":
      return "  User@MAIL.RU ";
    case "rule-inn":
      return "7707083893";
    case "rule-currency":
      return "12 800,50";
    default:
      return "";
  }
}

function structuralPreview(ruleId: string, raw: string): { ok: boolean; text: string } {
  const t = raw.trim();
  if (!t) return { ok: true, text: "—" };

  switch (ruleId) {
    case "rule-date": {
      const m = t.match(/^(\d{1,2})\.(\d{1,2})\.(\d{4})(?:\s+(\d{1,2}):(\d{2}))?$/);
      if (!m) return { ok: false, text: "не удалось разобрать как ДД.ММ.ГГГГ [ЧЧ:ММ]" };
      const d = m[1].padStart(2, "0");
      const mo = m[2].padStart(2, "0");
      const y = m[3];
      if (m[4] != null && m[5] != null) {
        const hh = m[4].padStart(2, "0");
        const mm = m[5];
        return { ok: true, text: `${y}-${mo}-${d}T${hh}:${mm}:00 (локально → далее UTC в pipeline)` };
      }
      return { ok: true, text: `${y}-${mo}-${d}` };
    }
    case "rule-phone": {
      const digits = t.replace(/\D/g, "");
      if (digits.length === 11 && digits.startsWith("8")) return { ok: true, text: `+7${digits.slice(1)}` };
      if (digits.length === 11 && digits.startsWith("7")) return { ok: true, text: `+${digits}` };
      if (digits.length === 10) return { ok: true, text: `+7${digits}` };
      return { ok: false, text: "ожидается 10–11 цифр (РФ) для однозначного E.164" };
    }
    case "rule-email": {
      const e = t.trim().toLowerCase();
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(e)) return { ok: false, text: "некорректный формат email" };
      return { ok: true, text: e };
    }
    case "rule-inn": {
      const digits = t.replace(/\D/g, "");
      if (digits.length === 10 || digits.length === 12) return { ok: true, text: digits };
      return { ok: false, text: "ИНН: 10 цифр (ЮЛ) или 12 (ИП)" };
    }
    case "rule-currency": {
      const normalized = t.replace(/\s/g, "").replace(",", ".");
      if (!/^\d+(\.\d{1,2})?$/.test(normalized)) return { ok: false, text: "ожидается десятичное число" };
      const [a, b = ""] = normalized.split(".");
      const frac = (b + "00").slice(0, 2);
      return { ok: true, text: `${a}.${frac}` };
    }
    default:
      return { ok: false, text: "неизвестное правило" };
  }
}

export function NormalizationPage() {
  const [sampleRuleId, setSampleRuleId] = useState("rule-phone");
  const [sampleInput, setSampleInput] = useState("8(912)555-77-88");
  const preview = useMemo(() => structuralPreview(sampleRuleId, sampleInput), [sampleRuleId, sampleInput]);

  return (
    <div className="p-4">
      <PageHeader
        title="Нормализация"
        description="Структурный слой: типизация и приведение форматов (даты, телефоны, email, ИНН и т.д.) в схеме normalized. Бизнес-семантика и витрины — в семантическом слое (dbt), не здесь."
        breadcrumbs="Данные / Нормализация"
        actions={
          <div className="flex flex-wrap gap-2">
            <LinkAsButton href="/semantic-layer" variant="outline" data-testid="link-semantic-layer">
              Семантический слой
            </LinkAsButton>
            <LinkAsButton href="/normalization/rules" variant="outline" data-testid="link-norm-rules">
              Правила
            </LinkAsButton>
            <LinkAsButton href="/normalization/dictionaries" variant="outline" data-testid="link-norm-dictionaries">
              Справочники
            </LinkAsButton>
          </div>
        }
      />

      <div className="mb-4 rounded-lg border bg-card p-4" data-testid="structural-before-after">
        <h2 className="mb-2 text-lg font-semibold">Структурные правила: до / после</h2>
        <p className="mb-3 text-sm text-muted-foreground">
          Ниже — иллюстрация того, что делает normalizer до появления бизнес-полей в dbt-моделях.
        </p>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[520px] text-left text-sm">
            <thead className="bg-muted">
              <tr>
                <th className="p-2">Группа</th>
                <th className="p-2">До</th>
                <th className="p-2">После (ориентир)</th>
              </tr>
            </thead>
            <tbody>
              {STRUCTURAL_BEFORE_AFTER.map((row) => (
                <tr key={row.rule} className="border-t">
                  <td className="p-2 font-medium">{row.rule}</td>
                  <td className="p-2 font-mono text-xs">{row.before}</td>
                  <td className="p-2 font-mono text-xs">{row.after}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="mb-4 flex flex-wrap gap-2 text-sm">
        <LinkAsButton href="/normalization/rules" data-testid="tab-norm-rules">
          Вкладка: правила
        </LinkAsButton>
        <LinkAsButton href="/normalization/dictionaries" variant="outline" data-testid="tab-norm-dicts">
          Вкладка: справочники
        </LinkAsButton>
      </div>

      <div className="grid gap-3 md:grid-cols-2" data-testid="grid-normalization-rules">
        {normalizationRules.map((rule) => (
          <NormalizationRuleCard key={rule.id} rule={rule} />
        ))}
      </div>

      <div className="mt-4 rounded-lg border bg-card p-4" data-testid="normalization-rule-test">
        <h2 className="mb-2 text-lg font-semibold">Проверка на примере (клиентский демо-превью)</h2>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
          <label className="flex min-w-[180px] flex-col gap-1 text-sm">
            Правило
            <select
              className="rounded-md border bg-background px-2 py-2 text-sm"
              value={sampleRuleId}
              onChange={(e) => {
                const id = e.target.value;
                setSampleRuleId(id);
                setSampleInput(defaultSampleForRule(id));
              }}
              data-testid="select-structural-rule"
            >
              {normalizationRules.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.title}
                </option>
              ))}
            </select>
          </label>
          <label className="flex flex-1 flex-col gap-1 text-sm">
            Значение
            <Input
              value={sampleInput}
              onChange={(e) => setSampleInput(e.target.value)}
              placeholder="Введите sample"
              data-testid="input-rule-sample"
            />
          </label>
          <Button
            type="button"
            variant="outline"
            data-testid="button-test-rule"
            onClick={() => setSampleInput(defaultSampleForRule(sampleRuleId))}
          >
            Пример
          </Button>
        </div>
        <p className="mt-2 text-xs text-muted-foreground">Превью пересчитывается при изменении поля «Значение».</p>
        <div
          className={`mt-3 rounded-md border p-3 text-sm ${preview.ok ? "border-muted bg-muted/30" : "border-destructive/50 bg-destructive/5"}`}
          data-testid="structural-preview-output"
        >
          <span className="text-muted-foreground">Результат: </span>
          <span className="font-mono">{preview.text}</span>
        </div>
      </div>

      <div className="mt-4 rounded-lg border bg-card p-4 text-sm text-muted-foreground" data-testid="normalization-history-stub">
        <strong className="text-foreground">История изменений</strong> — в MVP заглушка; события аудита см. раздел «Аудит».
      </div>
    </div>
  );
}
