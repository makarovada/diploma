import yaml from "js-yaml";

export type RestBuilderAuthType = "none" | "bearer" | "api_key_header";

export type RestBuilderStream = {
  name: string;
  path: string;
  method: "GET" | "POST";
  records_json_path: string;
  pagination_type: "none" | "offset";
  limit_param: string;
  offset_param: string;
  limit: number;
  max_pages: number;
  body_json: string;
};

export type RestBuilderConfig = {
  base_url: string;
  auth_type: RestBuilderAuthType;
  auth_token: string;
  auth_header_name: string;
  token_prefix: string;
  openapi_url: string;
  timeout_seconds: number;
  streams: RestBuilderStream[];
};

export type RestBuilderProbeResult = {
  ok: boolean;
  status_code: number | null;
  message: string;
  sample_records: Record<string, unknown>[];
  record_count: number;
  schema_hint?: Record<string, unknown>;
  stream?: string;
  url?: string;
};

export function emptyRestBuilderStream(): RestBuilderStream {
  return {
    name: "posts",
    path: "/posts",
    method: "GET",
    records_json_path: "",
    pagination_type: "none",
    limit_param: "limit",
    offset_param: "offset",
    limit: 50,
    max_pages: 20,
    body_json: "",
  };
}

export function emptyRestBuilderConfig(): RestBuilderConfig {
  return {
    base_url: "https://jsonplaceholder.typicode.com",
    auth_type: "none",
    auth_token: "",
    auth_header_name: "Authorization",
    token_prefix: "Bearer ",
    openapi_url: "",
    timeout_seconds: 60,
    streams: [emptyRestBuilderStream()],
  };
}

function normalizeBaseUrl(raw: string): string {
  return raw.trim().replace(/\/+$/, "");
}

function parseAuthType(raw: unknown): RestBuilderAuthType {
  const v = String(raw ?? "none").trim().toLowerCase();
  if (v === "bearer" || v === "api_key_header") return v;
  return "none";
}

function parseStreamFromDict(raw: Record<string, unknown>): RestBuilderStream {
  const pag = raw.pagination && typeof raw.pagination === "object" ? (raw.pagination as Record<string, unknown>) : {};
  const pagType = String(raw.pagination_type ?? pag.type ?? "none").toLowerCase();
  let bodyJson = "";
  if (raw.body && typeof raw.body === "object") {
    try {
      bodyJson = JSON.stringify(raw.body, null, 2);
    } catch {
      bodyJson = "";
    }
  }
  return {
    name: String(raw.name ?? "").trim(),
    path: String(raw.path ?? "").trim(),
    method: String(raw.method ?? "GET").toUpperCase() === "POST" ? "POST" : "GET",
    records_json_path: String(raw.records_json_path ?? ""),
    pagination_type: pagType === "offset" ? "offset" : "none",
    limit_param: String(raw.limit_param ?? pag.limit_param ?? "limit"),
    offset_param: String(raw.offset_param ?? pag.offset_param ?? "offset"),
    limit: Number(raw.limit ?? pag.limit ?? 50) || 50,
    max_pages: Number(raw.max_pages ?? pag.max_pages ?? 20) || 20,
    body_json: bodyJson,
  };
}

function parseStreamFromYaml(raw: Record<string, unknown>): RestBuilderStream {
  const pag = raw.pagination && typeof raw.pagination === "object" ? (raw.pagination as Record<string, unknown>) : {};
  let bodyJson = "";
  if (raw.body && typeof raw.body === "object") {
    try {
      bodyJson = JSON.stringify(raw.body, null, 2);
    } catch {
      bodyJson = "";
    }
  }
  const pagType = String(pag.type ?? "none").toLowerCase();
  return {
    name: String(raw.name ?? "").trim(),
    path: String(raw.path ?? "").trim(),
    method: String(raw.method ?? "GET").toUpperCase() === "POST" ? "POST" : "GET",
    records_json_path: String(raw.records_json_path ?? ""),
    pagination_type: pagType === "offset" ? "offset" : "none",
    limit_param: String(pag.limit_param ?? "limit"),
    offset_param: String(pag.offset_param ?? "offset"),
    limit: Number(pag.limit ?? 50) || 50,
    max_pages: Number(pag.max_pages ?? 20) || 20,
    body_json: bodyJson,
  };
}

export function parseRestBuilderYaml(text: string): RestBuilderConfig {
  const raw = yaml.load(text);
  if (!raw || typeof raw !== "object") {
    throw new Error("YAML: ожидается объект в корне");
  }
  const obj = raw as Record<string, unknown>;
  const auth = obj.auth && typeof obj.auth === "object" ? (obj.auth as Record<string, unknown>) : {};
  const streamsRaw = Array.isArray(obj.streams) ? obj.streams : [];
  const streams = streamsRaw
    .filter((s): s is Record<string, unknown> => Boolean(s && typeof s === "object"))
    .map(parseStreamFromYaml)
    .filter((s) => s.name && s.path);
  return {
    base_url: normalizeBaseUrl(String(obj.base_url ?? "")),
    auth_type: parseAuthType(auth.type),
    auth_token: String(auth.token ?? ""),
    auth_header_name: String(auth.header_name ?? "Authorization"),
    token_prefix: String(auth.token_prefix ?? "Bearer "),
    openapi_url: String(obj.openapi_url ?? ""),
    timeout_seconds: Number(obj.timeout_seconds ?? 60) || 60,
    streams: streams.length ? streams : [emptyRestBuilderStream()],
  };
}

export function parseRestBuilderConfig(raw: Record<string, unknown>): RestBuilderConfig {
  const yamlBody = raw.yaml_body ?? raw.connector_builder_yaml;
  const hasStructured = Boolean(String(raw.base_url ?? "").trim()) && Array.isArray(raw.streams) && raw.streams.length > 0;
  if (!hasStructured && yamlBody && String(yamlBody).trim()) {
    try {
      return parseRestBuilderYaml(String(yamlBody));
    } catch {
      return emptyRestBuilderConfig();
    }
  }

  const auth = raw.auth && typeof raw.auth === "object" ? (raw.auth as Record<string, unknown>) : {};
  const streamsRaw = Array.isArray(raw.streams) ? raw.streams : [];
  const streams = streamsRaw
    .filter((s): s is Record<string, unknown> => Boolean(s && typeof s === "object"))
    .map(parseStreamFromDict)
    .filter((s) => s.name && s.path);

  return {
    base_url: normalizeBaseUrl(String(raw.base_url ?? "")),
    auth_type: parseAuthType(raw.auth_type ?? auth.type),
    auth_token: String(raw.auth_token ?? auth.token ?? ""),
    auth_header_name: String(raw.auth_header_name ?? auth.header_name ?? "Authorization"),
    token_prefix: String(raw.token_prefix ?? auth.token_prefix ?? "Bearer "),
    openapi_url: String(raw.openapi_url ?? ""),
    timeout_seconds: Number(raw.timeout_seconds ?? 60) || 60,
    streams: streams.length ? streams : [emptyRestBuilderStream()],
  };
}

function streamToRecord(st: RestBuilderStream): Record<string, unknown> {
  let body: Record<string, unknown> | undefined;
  if (st.body_json.trim()) {
    try {
      const parsed = JSON.parse(st.body_json) as unknown;
      if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
        body = parsed as Record<string, unknown>;
      }
    } catch {
      /* ignore invalid body */
    }
  }
  const out: Record<string, unknown> = {
    name: st.name.trim(),
    path: st.path.trim(),
    method: st.method,
    records_json_path: st.records_json_path.trim(),
    pagination_type: st.pagination_type,
    limit_param: st.limit_param.trim() || "limit",
    offset_param: st.offset_param.trim() || "offset",
    limit: st.limit,
    max_pages: st.max_pages,
  };
  if (body) out.body = body;
  return out;
}

export function restBuilderConfigToYaml(cfg: RestBuilderConfig): string {
  const payload: Record<string, unknown> = {
    version: 1,
    base_url: normalizeBaseUrl(cfg.base_url),
    auth: {
      type: cfg.auth_type,
      header_name: cfg.auth_header_name.trim() || "Authorization",
      token_prefix: cfg.token_prefix || "Bearer ",
    },
    timeout_seconds: cfg.timeout_seconds,
    streams: cfg.streams.map((st) => {
      const streamPayload: Record<string, unknown> = {
        name: st.name.trim(),
        path: st.path.trim(),
        method: st.method,
        pagination: {
          type: st.pagination_type,
          limit_param: st.limit_param,
          offset_param: st.offset_param,
          limit: st.limit,
          max_pages: st.max_pages,
        },
      };
      if (st.records_json_path.trim()) {
        streamPayload.records_json_path = st.records_json_path.trim();
      }
      if (st.body_json.trim()) {
        try {
          streamPayload.body = JSON.parse(st.body_json);
        } catch {
          /* skip */
        }
      }
      return streamPayload;
    }),
  };
  const auth = payload.auth as Record<string, unknown>;
  if (cfg.auth_token.trim()) auth.token = cfg.auth_token.trim();
  if (cfg.openapi_url.trim()) payload.openapi_url = cfg.openapi_url.trim();
  return yaml.dump(payload, { lineWidth: 120, noRefs: true });
}

export function restBuilderConfigToRecord(cfg: RestBuilderConfig): Record<string, unknown> {
  const yamlBody = restBuilderConfigToYaml(cfg);
  return {
    base_url: normalizeBaseUrl(cfg.base_url),
    auth_type: cfg.auth_type,
    auth_token: cfg.auth_token.trim(),
    auth_header_name: cfg.auth_header_name.trim() || "Authorization",
    token_prefix: cfg.token_prefix || "Bearer ",
    openapi_url: cfg.openapi_url.trim(),
    timeout_seconds: cfg.timeout_seconds,
    streams: cfg.streams.map(streamToRecord),
    yaml_body: yamlBody,
  };
}

export function validateRestBuilderConfig(cfg: RestBuilderConfig): string | null {
  const base = normalizeBaseUrl(cfg.base_url);
  if (!base) return "Укажите Base URL REST API.";
  if (!/^https?:\/\//i.test(base)) return "Base URL должен начинаться с http:// или https://.";
  if (!cfg.streams.length) return "Добавьте хотя бы один endpoint.";
  const names = new Set<string>();
  for (const st of cfg.streams) {
    if (!st.name.trim()) return "У каждого endpoint должно быть имя потока.";
    if (!st.path.trim()) return `Endpoint «${st.name}»: укажите path.`;
    if (!st.path.startsWith("/")) return `Endpoint «${st.name}»: path должен начинаться с /.`;
    const key = st.name.trim().toLowerCase();
    if (names.has(key)) return `Дублируется имя потока «${st.name}».`;
    names.add(key);
    if (st.body_json.trim()) {
      try {
        JSON.parse(st.body_json);
      } catch {
        return `Endpoint «${st.name}»: некорректный JSON body.`;
      }
    }
  }
  if (cfg.auth_type !== "none" && !cfg.auth_token.trim()) {
    return "Укажите токен или API key для выбранного метода авторизации.";
  }
  return null;
}

export function normalizeRestBuilderConfig(cfg: RestBuilderConfig): RestBuilderConfig {
  const seen = new Set<string>();
  const streams = cfg.streams.map((st, idx) => {
    let name = st.name.trim() || `stream_${idx + 1}`;
    const base = name.toLowerCase();
    if (seen.has(base)) {
      let n = 2;
      while (seen.has(`${base}_${n}`)) n += 1;
      name = `${name}_${n}`;
    }
    seen.add(name.toLowerCase());
    return {
      ...st,
      name,
      path: st.path.trim(),
      limit_param: st.limit_param.trim() || "limit",
      offset_param: st.offset_param.trim() || "offset",
    };
  });
  return {
    ...cfg,
    base_url: normalizeBaseUrl(cfg.base_url),
    auth_header_name: cfg.auth_header_name.trim() || "Authorization",
    streams,
  };
}
