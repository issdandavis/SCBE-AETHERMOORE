import { describe, expect, it } from "vitest";

const { authOk } = require("../api/_agent_common");

describe("agent dispatch auth", () => {
  it("fails closed when AGENT_DISPATCH_SECRET is unset", () => {
    const req = { headers: {} };
    expect(authOk(req, { dispatchSecret: "" })).toBe(false);
  });

  it("accepts bearer or x-agent-dispatch-secret when configured", () => {
    const reqWithBearer = { headers: { authorization: "Bearer top-secret" } };
    const reqWithHeader = { headers: { "x-agent-dispatch-secret": "top-secret" } };

    expect(authOk(reqWithBearer, { dispatchSecret: "top-secret" })).toBe(true);
    expect(authOk(reqWithHeader, { dispatchSecret: "top-secret" })).toBe(true);
  });
});
