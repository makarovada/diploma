import { CheckCircle2, Circle, Loader2, XCircle } from "lucide-react";
import type { Status } from "@/lib/types";

const stages = ["Extract", "Staging", "Normalize", "Validate", "Load", "Complete"];

export function StageTimeline({ status }: { status: Status }) {
  const statusIcon = (idx: number) => {
    if (status === "failed" && idx >= 4) return <XCircle className="h-4 w-4 text-destructive" />;
    if (status === "running" && idx === 2) return <Loader2 className="h-4 w-4 animate-spin text-info" />;
    if (status === "success" || status === "partial") return <CheckCircle2 className="h-4 w-4 text-success" />;
    return <Circle className="h-4 w-4 text-muted-foreground" />;
  };

  return (
    <div className="grid gap-2 rounded-lg border bg-card p-4 md:grid-cols-6" data-testid="timeline-run-stage">
      {stages.map((stage, idx) => (
        <div key={stage} className="flex items-center gap-2 text-sm" data-testid={`timeline-run-stage-${stage.toLowerCase()}`}>
          {statusIcon(idx)}
          <span>{stage}</span>
        </div>
      ))}
    </div>
  );
}
