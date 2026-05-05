import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { StatusBadge } from "@/components/status-badge";

describe("StatusBadge", () => {
  it("renders localized label for running status", () => {
    render(<StatusBadge status="running" testId="status-badge" />);
    expect(screen.getByTestId("status-badge")).toHaveTextContent("Выполняется");
  });
});
