import type { Status } from "@/lib/types";

/** Маппинг статуса sync_run → StatusBadge */
export function syncRunStatusToBadge(status: string): Status {
  switch (status) {
    case "success":
      return "success";
    case "failed":
      return "failed";
    case "running":
      return "running";
    case "queued":
      return "queued";
    case "cancelled":
      return "cancelled";
    default:
      return "draft";
  }
}

export function formatIso(dt: string | null | undefined, fallback = "—"): string {
  if (!dt) return fallback;
  try {
    return new Date(dt).toLocaleString("ru-RU", { dateStyle: "short", timeStyle: "short" });
  } catch {
    return fallback  }
}

export function formatDuration(started: string | null, finished: string | null): string {
  if (!started) return "—";
  try {
    const a = new Date(started).getTime();
    const b = finished ? new Date(finished).getTime() : Date.now();
    const sec = Math.max(0, Math.floor((b - a) / 1000));
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
  } catch {
    return "—";
  }
}
