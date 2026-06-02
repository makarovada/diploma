import { Activity, AlertTriangle, CheckCircle2, CirclePause, CircleX, Clock3, FileWarning, Loader2 } from "lucide-react";
import type { Status } from "@/lib/types";
import { cn } from "@/lib/utils";

/** Фон + рамка + иконка: статус различим при дальтонизме, не только по цвету. */
const statusMeta: Record<Status, { label: string; className: string; Icon: typeof CheckCircle2 }> = {
  success: {
    label: "Успешно",
    className: "border border-success/50 bg-success/12 text-success",
    Icon: CheckCircle2,
  },
  partial: {
    label: "Частично",
    className: "border border-warning/50 bg-warning/12 text-warning",
    Icon: FileWarning,
  },
  failed: {
    label: "Ошибка",
    className: "border border-destructive/50 bg-destructive/12 text-destructive",
    Icon: CircleX,
  },
  running: {
    label: "Выполняется",
    className: "border border-info/50 bg-info/12 text-info",
    Icon: Loader2,
  },
  queued: {
    label: "В очереди",
    className: "border border-border bg-muted text-muted-foreground",
    Icon: Clock3,
  },
  cancelled: {
    label: "Отменён",
    className: "border border-border bg-muted text-muted-foreground",
    Icon: CirclePause,
  },
  paused: {
    label: "Пауза",
    className: "border border-border bg-muted text-muted-foreground",
    Icon: CirclePause,
  },
  draft: {
    label: "Черновик",
    className: "border border-dashed border-border bg-muted/60 text-muted-foreground",
    Icon: Activity,
  },
  disabled: {
    label: "Отключено",
    className: "border border-border bg-muted text-muted-foreground",
    Icon: AlertTriangle,
  },
  ready: {
    label: "Готово",
    className: "border border-success/40 bg-success/10 text-success",
    Icon: CheckCircle2,
  },
};

export function StatusBadge({ status, testId }: { status: Status; testId?: string }) {
  const meta = statusMeta[status];
  return (
    <span
      data-testid={testId}
      className={cn("inline-flex items-center gap-1 rounded-full px-2 py-1 text-xs font-medium", meta.className)}
    >
      <meta.Icon className={cn("h-3 w-3 shrink-0", status === "running" && "animate-spin")} aria-hidden />
      {meta.label}
    </span>
  );
}
