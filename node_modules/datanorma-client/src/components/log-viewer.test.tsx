import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { LogViewer } from "@/components/log-viewer";
import { runLogs } from "@/lib/mock-data";

describe("LogViewer", () => {
  it("renders controls and log content", () => {
    render(<LogViewer logs={runLogs} />);
    expect(screen.getByTestId("panel-log-viewer")).toBeInTheDocument();
    expect(screen.getByTestId("input-log-search")).toBeInTheDocument();
    expect(screen.getByTestId("log-content")).toHaveTextContent("extract");
  });
});
