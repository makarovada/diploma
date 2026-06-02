import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { MappingTable } from "@/components/mapping-table";

describe("MappingTable", () => {
  it("renders column rule rows", () => {
    render(
      <MappingTable
        rows={[
          {
            entity: null,
            source_field: "order_id",
            target_field: "order_id",
            type: "integer",
            required: true,
          },
        ]}
      />,
    );
    expect(screen.getByTestId("table-mapping")).toBeTruthy();
    expect(screen.getByTestId("row-mapping-:order_id")).toBeTruthy();
  });

  it("shows empty state", () => {
    render(<MappingTable rows={[]} />);
    expect(screen.getByTestId("table-mapping-empty")).toBeTruthy();
  });
});
