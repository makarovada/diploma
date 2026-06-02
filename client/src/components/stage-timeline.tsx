import { CheckCircle2, Circle, Loader2, XCircle } from "lucide-react";
import type { Status } from "@/lib/types";

const stages: Array<{ code: string; label: string }> = [
  { code: "extract", label: "Extract" },
  { code: "staging_raw", label: "Staging raw" },
  { code: "normalize", label: "Normalize" },
  { code: "dbt_run", label: "dbt run" },
  { code: "validate", label: "Validate" },
  { code: "complete", label: "Complete" },
];

export function StageTimeline({ status, currentStage }: { status: Status; currentStage?: string }) {
  const activeIdx = Math.max(0, stages.findIndex((s) => s.code === currentStage));
  const statusIcon = (idx: number) => {
    if (status === "failed" && idx === activeIdx) return <XCircle className="h-4 w-4 text-destructive" />;
    if (status === "running" && idx === activeIdx) return <Loader2 className="h-4 w-4 animate-spin text-info" />;
    if (status === "partial" && idx <= activeIdx) return <CheckCircle2 className="h-4 w-4 text-warning" />;
    if (status === "success" && idx <= activeIdx) return <CheckCircle2 className="h-4 w-4 text-success" />;
    if (status === "failed" && idx < activeIdx) return <CheckCircle2 className="h-4 w-4 text-success" />;
    return <Circle className="h-4 w-4 text-muted-foreground" />;
  };

  return (
    <div className="grid gap-2 rounded-lg border bg-card p-4 md:grid-cols-6" data-testid="timeline-run-stage">
      {stages.map((stage, idx) => (
        <div key={stage.code} className="flex items-center gap-2 text-sm" data-testid={`timeline-run-stage-${stage.code}`}>
          {statusIcon(idx)}
          <span>{stage.label}</span>
        </div>
      ))}
    </div>
  );
}
