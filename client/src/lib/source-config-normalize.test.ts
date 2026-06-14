import { describe, expect, it } from "vitest";
import { normalizeSourceConfigForConnector, normalizeSourceConfigTextForConnector } from "@/lib/source-config-normalize";

describe("normalizeSourceConfigForConnector", () => {
  it("strips profile.json from bitrix24 webhook_url", () => {
    const out = normalizeSourceConfigForConnector("bitrix24", {
      webhook_url: "https://b24-rljb1z.bitrix24.ru/rest/1/k7xsg7gdhh8bxql5/profile.json",
    });
    expect(out).toEqual({
      webhook_url: "https://b24-rljb1z.bitrix24.ru/rest/1/k7xsg7gdhh8bxql5",
    });
  });

  it("leaves other connectors unchanged", () => {
    const cfg = { api_token: "x" };
    expect(normalizeSourceConfigForConnector("yandex_metrika", cfg)).toBe(cfg);
  });
});

describe("normalizeSourceConfigTextForConnector", () => {
  it("normalizes bitrix24 JSON text", () => {
    const text = JSON.stringify(
      { webhook_url: "https://x.bitrix24.ru/rest/1/abc/profile.json/" },
      null,
      2,
    );
    const out = normalizeSourceConfigTextForConnector("bitrix24", text);
    expect(JSON.parse(out)).toEqual({ webhook_url: "https://x.bitrix24.ru/rest/1/abc" });
  });
});
