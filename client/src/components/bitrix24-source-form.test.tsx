import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it } from "vitest";
import {
  Bitrix24SourceForm,
  bitrix24ConfigToRecord,
  normalizeBitrix24WebhookUrl,
  parseBitrix24Config,
  validateBitrix24Config,
} from "@/components/bitrix24-source-form";

describe("normalizeBitrix24WebhookUrl", () => {
  it("strips profile.json suffix", () => {
    expect(normalizeBitrix24WebhookUrl("https://x.bitrix24.ru/rest/1/abc/profile.json")).toBe(
      "https://x.bitrix24.ru/rest/1/abc",
    );
  });

  it("trims trailing slashes", () => {
    expect(normalizeBitrix24WebhookUrl("https://x.bitrix24.ru/rest/1/abc/")).toBe(
      "https://x.bitrix24.ru/rest/1/abc",
    );
  });
});

describe("validateBitrix24Config", () => {
  it("accepts valid webhook base", () => {
    expect(
      validateBitrix24Config({
        webhook_url: "https://b24-rljb1z.bitrix24.ru/rest/1/k7xsg7gdhh8bxql5/",
      }),
    ).toBeNull();
  });

  it("accepts profile.json URL after normalization", () => {
    expect(
      validateBitrix24Config({
        webhook_url: "https://b24-rljb1z.bitrix24.ru/rest/1/k7xsg7gdhh8bxql5/profile.json",
      }),
    ).toBeNull();
  });
});

describe("Bitrix24SourceForm", () => {
  it("renders webhook input and emits changes", async () => {
    const user = userEvent.setup();

    function Harness() {
      const [cfg, setCfg] = useState({ webhook_url: "" });
      return <Bitrix24SourceForm value={cfg} onChange={setCfg} />;
    }

    render(<Harness />);
    const input = screen.getByTestId("input-bitrix24-webhook-url");
    await user.type(input, "https://portal.bitrix24.ru/rest/1/secret");
    expect(input).toHaveValue("https://portal.bitrix24.ru/rest/1/secret");
  });
});

describe("parseBitrix24Config / bitrix24ConfigToRecord", () => {
  it("round-trips normalized config", () => {
    const parsed = parseBitrix24Config({ webhook_url: "https://x.bitrix24.ru/rest/1/abc/profile.json" });
    expect(bitrix24ConfigToRecord(parsed)).toEqual({ webhook_url: "https://x.bitrix24.ru/rest/1/abc" });
  });
});
