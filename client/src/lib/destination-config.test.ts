import { describe, expect, it } from "vitest";
import {
  defaultDestinationConfig,
  destinationConfigToRecord,
  parseDestinationConfig,
  validateDestinationConfig,
} from "@/lib/destination-config";

describe("destination-config", () => {
  it("parses postgres config with table_name alias", () => {
    const state = parseDestinationConfig("postgres", { schema: "stg", table_name: "orders", primary_key: ["a", "b"] });
    expect(state.connector).toBe("postgres");
    if (state.connector === "postgres") {
      expect(state.config.table).toBe("orders");
      expect(state.config.primary_key).toBe("a, b");
    }
  });

  it("serializes clickhouse config", () => {
    const state = defaultDestinationConfig("clickhouse");
    if (state.connector === "clickhouse") {
      state.config.host = "ch.local";
      state.config.port = "8443";
      state.config.secure = true;
    }
    const rec = destinationConfigToRecord(state);
    expect(rec.host).toBe("ch.local");
    expect(rec.port).toBe(8443);
    expect(rec.secure).toBe(true);
  });

  it("validates xlsx extension", () => {
    const state = defaultDestinationConfig("xlsx");
    if (state.connector === "xlsx") state.config.path = "/tmp/out.csv";
    expect(validateDestinationConfig(state)).toMatch(/\.xlsx/);
  });
});
