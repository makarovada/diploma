import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ConnectorConfigForm } from "@/components/connection-wizard/connector-config-form";

describe("ConnectorConfigForm", () => {
  it("renders Bitrix24 form instead of JSON textarea", () => {
    render(
      <ConnectorConfigForm
        connectorCode="bitrix24"
        configText={JSON.stringify({ webhook_url: "" }, null, 2)}
        needsPersist={false}
        onChangeText={vi.fn()}
        onSaveConfig={vi.fn()}
        saving={false}
        saveError={null}
      />,
    );

    expect(screen.getByTestId("wizard-connector-config-bitrix24")).toBeInTheDocument();
    expect(screen.getByTestId("form-bitrix24")).toBeInTheDocument();
    expect(screen.queryByTestId("textarea-source-config-json")).not.toBeInTheDocument();
  });
});
