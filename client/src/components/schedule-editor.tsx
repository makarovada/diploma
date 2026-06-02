import { useEffect, useMemo, useState } from "react";
import { Input } from "@/components/ui/input";
import {
  buildCronFromConfig,
  DEFAULT_SCHEDULE_CONFIG,
  describeSchedule,
  parseCronToConfig,
  SCHEDULE_MODE_OPTIONS,
  SCHEDULE_TIMEZONE_PRESETS,
  type ScheduleConfig,
  type ScheduleMode,
  type WeekdayCron,
  WEEKDAY_OPTIONS,
} from "@/lib/schedule-config";

export type ScheduleEditorProps = {
  cron: string;
  timezone: string;
  onCronChange: (cron: string) => void;
  onTimezoneChange: (timezone: string) => void;
  /** Префикс для data-testid (например wizard / settings). */
  testIdPrefix?: string;
};

function toggleWeekday(days: WeekdayCron[], day: WeekdayCron): WeekdayCron[] {
  return days.includes(day) ? days.filter((d) => d !== day) : [...days, day];
}

export function ScheduleEditor({
  cron,
  timezone,
  onCronChange,
  onTimezoneChange,
  testIdPrefix = "schedule",
}: ScheduleEditorProps) {
  const [config, setConfig] = useState<ScheduleConfig>(() => parseCronToConfig(cron));
  const [lastExternalCron, setLastExternalCron] = useState(cron);

  useEffect(() => {
    if (cron === lastExternalCron) return;
    setLastExternalCron(cron);
    setConfig(parseCronToConfig(cron));
  }, [cron, lastExternalCron]);

  const applyConfig = (next: ScheduleConfig) => {
    setConfig(next);
    const built = buildCronFromConfig(next);
    setLastExternalCron(built);
    onCronChange(built);
  };

  const patch = (partial: Partial<ScheduleConfig>) => {
    applyConfig({ ...config, ...partial });
  };

  const setMode = (mode: ScheduleMode) => {
    const base = { ...DEFAULT_SCHEDULE_CONFIG, ...config, mode };
    if (mode === "weekly" && base.weekdays.length === 0) {
      base.weekdays = [1, 2, 3, 4, 5];
    }
    applyConfig(base);
  };

  const previewCron = useMemo(() => buildCronFromConfig(config), [config]);
  const previewText = useMemo(() => describeSchedule(config, timezone), [config, timezone]);

  const tid = (suffix: string) => `${testIdPrefix}-${suffix}`;

  return (
    <div className="space-y-4" data-testid={`${testIdPrefix}-editor`}>
      <fieldset className="space-y-2">
        <legend className="text-sm font-medium">Режим</legend>
        <div className="grid gap-2 sm:grid-cols-2">
          {SCHEDULE_MODE_OPTIONS.map((opt) => (
            <label
              key={opt.mode}
              className={`flex cursor-pointer gap-2 rounded-md border p-3 text-sm transition-colors ${
                config.mode === opt.mode ? "border-primary bg-secondary/60" : "hover:bg-muted/50"
              }`}
              data-testid={tid(`mode-${opt.mode}`)}
            >
              <input
                type="radio"
                name={`${testIdPrefix}-mode`}
                className="mt-0.5"
                checked={config.mode === opt.mode}
                onChange={() => setMode(opt.mode)}
                data-testid={tid(`radio-${opt.mode}`)}
              />
              <span>
                <span className="font-medium">{opt.label}</span>
                <span className="mt-0.5 block text-xs text-muted-foreground">{opt.hint}</span>
              </span>
            </label>
          ))}
        </div>
      </fieldset>

      {config.mode === "interval_minutes" ? (
        <div className="rounded-md border bg-muted/30 p-3">
          <label className="text-sm font-medium" htmlFor={tid("interval-minutes")}>
            Интервал (минуты)
          </label>
          <Input
            id={tid("interval-minutes")}
            type="number"
            min={1}
            max={59}
            className="mt-1 max-w-[8rem]"
            value={config.intervalMinutes}
            onChange={(e) => patch({ intervalMinutes: Number(e.target.value) })}
            data-testid={tid("input-interval-minutes")}
          />
        </div>
      ) : null}

      {config.mode === "interval_hours" ? (
        <div className="rounded-md border bg-muted/30 p-3">
          <label className="text-sm font-medium" htmlFor={tid("interval-hours")}>
            Интервал (часы)
          </label>
          <Input
            id={tid("interval-hours")}
            type="number"
            min={1}
            max={23}
            className="mt-1 max-w-[8rem]"
            value={config.intervalHours}
            onChange={(e) => patch({ intervalHours: Number(e.target.value) })}
            data-testid={tid("input-interval-hours")}
          />
        </div>
      ) : null}

      {config.mode === "daily" || config.mode === "weekly" || config.mode === "monthly" ? (
        <div className="space-y-3 rounded-md border bg-muted/30 p-3">
          {config.mode === "weekly" ? (
            <div>
              <p className="text-sm font-medium">Дни недели</p>
              <div className="mt-2 flex flex-wrap gap-2">
                {WEEKDAY_OPTIONS.map((d) => {
                  const on = config.weekdays.includes(d.value);
                  return (
                    <button
                      key={d.value}
                      type="button"
                      className={`min-w-[2.5rem] rounded-md border px-2 py-1 text-sm font-medium ${
                        on ? "border-primary bg-primary text-primary-foreground" : "bg-background hover:bg-muted"
                      }`}
                      aria-pressed={on}
                      onClick={() => patch({ weekdays: toggleWeekday(config.weekdays, d.value) })}
                      data-testid={tid(`weekday-${d.value}`)}
                    >
                      {d.label}
                    </button>
                  );
                })}
              </div>
              {config.weekdays.length === 0 ? (
                <p className="mt-1 text-xs text-destructive">Выберите хотя бы один день</p>
              ) : null}
            </div>
          ) : null}

          {config.mode === "monthly" ? (
            <div>
              <label className="text-sm font-medium" htmlFor={tid("month-day")}>
                Число месяца
              </label>
              <Input
                id={tid("month-day")}
                type="number"
                min={1}
                max={28}
                className="mt-1 max-w-[8rem]"
                value={config.monthDay}
                onChange={(e) => patch({ monthDay: Number(e.target.value) })}
                data-testid={tid("input-month-day")}
              />
              <p className="mt-1 text-xs text-muted-foreground">1–28 — чтобы избежать пропусков в коротких месяцах</p>
            </div>
          ) : null}

          <div className="flex flex-wrap gap-4">
            <div>
              <label className="text-sm font-medium" htmlFor={tid("hour")}>
                Час
              </label>
              <Input
                id={tid("hour")}
                type="number"
                min={0}
                max={23}
                className="mt-1 max-w-[6rem]"
                value={config.hour}
                onChange={(e) => patch({ hour: Number(e.target.value) })}
                data-testid={tid("input-hour")}
              />
            </div>
            <div>
              <label className="text-sm font-medium" htmlFor={tid("minute")}>
                Минута
              </label>
              <Input
                id={tid("minute")}
                type="number"
                min={0}
                max={59}
                className="mt-1 max-w-[6rem]"
                value={config.minute}
                onChange={(e) => patch({ minute: Number(e.target.value) })}
                data-testid={tid("input-minute")}
              />
            </div>
          </div>
        </div>
      ) : null}

      {config.mode === "custom" ? (
        <div className="rounded-md border bg-muted/30 p-3">
          <label className="text-sm font-medium" htmlFor={tid("custom-cron")}>
            Выражение cron
          </label>
          <Input
            id={tid("custom-cron")}
            className="mt-1 font-mono text-sm"
            value={config.customCron}
            onChange={(e) => {
              const customCron = e.target.value;
              const next = { ...config, customCron };
              setConfig(next);
              setLastExternalCron(customCron);
              onCronChange(customCron);
            }}
            placeholder="0 3 * * *"
            data-testid={tid("input-custom-cron")}
          />
          <p className="mt-2 text-xs text-muted-foreground">
            Пять полей через пробел. Примеры: <code className="font-mono">*/5 * * * *</code> — каждые 5 мин.;{" "}
            <code className="font-mono">30 8 * * 1-5</code> — будни в 08:30.
          </p>
        </div>
      ) : null}

      <div>
        <label className="text-sm font-medium" htmlFor={tid("timezone")}>
          Часовой пояс
        </label>
        <select
          id={tid("timezone")}
          className="mt-1 flex h-10 w-full max-w-md rounded-md border border-input bg-background px-3 py-2 text-sm"
          value={timezone}
          onChange={(e) => onTimezoneChange(e.target.value)}
          data-testid={tid("select-timezone")}
        >
          {SCHEDULE_TIMEZONE_PRESETS.map((tz) => (
            <option key={tz} value={tz}>
              {tz}
            </option>
          ))}
        </select>
        <p className="mt-1 text-xs text-muted-foreground">Время запуска интерпретируется в этом поясе (Dagster sensor).</p>
      </div>

      <div
        className="rounded-md border border-dashed bg-muted/20 px-3 py-2 text-sm"
        data-testid={tid("preview")}
      >
        <p className="font-medium">{previewText}</p>
        {previewCron ? (
          <p className="mt-1 font-mono text-xs text-muted-foreground" data-testid={tid("preview-cron")}>
            {previewCron}
          </p>
        ) : (
          <p className="mt-1 text-xs text-muted-foreground">Cron не задан — автозапуск отключён</p>
        )}
      </div>
    </div>
  );
}
