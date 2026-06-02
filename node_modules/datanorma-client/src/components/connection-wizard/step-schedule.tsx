import { ScheduleEditor } from "@/components/schedule-editor";

type Props = {
  cron: string;
  timezone: string;
  onChange: (patch: { scheduleCron?: string; timezone?: string }) => void;
};

export function StepSchedule({ cron, timezone, onChange }: Props) {
  return (
    <div className="rounded-lg border bg-card p-4" data-testid="wizard-step-schedule">
      <p className="mb-4 text-sm text-muted-foreground">
        Настройте автоматическую синхронизацию или оставьте только ручной запуск. Расписание можно изменить позже в
        настройках подключения.
      </p>
      <ScheduleEditor
        cron={cron}
        timezone={timezone}
        testIdPrefix="wizard-schedule"
        onCronChange={(scheduleCron) => onChange({ scheduleCron })}
        onTimezoneChange={(tz) => onChange({ timezone: tz })}
      />
    </div>
  );
}
