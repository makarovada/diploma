import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ConnectionWizardPage } from "@/pages/connection-wizard";

vi.mock("@/components/connection-wizard/connection-wizard-shell", () => ({
  ConnectionWizardShell: () => <div data-testid="wizard-shell-smoke">Wizard shell</div>,
}));

describe("ConnectionWizardPage", () => {
  it("renders wizard shell", () => {
    render(<ConnectionWizardPage />);
    expect(screen.getByTestId("wizard-shell-smoke")).toBeInTheDocument();
  });
});
