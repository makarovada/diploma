import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { MappingTable } from "@/components/mapping-table";
import type { MappingRow } from "@/lib/types";

const mappingRows: MappingRow[] = [
  {
    sourceField: "order_id",
    type: "string",
    targetField: "order.external_id",
    transformation: "",
    required: true,
    sample: "123",
    preview: "123",
    state: "mapped",
  },
];

describe("MappingTable", () => {
  it("renders mapping rows and filter button", () => {
    render(<MappingTable rows={mappingRows} />);
    expect(screen.getByTestId("table-mapping-stream-orders")).toBeInTheDocument();
    expect(screen.getByTestId("button-mapping-filter-unmapped")).toBeInTheDocument();
    expect(screen.getByTestId("row-mapping-order_id")).toBeInTheDocument();
  });
});
