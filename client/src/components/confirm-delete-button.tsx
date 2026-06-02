import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { formatApiErrorMessage } from "@/lib/api-client";

type ConfirmDeleteButtonProps = {
  entityLabel: string;
  onDelete: () => Promise<void>;
  onSuccess?: () => void;
  disabled?: boolean;
  disabledTitle?: string;
  testId: string;
  className?: string;
};

export function ConfirmDeleteButton({
  entityLabel,
  onDelete,
  onSuccess,
  disabled,
  disabledTitle,
  testId,
  className,
}: ConfirmDeleteButtonProps) {
  const [confirming, setConfirming] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const deleteMut = useMutation({
    mutationFn: onDelete,
    onSuccess: () => {
      setErr(null);
      setConfirming(false);
      onSuccess?.();
    },
    onError: (e: unknown) => {
      setErr(formatApiErrorMessage(e, "Не удалось удалить"));
    },
  });

  if (disabled) {
    return (
      <Button
        type="button"
        variant="outline"
        className={className}
        disabled
        title={disabledTitle}
        data-testid={testId}
      >
        Удалить
      </Button>
    );
  }

  if (confirming) {
    return (
      <span className="inline-flex flex-wrap items-center gap-1">
        <Button
          type="button"
          variant="destructive"
          className={className}
          disabled={deleteMut.isPending}
          data-testid={`${testId}-confirm`}
          onClick={() => deleteMut.mutate()}
        >
          {deleteMut.isPending ? "Удаление…" : "Да, удалить"}
        </Button>
        <Button
          type="button"
          variant="outline"
          className={className}
          disabled={deleteMut.isPending}
          data-testid={`${testId}-cancel`}
          onClick={() => {
            setConfirming(false);
            setErr(null);
          }}
        >
          Отмена
        </Button>
        {err ? (
          <span className="w-full text-xs text-destructive" data-testid={`${testId}-error`}>
            {err}
          </span>
        ) : null}
      </span>
    );
  }

  return (
    <Button
      type="button"
      variant="outline"
      className={className}
      data-testid={testId}
      onClick={() => {
        setErr(null);
        setConfirming(true);
      }}
      title={`Удалить: ${entityLabel}`}
    >
      Удалить
    </Button>
  );
}
