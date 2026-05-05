import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ColumnRulesEditor } from "@/components/connection-wizard/column-rules-editor";

describe("ColumnRulesEditor", () => {
  it("renders mapping table via column rules editor", () => {
    const onChangeRow = vi.fn();
    render(
      <ColumnRulesEditor
        rows={[
          {
            id: "orders:id",
            streamName: "orders",
            sourceField: "id",
            targetField: "order.external_id",
            transformation: "",
            required: true,
          },
        ]}
        onChangeRow={onChangeRow}
      />,
    );
    expect(screen.getByTestId("wizard-step-mapping")).toBeInTheDocument();
    expect(screen.getByTestId("row-wizard-mapping-orders:id")).toBeInTheDocument();
  });
});

