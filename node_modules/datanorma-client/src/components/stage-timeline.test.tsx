import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { StageTimeline } from "@/components/stage-timeline";

describe("StageTimeline", () => {
  it("renders dbt_run stage in pipeline", () => {
    render(<StageTimeline status="running" currentStage="dbt_run" />);
    expect(screen.getByTestId("timeline-run-stage-dbt_run")).toBeInTheDocument();
  });
});
