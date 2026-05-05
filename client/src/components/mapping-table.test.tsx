import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { MappingTable } from "@/components/mapping-table";
import { mappingRows } from "@/lib/mock-data";

describe("MappingTable", () => {
  it("renders mapping rows and filter button", () => {
    render(<MappingTable rows={mappingRows} />);
    expect(screen.getByTestId("table-mapping-stream-orders")).toBeInTheDocument();
    expect(screen.getByTestId("button-mapping-filter-unmapped")).toBeInTheDocument();
    expect(screen.getByTestId("row-mapping-order_id")).toBeInTheDocument();
  });
});
