/** Конфигурация приёмников ELT (поля совпадают с datanorma/destinations/*.py). */

export const DESTINATION_CONNECTORS = [
  { value: "postgres", label: "PostgreSQL" },
  { value: "csv", label: "CSV (файл)" },
  { value: "xlsx", label: "Excel (.xlsx)" },
  { value: "clickhouse", label: "ClickHouse (HTTP)" },
] as const;

export type DestinationConnectorCode = (typeof DESTINATION_CONNECTORS)[number]["value"];

export type PostgresDestinationConfig = {
  url: string;
  schema: string;
  table: string;
  primary_key: string;
};

export type CsvDestinationConfig = {
  path: string;
  filename: string;
};

export type XlsxDestinationConfig = {
  path: string;
  sheet_name: string;
};

export type ClickHouseDestinationConfig = {
  host: string;
  port: string;
  database: string;
  table: string;
  user: string;
  password: string;
  secure: boolean;
};

export type DestinationConfigFormState =
  | { connector: "postgres"; config: PostgresDestinationConfig }
  | { connector: "csv"; config: CsvDestinationConfig }
  | { connector: "xlsx"; config: XlsxDestinationConfig }
  | { connector: "clickhouse"; config: ClickHouseDestinationConfig };

export const POSTGRES_DESTINATION_DEFAULTS: PostgresDestinationConfig = {
  url: "postgresql://test_user:test_pass@host.docker.internal:5544/test_sink",
  schema: "public",
  table: "elt_test_load",
  primary_key: "id",
};

export const CSV_DESTINATION_DEFAULTS: CsvDestinationConfig = {
  path: "/data/exports",
  filename: "",
};

export const XLSX_DESTINATION_DEFAULTS: XlsxDestinationConfig = {
  path: "/data/export.xlsx",
  sheet_name: "",
};

export const CLICKHOUSE_DESTINATION_DEFAULTS: ClickHouseDestinationConfig = {
  host: "localhost",
  port: "8123",
  database: "default",
  table: "elt_load",
  user: "default",
  password: "",
  secure: false,
};

export function isDestinationConnectorCode(code: string): code is DestinationConnectorCode {
  return DESTINATION_CONNECTORS.some((c) => c.value === code);
}

export function defaultDestinationConfig(connector: DestinationConnectorCode): DestinationConfigFormState {
  switch (connector) {
    case "postgres":
      return { connector, config: { ...POSTGRES_DESTINATION_DEFAULTS } };
    case "csv":
      return { connector, config: { ...CSV_DESTINATION_DEFAULTS } };
    case "xlsx":
      return { connector, config: { ...XLSX_DESTINATION_DEFAULTS } };
    case "clickhouse":
      return { connector, config: { ...CLICKHOUSE_DESTINATION_DEFAULTS } };
  }
}

export function parseDestinationConfig(
  connector: string,
  raw: Record<string, unknown>,
): DestinationConfigFormState {
  const code = isDestinationConnectorCode(connector) ? connector : "postgres";
  switch (code) {
    case "postgres": {
      const pk = raw.primary_key;
      let primary_key = "id";
      if (typeof pk === "string") primary_key = pk;
      else if (Array.isArray(pk)) primary_key = pk.map(String).join(", ");
      return {
        connector: code,
        config: {
          url: String(raw.url ?? ""),
          schema: String(raw.schema ?? "public"),
          table: String(raw.table ?? raw.table_name ?? "elt_stream_load"),
          primary_key,
        },
      };
    }
    case "csv":
      return {
        connector: code,
        config: {
          path: String(raw.path ?? raw.directory ?? ""),
          filename: String(raw.filename ?? ""),
        },
      };
    case "xlsx":
      return {
        connector: code,
        config: {
          path: String(raw.path ?? ""),
          sheet_name: String(raw.sheet_name ?? ""),
        },
      };
    case "clickhouse":
      return {
        connector: code,
        config: {
          host: String(raw.host ?? "localhost"),
          port: String(raw.port ?? "8123"),
          database: String(raw.database ?? "default"),
          table: String(raw.table ?? "elt_load"),
          user: String(raw.user ?? "default"),
          password: String(raw.password ?? ""),
          secure: Boolean(raw.secure),
        },
      };
  }
}

export function destinationConfigToRecord(state: DestinationConfigFormState): Record<string, unknown> {
  switch (state.connector) {
    case "postgres": {
      const c = state.config;
      const out: Record<string, unknown> = {
        schema: c.schema.trim() || "public",
        table: c.table.trim() || "elt_stream_load",
      };
      if (c.url.trim()) out.url = c.url.trim();
      const pk = c.primary_key.trim();
      if (pk) {
        out.primary_key = pk.includes(",") ? pk.split(",").map((s) => s.trim()).filter(Boolean) : pk;
      }
      return out;
    }
    case "csv": {
      const c = state.config;
      const out: Record<string, unknown> = { path: c.path.trim() };
      if (c.filename.trim()) out.filename = c.filename.trim();
      return out;
    }
    case "xlsx": {
      const c = state.config;
      const out: Record<string, unknown> = { path: c.path.trim() };
      if (c.sheet_name.trim()) out.sheet_name = c.sheet_name.trim();
      return out;
    }
    case "clickhouse": {
      const c = state.config;
      const out: Record<string, unknown> = {
        host: c.host.trim() || "localhost",
        port: Number(c.port) || 8123,
        database: c.database.trim() || "default",
        table: c.table.trim() || "elt_load",
        user: c.user.trim() || "default",
      };
      if (c.password) out.password = c.password;
      if (c.secure) out.secure = true;
      return out;
    }
  }
}

export function validateDestinationConfig(state: DestinationConfigFormState): string | null {
  switch (state.connector) {
    case "postgres":
      if (!state.config.table.trim()) return "Укажите имя таблицы PostgreSQL.";
      return null;
    case "csv":
      if (!state.config.path.trim()) return "Укажите путь к файлу или каталогу CSV.";
      return null;
    case "xlsx":
      if (!state.config.path.trim()) return "Укажите путь к файлу .xlsx.";
      if (!state.config.path.trim().toLowerCase().endsWith(".xlsx")) {
        return "Путь должен указывать на файл с расширением .xlsx.";
      }
      return null;
    case "clickhouse":
      if (!state.config.host.trim()) return "Укажите host ClickHouse.";
      if (!state.config.table.trim()) return "Укажите имя таблицы ClickHouse.";
      return null;
  }
}

export function describeDestinationConfig(state: DestinationConfigFormState): string[] {
  switch (state.connector) {
    case "postgres": {
      const c = state.config;
      const lines = [
        `Схема: ${c.schema || "public"}`,
        `Таблица: ${c.table || "—"}`,
        c.url.trim() ? `URL: ${c.url.trim()}` : "URL: (по умолчанию из настроек сервера)",
      ];
      if (c.primary_key.trim()) lines.push(`Первичный ключ: ${c.primary_key.trim()}`);
      return lines;
    }
    case "csv": {
      const c = state.config;
      return [
        `Путь: ${c.path || "—"}`,
        c.filename.trim() ? `Имя файла (для каталога): ${c.filename}` : "Имя файла: по имени потока",
      ];
    }
    case "xlsx": {
      const c = state.config;
      return [
        `Файл: ${c.path || "—"}`,
        c.sheet_name.trim() ? `Лист: ${c.sheet_name}` : "Лист: по имени потока",
      ];
    }
    case "clickhouse": {
      const c = state.config;
      return [
        `Хост: ${c.host}:${c.port}`,
        `База / таблица: ${c.database}.${c.table}`,
        `Пользователь: ${c.user}`,
        c.secure ? "TLS: да" : "TLS: нет",
      ];
    }
  }
}
