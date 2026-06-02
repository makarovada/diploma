import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ColumnRulesEditor } from "@/components/connection-wizard/column-rules-editor";

describe("ColumnRulesEditor", () => {
  it("renders column rules table", () => {
    const onChangeRow = vi.fn();
    render(
      <ColumnRulesEditor
        layout="entities"
        entityLabels={{ orders: "Заказы" }}
        rows={[
          {
            id: "orders:id",
            entity: "orders",
            sourceField: "id",
            targetField: "id",
            ruleType: "integer",
            required: true,
          },
        ]}
        onChangeRow={onChangeRow}
      />,
    );
    expect(screen.getByTestId("wizard-step-column-rules")).toBeTruthy();
    expect(screen.getByTestId("row-wizard-column-rule-orders:id")).toBeTruthy();
  });

  it("hides entity column for flat layout", () => {
    render(
      <ColumnRulesEditor
        layout="flat"
        entityLabels={{}}
        rows={[
          {
            id: "x:id",
            entity: null,
            sourceField: "id",
            targetField: "id",
            ruleType: "integer",
            required: false,
          },
        ]}
        onChangeRow={vi.fn()}
      />,
    );
    expect(screen.queryByText("Сущность")).toBeNull();
  });
});
