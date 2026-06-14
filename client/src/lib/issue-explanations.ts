import type { Issue, Status } from "@/lib/types";

export type IssueExplanation = {
  title: string;
  description: string;
  recommendedAction: string;
};

export type StreamHealthStatus = "active" | "warning" | "error" | "disabled" | "running";

const ISSUE_EXPLANATIONS: Record<string, IssueExplanation> = {
  required_missing: {
    title: "Обязательное поле пустое",
    description: "В записи отсутствует значение для поля, помеченного как обязательное в правилах колонок.",
    recommendedAction:
      "Сделайте поле необязательным в правилах колонок или проверьте маппинг исходного поля на целевое.",
  },
  cast_error: {
    title: "Неверный формат значения",
    description: "Значение из источника не удалось привести к ожидаемому типу (дата, число, телефон и т.д.).",
    recommendedAction:
      "Настройте тип колонки (date, integer, phone…) или политику on_error в правилах потока.",
  },
  destination_write_failed: {
    title: "Не удалось записать в приёмник",
    description: "Данные прошли нормализацию, но запись в PostgreSQL или другой приёмник завершилась ошибкой.",
    recommendedAction: "Проверьте схему и таблицу приёмника, права доступа и совместимость типов колонок.",
  },
  elt_sync_failed: {
    title: "Ошибка синхронизации",
    description: "Синхронизация прервана до завершения обработки всех записей.",
    recommendedAction: "Откройте детали запуска, проверьте конфигурацию источника и приёмника, затем повторите синк.",
  },
};

const DEFAULT_ISSUE_EXPLANATION: IssueExplanation = {
  title: "Проблема при нормализации",
  description: "Запись не прошла проверку правил структурной нормализации.",
  recommendedAction: "Проверьте правила колонок для потока или исправьте данные в источнике.",
};

export function explainIssue(errorCode: string, fallbackMessage?: string): IssueExplanation {
  const key = errorCode.toLowerCase().trim();
  const base = ISSUE_EXPLANATIONS[key] ?? DEFAULT_ISSUE_EXPLANATION;
  if (key === "elt_sync_failed" && fallbackMessage?.trim()) {
    return { ...base, description: fallbackMessage.trim() };
  }
  return base;
}

export function explainSyncRunError(errorMessage: string | null | undefined): IssueExplanation {
  if (!errorMessage?.trim()) return ISSUE_EXPLANATIONS.elt_sync_failed;
  const msg = errorMessage.trim();
  if (msg.toLowerCase().includes("destination") || msg.toLowerCase().includes("приёмник")) {
    return { ...ISSUE_EXPLANATIONS.destination_write_failed, description: msg };
  }
  return { ...ISSUE_EXPLANATIONS.elt_sync_failed, description: msg };
}

export function explainIssuesBanner(count: number): string {
  if (count === 1) {
    return "Синхронизация завершилась, но 1 запись не прошла проверку качества данных.";
  }
  return `Синхронизация завершилась, но ${count} записей не прошли проверку качества данных.`;
}

export const STREAM_ISSUES_DISABLE_THRESHOLD = 8;

const STREAM_HEALTH_LABELS: Record<StreamHealthStatus, string> = {
  active: "Активен",
  warning: "Есть проблемы",
  error: "Ошибка синка",
  disabled: "Отключён",
  running: "Синхронизация…",
};

export function streamHealthLabel(status: StreamHealthStatus): string {
  return STREAM_HEALTH_LABELS[status];
}

export function streamHealthToBadgeStatus(status: StreamHealthStatus): Status {
  switch (status) {
    case "active":
      return "success";
    case "warning":
      return "partial";
    case "error":
      return "failed";
    case "disabled":
      return "disabled";
    case "running":
      return "running";
    default:
      return "ready";
  }
}

export type StreamHealthInput = {
  streamName: string;
  enabled: boolean;
  openIssueCount: number;
  isRunning: boolean;
  lastStreamFailed?: boolean;
};

export function computeStreamHealth(input: StreamHealthInput): StreamHealthStatus {
  if (!input.enabled) return "disabled";
  if (input.isRunning) return "running";
  if (input.lastStreamFailed) return "error";
  if (input.openIssueCount > 0) return "warning";
  return "active";
}

export function enrichIssue(issue: Issue, row?: { connection_id?: number | null; sync_run_id?: number | null; raw_value?: unknown }): Issue {
  const exp = explainIssue(issue.type, issue.original);
  let rawValue: string | undefined;
  if (row?.raw_value != null && String(row.raw_value).trim()) {
    rawValue = String(row.raw_value);
  }
  return {
    ...issue,
    title: exp.title,
    explanation: exp.description,
    recommendedAction: exp.recommendedAction,
    connectionId: row?.connection_id != null ? String(row.connection_id) : undefined,
    syncRunId: row?.sync_run_id != null ? String(row.sync_run_id) : undefined,
    rawValue,
  };
}

export const CANCEL_SYNC_HINT =
  "Отмена будет применена после завершения текущего потока. Следующие потоки в этом запуске не будут обработаны.";

export const DISABLE_STREAM_CONFIRM =
  "Поток будет исключён из следующих синхронизаций. Уже загруженные данные в приёмнике сохранятся. Включить поток можно в любой момент.";
