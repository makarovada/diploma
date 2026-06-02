import { describe, expect, it } from "vitest";
import {
  buildCronFromConfig,
  DEFAULT_SCHEDULE_CONFIG,
  describeCronExpression,
  parseCronToConfig,
} from "@/lib/schedule-config";

describe("schedule-config", () => {
  it("manual mode yields empty cron", () => {
    expect(buildCronFromConfig({ ...DEFAULT_SCHEDULE_CONFIG, mode: "manual" })).toBe("");
    expect(parseCronToConfig("").mode).toBe("manual");
  });

  it("roundtrips interval minutes", () => {
    const expr = "*/15 * * * *";
    const cfg = parseCronToConfig(expr);
    expect(cfg.mode).toBe("interval_minutes");
    expect(cfg.intervalMinutes).toBe(15);
    expect(buildCronFromConfig(cfg)).toBe(expr);
  });

  it("roundtrips interval hours", () => {
    const expr = "0 */6 * * *";
    const cfg = parseCronToConfig(expr);
    expect(cfg.mode).toBe("interval_hours");
    expect(cfg.intervalHours).toBe(6);
    expect(buildCronFromConfig(cfg)).toBe(expr);
  });

  it("roundtrips daily", () => {
    const expr = "30 8 * * *";
    const cfg = parseCronToConfig(expr);
    expect(cfg.mode).toBe("daily");
    expect(cfg.hour).toBe(8);
    expect(cfg.minute).toBe(30);
    expect(buildCronFromConfig(cfg)).toBe(expr);
  });

  it("roundtrips weekly weekdays", () => {
    const expr = "0 9 * * 1,3,5";
    const cfg = parseCronToConfig(expr);
    expect(cfg.mode).toBe("weekly");
    expect(cfg.weekdays).toEqual([1, 3, 5]);
    expect(buildCronFromConfig(cfg)).toBe(expr);
  });

  it("parses weekday range into weekly days list", () => {
    const cfg = parseCronToConfig("0 9 * * 1-5");
    expect(cfg.mode).toBe("weekly");
    expect(cfg.weekdays).toEqual([1, 2, 3, 4, 5]);
    expect(buildCronFromConfig(cfg)).toBe("0 9 * * 1,2,3,4,5");
  });

  it("roundtrips monthly", () => {
    const expr = "0 3 15 * *";
    const cfg = parseCronToConfig(expr);
    expect(cfg.mode).toBe("monthly");
    expect(cfg.monthDay).toBe(15);
    expect(buildCronFromConfig(cfg)).toBe(expr);
  });

  it("unknown cron stays custom", () => {
    const expr = "0 0 1 1 *";
    expect(parseCronToConfig(expr).mode).toBe("custom");
  });

  it("describeCronExpression for weekly", () => {
    const text = describeCronExpression("0 9 * * 1,2,3,4,5", "Europe/Moscow");
    expect(text).toContain("Пн");
    expect(text).toContain("09:00");
    expect(text).toContain("Europe/Moscow");
  });
});
