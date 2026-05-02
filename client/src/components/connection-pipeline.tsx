import { ArrowRight, Database, GitMerge, HardDriveDownload, Layers } from "lucide-react";
import { cn } from "@/lib/utils";

const steps = [
  { key: "source", label: "Источник", Icon: Database },
  { key: "streams", label: "Потоки", Icon: Layers },
  { key: "normalize", label: "Нормализация", Icon: GitMerge },
  { key: "dest", label: "Приёмник", Icon: HardDriveDownload },
];

export function ConnectionPipeline({
  sourceLabel,
  destLabel,
  className,
}: {
  sourceLabel: string;
  destLabel: string;
  className?: string;
}) {
  return (
    <div data-testid="connection-pipeline" className={cn("flex flex-wrap items-center gap-2 rounded-lg border bg-card px-4 py-3 text-sm", className)}>
      {steps.map((s, i) => (
        <div key={s.key} className="flex items-center gap-2">
          {i > 0 ? <ArrowRight className="h-4 w-4 shrink-0 text-muted-foreground" /> : null}
          <div
            className="flex items-center gap-2 rounded-md bg-muted/60 px-2 py-1"
            data-testid={`pipeline-step-${s.key}`}
          >
            <s.Icon className="h-4 w-4 text-primary" />
            <span className="font-medium">{s.label}</span>
            {s.key === "source" ? <span className="text-muted-foreground">· {sourceLabel}</span> : null}
            {s.key === "dest" ? <span className="text-muted-foreground">· {destLabel}</span> : null}
          </div>
        </div>
      ))}
    </div>
  );
}
