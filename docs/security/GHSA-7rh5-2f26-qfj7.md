# GHSA-7rh5-2f26-qfj7 code-path notes

The GitHub advisory API returned HTTP 403 to the token available for this change, so the advisory text itself was not read. The prior triage at `c37f45be93c177d66e85f18a0e1f3ba935977e82` named three code paths. Each was checked in the tree at that commit before editing:

| Claim | Code at that commit | Result |
| --- | --- | --- |
| Cross-tenant audit read | `api/main.py` `get_audit` required an API key, then returned `DECISIONS_STORE[decision_id]` with no tenant comparison. `get_agent`, audit report, and audit export already scope by tenant. | Confirmed in the in-memory governance API. |
| Unauthenticated `/mesh` and `/search` | `src/api/mesh_routes.py` and `src/api/search_routes.py` define no API-key dependency. `src/api/main.py` mounted both routers without one. `api/main.py` mounted `/mesh` the same way. `/search` is not mounted on `api/main.py`. | Confirmed. |
| Connector SSRF | `src/api/main.py` stored `endpoint_url` as given and `urlopen` followed it, including redirects and environment proxies. | Confirmed for the mobile connector dispatcher. |

No live deployment, production host, or external scanner was probed. A code-path fix does not show that any deployed service is exposed, patched, or restarted.

## What changed

- `GET /v1/audit/{decision_id}` returns the record only when `record["tenant"]` equals the authenticated tenant. A missing record and another tenant's record both return 404 with the same detail.
- `/mesh/*` on both FastAPI apps and `/search/*` on `src/api/main.py` use that app's existing `verify_api_key` dependency. The shared routers stay free of a hard-coded key store so each app keeps its own header and key source.
- Connector registration and dispatch use `src/api/connector_url_policy.py`. Dispatch resolves names, rejects any blocked answer, rechecks each redirect, ignores `HTTP_PROXY` / `HTTPS_PROXY`, and checks the connected peer before the response body is read.

## Compatibility

Default mode accepts public `https` URLs, including the Zapier, public n8n, Shopify `*.myshopify.com`, and generic webhook shapes already used by the mobile connector templates. `https://example.invalid/...` still registers; dispatch fails later if the name does not resolve.

These destinations are rejected until an operator sets the matching flag:

| Destination | Flag |
| --- | --- |
| Loopback, RFC1918, ULA, CGNAT, `.local`, `.internal`, or a single-label host | `SCBE_CONNECTOR_ALLOW_PRIVATE_NETWORKS=1` |
| Plain `http` | `SCBE_CONNECTOR_ALLOW_INSECURE_HTTP=1` |

`http://localhost:5678/...` needs both flags. Link-local addresses, `169.254.169.254`, `100.100.100.200`, `fd00:ec2::254`, and metadata hostnames stay blocked with the flags on. `shop_domain` must be one `<shop>.myshopify.com` label. Connector calls do not use process proxy variables. `Host` and hop-by-hop headers are rejected.

Clients that called `/mesh` or `/search` without an API key now receive 401. `src/api/main.py` accepts `x-api-key` or `SCBE_api_key`. `api/main.py` accepts `SCBE_api_key` or `X-API-Key`. `/health` on each app is unchanged.

## False positives

- A public name with any private or link-local address in its DNS answers is rejected, including split-horizon records.
- Hosts that only exist on a LAN, `.local`, or `.internal` name fail closed until the private-network flag is set.
- Non-canonical IP spellings (`2130706433`, octal dotted forms) are rejected even when they would mean a public address.
- Underscore hostnames and non-myshopify shop domains are rejected. A Shopify proxy on another public https host can still be entered as `endpoint_url`.
- IPv4-mapped peers are judged by the embedded IPv4 address so ordinary dual-stack answers are not treated as reserved.

## Residual risk

- Authenticated `/mesh` and `/search` callers still share one index. This change requires an API key; it does not add per-tenant rows.
- DNS can change between the preflight lookup and `connect()`. The peer check runs at the start of `connect()`, after the TCP handshake and, for https, after the TLS handshake. The connector payload and `Authorization` header are not written when that peer is blocked. A metadata service that answered from the handshake alone is outside what this check covers.
- Redirects are limited to three and must pass the same policy. Cross-origin and non-https redirects drop caller headers. Same-origin https redirects keep them.
- Other outbound callers (Polly, free-LLM, Stripe, n8n bridge) were not part of the confirmed paths and were not changed.
- The connector store is in-memory. A process that registered a connector before this code is loaded does not keep that registration across a restart; dispatch also rechecks the URL.
- Repository advisory text, CVSS, and affected packages could not be confirmed from the advisory API. Whether any internet-facing deployment runs these routes was not tested.
