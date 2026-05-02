import type { ReactNode } from "react";

export function PageHeader({
  title,
  description,
  actions,
  breadcrumbs,
}: {
  title: string;
  description: string;
  actions?: ReactNode;
  breadcrumbs: string;
}) {
  return (
    <div className="mb-4 flex flex-wrap items-start justify-between gap-4" data-testid={`header-${title.toLowerCase().replace(/\s+/g, "-")}`}>
      <div>
        <p className="text-xs text-muted-foreground">{breadcrumbs}</p>
        <h1 className="text-xl font-semibold">{title}</h1>
        <p className="text-sm text-muted-foreground">{description}</p>
      </div>
      {actions}
    </div>
  );
}
