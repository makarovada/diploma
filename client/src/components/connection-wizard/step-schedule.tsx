import { Input } from "@/components/ui/input";

type Props = {
  cron: string;
  timezone: string;
  onChange: (patch: { scheduleCron?: string; timezone?: string }) => void;
};

const tzPreset = ["UTC", "Europe/Moscow", "Asia/Yekaterinburg"];

export function StepSchedule({ cron, timezone, onChange }: Props) {
  return (
    <div className="rounded-lg border bg-card p-4" data-testid="wizard-step-schedule">
      <p className="mb-3 text-sm text-muted-foreground">
        Расписание в формате cron (опционально). Пустое значение — только ручной запуск.
      </p>
      <label className="text-sm font-medium" htmlFor="wizard-schedule-cron">
        Cron
      </label>
      <Input
        id="wizard-schedule-cron"
        className="mt-1 max-w-md font-mono text-sm"
        value={cron}
        onChange={(e) => onChange({ scheduleCron: e.target.value })}
        placeholder="0 */6 * * *"
        data-testid="input-schedule-cron"
      />
      <label className="mt-4 block text-sm font-medium" htmlFor="wizard-timezone">
        Часовой пояс
      </label>
      <select
        id="wizard-timezone"
        className="mt-1 flex h-10 max-w-md rounded-md border border-input bg-background px-3 py-2 text-sm"
        value={timezone}
        onChange={(e) => onChange({ timezone: e.target.value })}
        data-testid="select-schedule-timezone"
      >
        {tzPreset.map((tz) => (
          <option key={tz} value={tz}>
            {tz}
          </option>
        ))}
      </select>
    </div>
  );
}
