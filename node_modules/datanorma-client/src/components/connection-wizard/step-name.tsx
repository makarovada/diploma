import { Input } from "@/components/ui/input";

type Props = {
  name: string;
  description: string;
  onChange: (patch: { connectionName?: string; connectionDescription?: string }) => void;
  nameError?: string | null;
};

export function StepName({ name, description, onChange, nameError }: Props) {
  return (
    <div className="rounded-lg border bg-card p-4" data-testid="wizard-step-name">
      <label className="block text-sm font-medium" htmlFor="wizard-connection-name">
        Название подключения <span className="text-destructive">*</span>
      </label>
      <Input
        id="wizard-connection-name"
        className="mt-1 max-w-lg"
        value={name}
        onChange={(e) => onChange({ connectionName: e.target.value })}
        placeholder="Например: Ozon → склад"
        data-testid="input-connection-name"
        aria-invalid={Boolean(nameError)}
      />
      {nameError ? (
        <p className="mt-1 text-sm text-destructive" data-testid="error-connection-name">
          {nameError}
        </p>
      ) : null}

      <label className="mt-4 block text-sm font-medium" htmlFor="wizard-connection-description">
        Описание
      </label>
      <Input
        id="wizard-connection-description"
        className="mt-1 max-w-lg"
        value={description}
        onChange={(e) => onChange({ connectionDescription: e.target.value })}
        placeholder="Необязательно"
        data-testid="input-connection-description"
      />
    </div>
  );
}
