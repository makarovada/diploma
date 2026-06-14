import { describe, expect, it } from "vitest";
import {
  computeStreamHealth,
  explainIssue,
  explainIssuesBanner,
  explainSyncRunError,
  streamHealthLabel,
} from "@/lib/issue-explanations";
import { mapNormRowToIssue } from "@/lib/api-datanorma";

describe("issue-explanations", () => {
  it("returns Russian text for known error codes", () => {
    for (const code of ["required_missing", "cast_error", "destination_write_failed", "elt_sync_failed"]) {
      const exp = explainIssue(code);
      expect(exp.title.length).toBeGreaterThan(0);
      expect(exp.description.length).toBeGreaterThan(0);
      expect(exp.recommendedAction.length).toBeGreaterThan(0);
    }
  });

  it("falls back for unknown codes", () => {
    const exp = explainIssue("unknown_xyz");
    expect(exp.title).toContain("нормализац");
  });

  it("uses error message for elt_sync_failed", () => {
    const exp = explainSyncRunError("Не удалось подключиться к API");
    expect(exp.description).toContain("API");
  });

  it("formats issues banner", () => {
    expect(explainIssuesBanner(1)).toContain("1 запись");
    expect(explainIssuesBanner(5)).toContain("5 записей");
  });

  it("computes stream health states", () => {
    expect(computeStreamHealth({ streamName: "a", enabled: false, openIssueCount: 0, isRunning: false })).toBe("disabled");
    expect(streamHealthLabel("warning")).toBe("Есть проблемы");
  });
});

describe("mapNormRowToIssue enrichment", () => {
  it("adds title and connectionId from DTO", () => {
    const issue = mapNormRowToIssue({
      id: 1,
      issue_type: "required_missing",
      connection_id: 42,
      sync_run_id: 7,
      stream_name: "orders",
      target_field: "amount",
      error_text: "empty",
      raw_value: " ",
      status: "open",
    });
    expect(issue.title).toBe("Обязательное поле пустое");
    expect(issue.connectionId).toBe("42");
    expect(issue.syncRunId).toBe("7");
  });
});
