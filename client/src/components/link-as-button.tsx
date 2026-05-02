import { Link } from "wouter";
import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

type Variant = "default" | "outline";

export type LinkAsButtonProps = {
  href: string;
  variant?: Variant;
  className?: string;
  children?: ReactNode;
  replace?: boolean;
  "data-testid"?: string;
};

/** Ссылка, стилизованная как кнопка — без вложения `<button>` внутри `<a>`. */
export function LinkAsButton({ variant = "default", className, children, href, replace, "data-testid": dataTestId }: LinkAsButtonProps) {
  return (
    <Link
      href={href}
      replace={replace}
      data-testid={dataTestId}
      className={cn(
        "inline-flex items-center justify-center rounded-md px-3 py-2 text-sm font-medium transition-colors",
        variant === "default" && "bg-primary text-primary-foreground hover:opacity-90",
        variant === "outline" && "border bg-card hover:bg-muted",
        className,
      )}
    >
      {children}
    </Link>
  );
}
