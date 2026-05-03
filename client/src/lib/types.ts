export type Status =
  | "draft"
  | "ready"
  | "running"
  | "success"
  | "partial"
  | "failed"
  | "paused"
  | "disabled"
  | "queued"
  | "cancelled";

export type Connection = {
  id: string;
  name: string;
  source: string;
  destination: string;
  status: Status;
  syncMode: "full_refresh" | "incremental" | "append" | "upsert";
  schedule: string;
  lastRunAt: string;
  records: number;
  issues: number;
  mappingCoverage: number;
  normalizationEnabled: boolean;
};

export type Run = {
  id: string;
  connectionId: string;
  connectionName: string;
  status: Status;
  stage: "extract" | "staging" | "normalize" | "validate" | "load" | "complete";
  startedAt: string;
  duration: string;
  records: number;
  issues: number;
  triggeredBy: string;
};

export type Issue = {
  id: string;
  severity: "low" | "medium" | "high";
  type: string;
  connection: string;
  stream: string;
  field: string;
  original: string;
  suggested: string;
  status: "open" | "resolved";
};

export type MappingRow = {
  sourceField: string;
  type: string;
  targetField: string;
  transformation: string;
  required: boolean;
  sample: string;
  preview: string;
  state: "mapped" | "unmapped" | "required_missing" | "type_mismatch";
};

export type NormalizationRule = {
  id: string;
  title: string;
  enabled: boolean;
  fixedCount: number;
  issuesCount: number;
  description: string;
};

export type Source = {
  id: string;
  name: string;
  connector: string;
  category: string;
  checkStatus: "ok" | "warning" | "error" | "never";
  streamCount: number;
  lastUsed: string;
  owner: string;
};

export type Destination = {
  id: string;
  name: string;
  type: string;
  status: "ok" | "warning" | "error";
  schemaOrDb: string;
  lastUsed: string;
  connectionCount: number;
};

export type ConnectorCatalogItem = {
  id: string;
  name: string;
  category: string;
  region: "ru" | "intl";
  role: "source" | "destination" | "both";
  preview: boolean;
  description: string;
  streams: string[];
  auth: string;
};

export type ActivityEvent = {
  id: string;
  at: string;
  type: "run" | "issue" | "config" | "user";
  title: string;
  detail: string;
};

export type CanonicalField = {
  name: string;
  type: string;
  required: boolean;
  description: string;
  aliases: string;
  rule: string;
  example: string;
};

export type CanonicalEntity = {
  id: string;
  nameRu: string;
  fields: CanonicalField[];
};

export type AppUser = {
  id: string;
  name: string;
  email: string;
  role: "platform_admin" | "data_integrator" | "analyst" | "viewer";
  workspace: string;
  status: "active" | "invited" | "disabled";
  lastActive: string;
};

export type AuditEntry = {
  id: string;
  at: string;
  actor: string;
  action: string;
  entityType: string;
  entityName: string;
  result: "success" | "failure";
  details: string;
};

export type ScheduleRow = {
  id: string;
  connectionName: string;
  schedule: string;
  timezone: string;
  nextRun: string;
  lastRun: string;
  status: Status;
  owner: string;
};

export type QueueJob = {
  id: string;
  connectionName: string;
  stage: string;
  priority: number;
  queuedAt: string;
  startedAt: string;
  worker: string;
  status: Status;
};
