import { Activity, AlertTriangle, CheckCircle2, CirclePause, CircleX, Clock3, FileWarning, Loader2 } from "lucide-react";
import type { Status } from "@/lib/types";
import { cn } from "@/lib/utils";

const statusMeta: Record<Status, { label: string; className: string; Icon: typeof CheckCircle2 }> = {
  success: { label: "Успешно", className: "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300", Icon: CheckCircle2 },
  partial: { label: "Частично", className: "bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300", Icon: FileWarning },
  failed: { label: "Ошибка", className: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300", Icon: CircleX },
  running: { label: "Выполняется", className: "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300", Icon: Loader2 },
  queued: { label: "В очереди", className: "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-200", Icon: Clock3 },
  paused: { label: "Пауза", className: "bg-zinc-100 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-200", Icon: CirclePause },
  draft: { label: "Черновик", className: "bg-zinc-100 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-200", Icon: Activity },
  disabled: { label: "Отключено", className: "bg-zinc-100 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-200", Icon: AlertTriangle },
  ready: { label: "Готово", className: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300", Icon: CheckCircle2 },
};

export function StatusBadge({ status, testId }: { status: Status; testId?: string }) {
  const meta = statusMeta[status];
  return (
    <span data-testid={testId} className={cn("inline-flex items-center gap-1 rounded-full px-2 py-1 text-xs font-medium", meta.className)}>
      <meta.Icon className={cn("h-3 w-3", status === "running" && "animate-spin")} />
      {meta.label}
    </span>
  );
}
