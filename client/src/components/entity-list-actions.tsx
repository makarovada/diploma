import { LinkAsButton } from "@/components/link-as-button";
import { ConfirmDeleteButton } from "@/components/confirm-delete-button";

type EntityListActionsProps = {
  editHref: string;
  editTestId: string;
  deleteTestId: string;
  entityLabel: string;
  onDelete: () => Promise<void>;
  onDeleteSuccess?: () => void;
  deleteDisabled?: boolean;
  deleteDisabledTitle?: string;
};

export function EntityListActions({
  editHref,
  editTestId,
  deleteTestId,
  entityLabel,
  onDelete,
  onDeleteSuccess,
  deleteDisabled,
  deleteDisabledTitle,
}: EntityListActionsProps) {
  return (
    <div className="flex flex-wrap items-center gap-1" data-testid={`${deleteTestId}-group`}>
      <LinkAsButton href={editHref} variant="outline" className="px-2 py-1 text-xs" data-testid={editTestId}>
        Изменить
      </LinkAsButton>
      <ConfirmDeleteButton
        entityLabel={entityLabel}
        onDelete={onDelete}
        onSuccess={onDeleteSuccess}
        disabled={deleteDisabled}
        disabledTitle={deleteDisabledTitle}
        testId={deleteTestId}
        className="px-2 py-1 text-xs"
      />
    </div>
  );
}
