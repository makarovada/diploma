import type { ReactNode } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  CLICKHOUSE_DESTINATION_DEFAULTS,
  CSV_DESTINATION_DEFAULTS,
  DESTINATION_CONNECTORS,
  POSTGRES_DESTINATION_DEFAULTS,
  XLSX_DESTINATION_DEFAULTS,
  type DestinationConfigFormState,
  type DestinationConnectorCode,
  validateDestinationConfig,
} from "@/lib/destination-config";

type Props = {
  connector: DestinationConnectorCode;
  value: DestinationConfigFormState;
  onChange: (value: DestinationConfigFormState) => void;
  onConnectorChange?: (connector: DestinationConnectorCode) => void;
  idPrefix?: string;
  showConnectorSelect?: boolean;
  connectorReadOnly?: boolean;
};

function Field({
  id,
  label,
  hint,
  children,
}: {
  id: string;
  label: string;
  hint?: string;
  children: ReactNode;
}) {
  return (
    <div className="space-y-1">
      <label className="text-sm font-medium" htmlFor={id}>
        {label}
      </label>
      {children}
      {hint ? <p className="text-xs text-muted-foreground">{hint}</p> : null}
    </div>
  );
}

export function DestinationConfigForm({
  connector,
  value,
  onChange,
  onConnectorChange,
  idPrefix = "dest",
  showConnectorSelect = false,
  connectorReadOnly = false,
}: Props) {
  const validationError = validateDestinationConfig(value);

  const patchPostgres = (partial: Partial<typeof POSTGRES_DESTINATION_DEFAULTS>) => {
    if (value.connector !== "postgres") return;
    onChange({ connector: "postgres", config: { ...value.config, ...partial } });
  };

  const patchCsv = (partial: Partial<typeof CSV_DESTINATION_DEFAULTS>) => {
    if (value.connector !== "csv") return;
    onChange({ connector: "csv", config: { ...value.config, ...partial } });
  };

  const patchXlsx = (partial: Partial<typeof XLSX_DESTINATION_DEFAULTS>) => {
    if (value.connector !== "xlsx") return;
    onChange({ connector: "xlsx", config: { ...value.config, ...partial } });
  };

  const patchClickhouse = (partial: Partial<typeof CLICKHOUSE_DESTINATION_DEFAULTS>) => {
    if (value.connector !== "clickhouse") return;
    onChange({ connector: "clickhouse", config: { ...value.config, ...partial } });
  };

  return (
    <div className="space-y-4" data-testid={`${idPrefix}-config-form`}>
      {showConnectorSelect ? (
        <Field id={`${idPrefix}-connector`} label="Тип приёмника">
          <select
            id={`${idPrefix}-connector`}
            className="h-9 w-full rounded-md border bg-background px-2 text-sm"
            value={connector}
            disabled={connectorReadOnly}
            onChange={(e) => onConnectorChange?.(e.target.value as DestinationConnectorCode)}
            data-testid={`${idPrefix}-select-connector`}
          >
            {DESTINATION_CONNECTORS.map((c) => (
              <option key={c.value} value={c.value}>
                {c.label}
              </option>
            ))}
          </select>
        </Field>
      ) : connectorReadOnly ? (
        <p className="text-sm text-muted-foreground" data-testid={`${idPrefix}-connector-readonly`}>
          Тип: {DESTINATION_CONNECTORS.find((c) => c.value === connector)?.label ?? connector}
        </p>
      ) : null}

      {value.connector === "postgres" ? (
        <div className="space-y-3 rounded-md border border-dashed p-3" data-testid={`${idPrefix}-fields-postgres`}>
          <p className="text-sm font-medium">PostgreSQL</p>
          <Field
            id={`${idPrefix}-pg-url`}
            label="URL подключения"
            hint="Оставьте пустым, чтобы использовать DATABASE_URL сервера. Пример: postgresql://user:pass@host:5432/db"
          >
            <Input
              id={`${idPrefix}-pg-url`}
              value={value.config.url}
              onChange={(e) => patchPostgres({ url: e.target.value })}
              placeholder="postgresql://user:pass@host:5432/database"
              data-testid={`${idPrefix}-input-pg-url`}
            />
          </Field>
          <div className="grid gap-3 sm:grid-cols-2">
            <Field id={`${idPrefix}-pg-schema`} label="Схема">
              <Input
                id={`${idPrefix}-pg-schema`}
                value={value.config.schema}
                onChange={(e) => patchPostgres({ schema: e.target.value })}
                placeholder="public"
                data-testid={`${idPrefix}-input-pg-schema`}
              />
            </Field>
            <Field id={`${idPrefix}-pg-table`} label="Таблица">
              <Input
                id={`${idPrefix}-pg-table`}
                value={value.config.table}
                onChange={(e) => patchPostgres({ table: e.target.value })}
                placeholder="elt_test_load"
                data-testid={`${idPrefix}-input-pg-table`}
              />
            </Field>
          </div>
          <Field
            id={`${idPrefix}-pg-pk`}
            label="Первичный ключ (для upsert)"
            hint="Одно поле или несколько через запятую, например id или order_id, line_no"
          >
            <Input
              id={`${idPrefix}-pg-pk`}
              value={value.config.primary_key}
              onChange={(e) => patchPostgres({ primary_key: e.target.value })}
              placeholder="id"
              data-testid={`${idPrefix}-input-pg-primary-key`}
            />
          </Field>
          <Button
            type="button"
            variant="outline"
            onClick={() => onChange({ connector: "postgres", config: { ...POSTGRES_DESTINATION_DEFAULTS } })}
            data-testid={`${idPrefix}-button-pg-template`}
          >
            Подставить шаблон test_sink
          </Button>
        </div>
      ) : null}

      {value.connector === "csv" ? (
        <div className="space-y-3 rounded-md border border-dashed p-3" data-testid={`${idPrefix}-fields-csv`}>
          <p className="text-sm font-medium">CSV</p>
          <Field
            id={`${idPrefix}-csv-path`}
            label="Путь к файлу или каталогу"
            hint="Файл — запись в один CSV; каталог — для каждого потока создаётся отдельный файл"
          >
            <Input
              id={`${idPrefix}-csv-path`}
              value={value.config.path}
              onChange={(e) => patchCsv({ path: e.target.value })}
              placeholder="/data/exports/orders.csv или /data/exports/"
              data-testid={`${idPrefix}-input-csv-path`}
            />
          </Field>
          <Field
            id={`${idPrefix}-csv-filename`}
            label="Имя файла (если указан каталог)"
            hint="Пусто — имя формируется из названия потока, например orders.csv"
          >
            <Input
              id={`${idPrefix}-csv-filename`}
              value={value.config.filename}
              onChange={(e) => patchCsv({ filename: e.target.value })}
              placeholder="orders.csv"
              data-testid={`${idPrefix}-input-csv-filename`}
            />
          </Field>
        </div>
      ) : null}

      {value.connector === "xlsx" ? (
        <div className="space-y-3 rounded-md border border-dashed p-3" data-testid={`${idPrefix}-fields-xlsx`}>
          <p className="text-sm font-medium">Excel (.xlsx)</p>
          <Field id={`${idPrefix}-xlsx-path`} label="Путь к файлу .xlsx">
            <Input
              id={`${idPrefix}-xlsx-path`}
              value={value.config.path}
              onChange={(e) => patchXlsx({ path: e.target.value })}
              placeholder="/data/report.xlsx"
              data-testid={`${idPrefix}-input-xlsx-path`}
            />
          </Field>
          <Field
            id={`${idPrefix}-xlsx-sheet`}
            label="Имя листа"
            hint="Пусто — используется имя потока (до 31 символа)"
          >
            <Input
              id={`${idPrefix}-xlsx-sheet`}
              value={value.config.sheet_name}
              onChange={(e) => patchXlsx({ sheet_name: e.target.value })}
              placeholder="data"
              data-testid={`${idPrefix}-input-xlsx-sheet`}
            />
          </Field>
        </div>
      ) : null}

      {value.connector === "clickhouse" ? (
        <div className="space-y-3 rounded-md border border-dashed p-3" data-testid={`${idPrefix}-fields-clickhouse`}>
          <p className="text-sm font-medium">ClickHouse (HTTP)</p>
          <div className="grid gap-3 sm:grid-cols-2">
            <Field id={`${idPrefix}-ch-host`} label="Host">
              <Input
                id={`${idPrefix}-ch-host`}
                value={value.config.host}
                onChange={(e) => patchClickhouse({ host: e.target.value })}
                placeholder="localhost"
                data-testid={`${idPrefix}-input-ch-host`}
              />
            </Field>
            <Field id={`${idPrefix}-ch-port`} label="Порт (HTTP)">
              <Input
                id={`${idPrefix}-ch-port`}
                value={value.config.port}
                onChange={(e) => patchClickhouse({ port: e.target.value })}
                placeholder="8123"
                data-testid={`${idPrefix}-input-ch-port`}
              />
            </Field>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <Field id={`${idPrefix}-ch-database`} label="База данных">
              <Input
                id={`${idPrefix}-ch-database`}
                value={value.config.database}
                onChange={(e) => patchClickhouse({ database: e.target.value })}
                placeholder="default"
                data-testid={`${idPrefix}-input-ch-database`}
              />
            </Field>
            <Field id={`${idPrefix}-ch-table`} label="Таблица">
              <Input
                id={`${idPrefix}-ch-table`}
                value={value.config.table}
                onChange={(e) => patchClickhouse({ table: e.target.value })}
                placeholder="elt_load"
                data-testid={`${idPrefix}-input-ch-table`}
              />
            </Field>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <Field id={`${idPrefix}-ch-user`} label="Пользователь">
              <Input
                id={`${idPrefix}-ch-user`}
                value={value.config.user}
                onChange={(e) => patchClickhouse({ user: e.target.value })}
                placeholder="default"
                data-testid={`${idPrefix}-input-ch-user`}
              />
            </Field>
            <Field id={`${idPrefix}-ch-password`} label="Пароль">
              <Input
                id={`${idPrefix}-ch-password`}
                type="password"
                autoComplete="off"
                value={value.config.password}
                onChange={(e) => patchClickhouse({ password: e.target.value })}
                data-testid={`${idPrefix}-input-ch-password`}
              />
            </Field>
          </div>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={value.config.secure}
              onChange={(e) => patchClickhouse({ secure: e.target.checked })}
              data-testid={`${idPrefix}-checkbox-ch-secure`}
            />
            HTTPS (secure)
          </label>
        </div>
      ) : null}

      {validationError ? (
        <p className="text-sm text-hint" data-testid={`${idPrefix}-validation-hint`}>
          {validationError}
        </p>
      ) : null}
    </div>
  );
}
