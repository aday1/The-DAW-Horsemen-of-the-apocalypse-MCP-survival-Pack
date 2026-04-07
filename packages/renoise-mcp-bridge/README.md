# Renoise MCP bridge

Node.js stdio MCP server that forwards tool list and calls to **ReMCP** (HTTP) inside Renoise.

## Versions

- Bridge package: 1.0.2 (`package.json`)
- Upstream URL default: `http://127.0.0.1:19714/mcp` (override with `RENOISE_MCP_URL` or `node bridge.js <url>`)

## Setup

1. Install **Renoise** and the **ReMCP / Renoise MCP** component (see that tool’s documentation; it runs inside Renoise and opens an HTTP MCP endpoint).
2. In Renoise, **start the MCP server** from the tool (default URL is often `http://127.0.0.1:19714/mcp`).
3. In this folder run **`npm install`**.
4. **Cursor MCP**: command `node`, argument: full path to `bridge.js`, `cwd`: this directory. If your URL differs, set env **`RENOISE_MCP_URL`**.
5. Start Cursor; the bridge will retry until Renoise’s server is up.

### Helper prompts

Ask the assistant: *Walk me through installing Renoise MCP end-to-end with my real paths* — or enable **`RENOISE_MCP_DASHBOARD=1`** and use the Installation section on http://127.0.0.1:3849/

## Optional dashboard

Set `RENOISE_MCP_DASHBOARD=1` in the MCP process environment. After the bridge connects upstream, open http://127.0.0.1:3849/ for cached tool names, doc links, and starter prompts. JSON: http://127.0.0.1:3849/api/reference

## Related paths

- **DriveByMoss (VAday OSC fork)**: `temp_drivenbymoss/` — build with Maven, install the `.bwextension` per DrivenByMoss docs (used with Bitwig, not Renoise).

## GitHub backup

Create a new empty repository, then from this directory:

    git remote add origin https://github.com/<you>/<repo>.git
    git branch -M main
    git push -u origin main

Do not commit `node_modules/` (see `.gitignore`).
