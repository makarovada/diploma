/** Конфигурация расписания → 5-полевой cron (мин час день месяц день_недели). */

export const SCHEDULE_TIMEZONE_PRESETS = ["UTC", "Europe/Moscow", "Asia/Yekaterinburg"] as const;

export type ScheduleMode =
  | "manual"
  | "interval_minutes"
  | "interval_hours"
  | "daily"
  | "weekly"
  | "monthly"
  | "custom";

/** Cron: 0 = воскресенье … 6 = суббота */
export type WeekdayCron = 0 | 1 | 2 | 3 | 4 | 5 | 6;

export type ScheduleConfig = {
  mode: ScheduleMode;
  intervalMinutes: number;
  intervalHours: number;
  hour: number;
  minute: number;
  weekdays: WeekdayCron[];
  monthDay: number;
  customCron: string;
};

export const WEEKDAY_OPTIONS: { value: WeekdayCron; label: string }[] = [
  { value: 1, label: "Пн" },
  { value: 2, label: "Вт" },
  { value: 3, label: "Ср" },
  { value: 4, label: "Чт" },
  { value: 5, label: "Пт" },
  { value: 6, label: "Сб" },
  { value: 0, label: "Вс" },
];

export const DEFAULT_SCHEDULE_CONFIG: ScheduleConfig = {
  mode: "manual",
  intervalMinutes: 15,
  intervalHours: 6,
  hour: 3,
  minute: 0,
  weekdays: [1, 2, 3, 4, 5],
  monthDay: 1,
  customCron: "",
};

const CRON_RE =
  /^(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)$/;

function clampInt(n: number, min: number, max: number): number {
  if (!Number.isFinite(n)) return min;
  return Math.min(max, Math.max(min, Math.round(n)));
}

function parsePositiveInt(s: string): number | null {
  const n = Number.parseInt(s, 10);
  if (!Number.isFinite(n) || n < 1) return null;
  return n;
}

function parseDowField(field: string): WeekdayCron[] | null {
  if (field === "*") return [0, 1, 2, 3, 4, 5, 6];
  const out = new Set<WeekdayCron>();
  for (const part of field.split(",")) {
    const p = part.trim();
    if (!p) continue;
    if (p.includes("-")) {
      const [a, b] = p.split("-", 2);
      const start = Number.parseInt(a ?? "", 10);
      const end = Number.parseInt(b ?? "", 10);
      if (!Number.isFinite(start) || !Number.isFinite(end)) return null;
      const lo = Math.min(start, end);
      const hi = Math.max(start, end);
      for (let d = lo; d <= hi; d++) {
        if (d < 0 || d > 6) return null;
        out.add(d as WeekdayCron);
      }
      continue;
    }
    const d = Number.parseInt(p, 10);
    if (!Number.isFinite(d) || d < 0 || d > 6) return null;
    out.add(d as WeekdayCron);
  }
  if (out.size === 0) return null;
  return [...out].sort((a, b) => a - b);
}

/** Разобрать сохранённый cron в конфиг редактора (неизвестные выражения → custom). */
export function parseCronToConfig(cron: string): ScheduleConfig {
  const expr = (cron ?? "").trim();
  if (!expr) {
    return { ...DEFAULT_SCHEDULE_CONFIG, mode: "manual", customCron: "" };
  }

  const m = expr.match(CRON_RE);
  if (!m) {
    return { ...DEFAULT_SCHEDULE_CONFIG, mode: "custom", customCron: expr };
  }

  const [, minF, hourF, domF, monF, dowF] = m;

  if (minF?.startsWith("*/") && hourF === "*" && domF === "*" && monF === "*" && dowF === "*") {
    const n = parsePositiveInt(minF.slice(2));
    if (n != null && n <= 59) {
      return { ...DEFAULT_SCHEDULE_CONFIG, mode: "interval_minutes", intervalMinutes: n, customCron: expr };
    }
  }

  if (minF === "0" && hourF?.startsWith("*/") && domF === "*" && monF === "*" && dowF === "*") {
    const n = parsePositiveInt(hourF.slice(2));
    if (n != null && n <= 23) {
      return { ...DEFAULT_SCHEDULE_CONFIG, mode: "interval_hours", intervalHours: n, customCron: expr };
    }
  }

  const minute = Number.parseInt(minF ?? "", 10);
  const hour = Number.parseInt(hourF ?? "", 10);
  if (
    Number.isFinite(minute) &&
    minute >= 0 &&
    minute <= 59 &&
    Number.isFinite(hour) &&
    hour >= 0 &&
    hour <= 23 &&
    domF === "*" &&
    monF === "*"
  ) {
    if (dowF === "*") {
      return {
        ...DEFAULT_SCHEDULE_CONFIG,
        mode: "daily",
        minute,
        hour,
        customCron: expr,
      };
    }
    const weekdays = parseDowField(dowF ?? "");
    if (weekdays && weekdays.length > 0 && weekdays.length < 7) {
      return {
        ...DEFAULT_SCHEDULE_CONFIG,
        mode: "weekly",
        minute,
        hour,
        weekdays,
        customCron: expr,
      };
    }
    if (weekdays && weekdays.length === 7) {
      return {
        ...DEFAULT_SCHEDULE_CONFIG,
        mode: "daily",
        minute,
        hour,
        customCron: expr,
      };
    }
  }

  if (
    Number.isFinite(minute) &&
    minute >= 0 &&
    minute <= 59 &&
    Number.isFinite(hour) &&
    hour >= 0 &&
    hour <= 23 &&
    monF === "*" &&
    dowF === "*"
  ) {
    const dom = Number.parseInt(domF ?? "", 10);
    if (Number.isFinite(dom) && dom >= 1 && dom <= 28) {
      return {
        ...DEFAULT_SCHEDULE_CONFIG,
        mode: "monthly",
        minute,
        hour,
        monthDay: dom,
        customCron: expr,
      };
    }
  }

  return { ...DEFAULT_SCHEDULE_CONFIG, mode: "custom", customCron: expr };
}

function formatWeekdays(days: WeekdayCron[]): string {
  const order = WEEKDAY_OPTIONS.map((o) => o.value);
  const sorted = [...new Set(days)].sort((a, b) => order.indexOf(a) - order.indexOf(b));
  return sorted.join(",");
}

/** Собрать cron из конфига редактора. */
export function buildCronFromConfig(config: ScheduleConfig): string {
  const c = { ...DEFAULT_SCHEDULE_CONFIG, ...config };
  switch (c.mode) {
    case "manual":
      return "";
    case "interval_minutes": {
      const n = clampInt(c.intervalMinutes, 1, 59);
      return `*/${n} * * * *`;
    }
    case "interval_hours": {
      const n = clampInt(c.intervalHours, 1, 23);
      return `0 */${n} * * *`;
    }
    case "daily": {
      const minute = clampInt(c.minute, 0, 59);
      const hour = clampInt(c.hour, 0, 23);
      return `${minute} ${hour} * * *`;
    }
    case "weekly": {
      const minute = clampInt(c.minute, 0, 59);
      const hour = clampInt(c.hour, 0, 23);
      const days = c.weekdays.length > 0 ? c.weekdays : ([1, 2, 3, 4, 5] as WeekdayCron[]);
      return `${minute} ${hour} * * ${formatWeekdays(days)}`;
    }
    case "monthly": {
      const minute = clampInt(c.minute, 0, 59);
      const hour = clampInt(c.hour, 0, 23);
      const dom = clampInt(c.monthDay, 1, 28);
      return `${minute} ${hour} ${dom} * *`;
    }
    case "custom":
      return (c.customCron ?? "").trim();
    default:
      return "";
  }
}

function pad2(n: number): string {
  return String(n).padStart(2, "0");
}

function weekdayLabels(days: WeekdayCron[]): string {
  const map = new Map(WEEKDAY_OPTIONS.map((o) => [o.value, o.label]));
  const order = WEEKDAY_OPTIONS.map((o) => o.value);
  return [...new Set(days)]
    .sort((a, b) => order.indexOf(a) - order.indexOf(b))
    .map((d) => map.get(d) ?? String(d))
    .join(", ");
}

/** Человекочитаемое описание расписания. */
export function describeSchedule(config: ScheduleConfig, timezone: string): string {
  const tz = (timezone || "UTC").trim() || "UTC";
  const c = { ...DEFAULT_SCHEDULE_CONFIG, ...config };
  switch (c.mode) {
    case "manual":
      return "Только ручной запуск";
    case "interval_minutes": {
      const n = clampInt(c.intervalMinutes, 1, 59);
      return `Каждые ${n} мин. (${tz})`;
    }
    case "interval_hours": {
      const n = clampInt(c.intervalHours, 1, 23);
      return `Каждые ${n} ч., в начале часа (${tz})`;
    }
    case "daily":
      return `Ежедневно в ${pad2(c.hour)}:${pad2(c.minute)} (${tz})`;
    case "weekly":
      return `По дням: ${weekdayLabels(c.weekdays)} в ${pad2(c.hour)}:${pad2(c.minute)} (${tz})`;
    case "monthly":
      return `${c.monthDay}-го числа каждого месяца в ${pad2(c.hour)}:${pad2(c.minute)} (${tz})`;
    case "custom": {
      const expr = (c.customCron ?? "").trim();
      return expr ? `Cron: ${expr} (${tz})` : `Только ручной запуск (${tz})`;
    }
    default:
      return "Только ручной запуск";
  }
}

export function describeCronExpression(cron: string, timezone: string): string {
  return describeSchedule(parseCronToConfig(cron), timezone);
}

export type ScheduleModeOption = { mode: ScheduleMode; label: string; hint: string };

export const SCHEDULE_MODE_OPTIONS: ScheduleModeOption[] = [
  { mode: "manual", label: "Без расписания", hint: "Синхронизация только по кнопке «Запустить»" },
  { mode: "interval_minutes", label: "Каждые N минут", hint: "Для частого обновления (1–59 мин.)" },
  { mode: "interval_hours", label: "Каждые N часов", hint: "В начале каждого N-го часа" },
  { mode: "daily", label: "Ежедневно", hint: "Один раз в сутки в заданное время" },
  { mode: "weekly", label: "По дням недели", hint: "Выбранные дни в заданное время" },
  { mode: "monthly", label: "Ежемесячно", hint: "Фиксированное число месяца (1–28)" },
  { mode: "custom", label: "Свой cron", hint: "5 полей: мин час день месяц день_недели" },
];
