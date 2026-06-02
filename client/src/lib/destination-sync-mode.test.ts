import { describe, expect, it } from "vitest";
import {
  encodeCursorFields,
  encodePrimaryKeyFields,
  fieldsFromReplicationPreset,
  parseCursorFields,
  parsePrimaryKeyFields,
  replicationPresetFromFields,
  suggestPrimaryKeyField,
} from "@/lib/destination-sync-mode";

describe("destination-sync-mode", () => {
  it("maps full overwrite preset to backend fields", () => {
    expect(fieldsFromReplicationPreset("full_overwrite")).toEqual({
      sync_mode: "full_refresh",
      destination_sync_mode: "refresh_overwrite",
    });
  });

  it("maps incremental dedup preset", () => {
    expect(fieldsFromReplicationPreset("incremental_dedup")).toEqual({
      sync_mode: "incremental",
      destination_sync_mode: "append_dedup",
    });
  });

  it("detects preset from stored fields", () => {
    expect(
      replicationPresetFromFields("incremental", "append_dedup"),
    ).toBe("incremental_dedup");
    expect(
      replicationPresetFromFields("full_refresh", "refresh_overwrite"),
    ).toBe("full_overwrite");
  });

  it("suggests id-like primary key", () => {
    expect(suggestPrimaryKeyField(["name", "order_id", "amount"])).toBe("order_id");
    expect(suggestPrimaryKeyField(["title"])).toBe("title");
  });

  it("parses primary key list from string and json", () => {
    expect(parsePrimaryKeyFields("id")).toEqual(["id"]);
    expect(parsePrimaryKeyFields("id, tenant_id")).toEqual(["id", "tenant_id"]);
    expect(parsePrimaryKeyFields('["id","tenant_id"]')).toEqual(["id", "tenant_id"]);
  });

  it("encodes multiple primary keys for API", () => {
    expect(encodePrimaryKeyFields(["id"])).toBe("id");
    expect(encodePrimaryKeyFields(["id", "tenant_id"])).toBe('["id","tenant_id"]');
    expect(encodePrimaryKeyFields([])).toBeNull();
  });

  it("parses and encodes cursor field lists", () => {
    expect(parseCursorFields("updated_at")).toEqual(["updated_at"]);
    expect(parseCursorFields("updated_at, id")).toEqual(["updated_at", "id"]);
    expect(parseCursorFields('["updated_at","id"]')).toEqual(["updated_at", "id"]);
    expect(encodeCursorFields(["updated_at"])).toBe("updated_at");
    expect(encodeCursorFields(["updated_at", "id"])).toBe('["updated_at","id"]');
  });
});
