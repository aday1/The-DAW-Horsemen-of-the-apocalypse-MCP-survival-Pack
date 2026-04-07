/**
 * Stdio MCP bridge -> ReMCP streamable HTTP (Renoise).
 * Logs to stderr only; stdout is reserved for JSON-RPC.
 *
 * Optional local reference UI:
 *   RENOISE_MCP_DASHBOARD=1
 *   RENOISE_MCP_DASHBOARD_PORT=3849 (default)
 */
import http from 'node:http';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StreamableHTTPClientTransport } from '@modelcontextprotocol/sdk/client/streamableHttp.js';
import { SSEClientTransport } from '@modelcontextprotocol/sdk/client/sse.js';
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  ListToolsRequestSchema,
  CallToolRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';

const BRIDGE_VERSION = '1.0.2';

const INSTALL_STEPS = [
  'Install Renoise and the ReMCP / Renoise MCP extension or tool that exposes an HTTP MCP endpoint (see that project docs).',
  'In Renoise, start the MCP server from the tool UI so something is listening (default often http://127.0.0.1:19714/mcp).',
  'On this machine: open a shell in the RenoiseMCP folder, run npm install.',
  'Register this bridge in Cursor MCP settings: command node, args: full path to bridge.js, cwd: this folder.',
  'If the URL is not the default, set env RENOISE_MCP_URL to your /mcp URL.',
  'Optional: RENOISE_MCP_DASHBOARD=1 and open http://127.0.0.1:3849/ for cached tool names and prompts.',
];

function log(...args) {
  console.error('[renoise-bridge]', ...args);
}

function escHtml(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

const SAMPLE_PROMPTS = [
  [
    'Install checklist (human)',
    'Walk me through installing Renoise MCP end-to-end: Renoise + ReMCP server running, Node bridge deps, ' +
      'and a Cursor mcp.json block using my real paths. Mention RENOISE_MCP_URL if my port is not 19714.',
  ],
  [
    'EDM pattern sketch',
    'Using Renoise MCP tools: inspect the current song structure, add or rename patterns for intro/build/drop, ' +
      'and place notes on a 4-on-the-floor kick with offbeat hats. Keep everything inside Renoise pattern limits.',
  ],
  [
    'Breakcore chops',
    'Use Renoise MCP to duplicate a break pattern, apply sample offsets or micro-edits via available tools, ' +
      'and suggest BPM around 160-180 with syncopated snares. If the API exposes sample commands, apply them.',
  ],
  [
    'Glitch texture pass',
    'Through Renoise MCP, automate or sequence glitch-friendly parameters (bit depth, repeat, send levels) on the ' +
      'selected track or instrument. Prefer small random variations every few lines.',
  ],
];

let _cachedTools = [];
let _cachedUpstreamUrl = '';

function dashboardEnabled() {
  const v = (process.env.RENOISE_MCP_DASHBOARD || '').trim().toLowerCase();
  return ['1', 'true', 'yes', 'on'].includes(v);
}

async function refreshToolCache(upstream) {
  try {
    const r = await upstream.listTools({});
    _cachedTools = Array.isArray(r?.tools) ? r.tools : [];
  } catch (e) {
    log('listTools for dashboard cache failed:', e?.message || e);
    _cachedTools = [];
  }
}

function referenceJson() {
  const names = _cachedTools.map((t) => t.name).filter(Boolean).sort();
  return {
    bridge_version: BRIDGE_VERSION,
    upstream_url: _cachedUpstreamUrl,
    tool_count: names.length,
    tools: names,
    sample_prompts: SAMPLE_PROMPTS.map(([title, prompt]) => ({ title, prompt })),
    installation: {
      steps: INSTALL_STEPS,
      env: {
        RENOISE_MCP_URL: 'Override default http://127.0.0.1:19714/mcp',
        RENOISE_BRIDGE_RETRIES: 'Connection retries (default 60)',
        RENOISE_BRIDGE_DELAY_MS: 'Delay between retries ms (default 500)',
        RENOISE_MCP_DASHBOARD: 'Set 1/true for http://127.0.0.1:3849/',
        RENOISE_MCP_DASHBOARD_PORT: 'Dashboard base port (default 3849)',
      },
      note:
        'This repo is only the stdio bridge; Renoise-side ReMCP is installed from its own package.',
    },
    links: {
      renoise_api: 'https://github.com/renoise/xrnx',
      renoise_tools: 'https://github.com/renoise/tools',
    },
  };
}

function dashboardHtml() {
  const pj = JSON.stringify(referenceJson(), null, 2);
  const promptBlocks = SAMPLE_PROMPTS.map(
    ([title, text], i) =>
      `<div class="pc"><h4>${escHtml(title)}</h4><pre id="rp${i}">${escHtml(text)}</pre>` +
      `<button type="button" data-c="rp${i}">Copy</button></div>`,
  ).join('');
  const tools = referenceJson().tools
    .map((n) => `<li><code>${escHtml(n)}</code></li>`)
    .join('');
  return `<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"/><title>Renoise MCP bridge</title>
<style>
body{font-family:system-ui,sans-serif;background:#0f1419;color:#c8d0d8;margin:0;padding:16px 20px;line-height:1.45;font-size:14px}
h1{font-size:1.1rem;color:#eab308;margin:0 0 8px 0}
.tag{color:#6b7a88;font-size:12px;max-width:900px;margin-bottom:14px}
a{color:#93c5fd}
pre{white-space:pre-wrap;word-break:break-word;background:#151b24;border:1px solid #2a3440;padding:10px;border-radius:6px;font-size:12px;color:#b8c4d0}
ul{columns:2;column-gap:24px}
@media(max-width:720px){ul{columns:1}}
li{margin:2px 0}
.pc{background:#151b24;border:1px solid #2a3440;border-radius:8px;padding:12px;margin:12px 0}
.pc h4{margin:0 0 8px 0;color:#eab308;font-size:13px}
button{background:#ca8a04;color:#0f1419;border:none;padding:5px 12px;border-radius:5px;cursor:pointer;font-size:12px}
</style></head><body>
<h1>Renoise MCP bridge dashboard</h1>
<p class="tag">Stdio bridge to ReMCP at <code>${escHtml(_cachedUpstreamUrl)}</code>. Enable with <code>RENOISE_MCP_DASHBOARD=1</code>. JSON: <a href="/api/reference">/api/reference</a></p>
<p class="tag">Human docs: <a href="https://github.com/renoise/xrnx">XRNX / Lua API</a>, <a href="https://github.com/renoise/tools">tools</a>. Tool names below are cached from the live upstream server.</p>
<h2 style="color:#e6edf3;font-size:1rem">Installation</h2>
<ol style="color:#b8c4d0;font-size:13px;line-height:1.5">${INSTALL_STEPS.map((s) => '<li>' + escHtml(s) + '</li>').join('')}</ol>
<p class="tag">There is no separate install tool in this bridge; use the checklist above or ask the model with the first starter prompt.</p>
<h2 style="color:#e6edf3;font-size:1rem">Cached tools (${referenceJson().tool_count})</h2>
<ul>${tools || '<li>(connect Renoise ReMCP to populate)</li>'}</ul>
<h2 style="color:#e6edf3;font-size:1rem">Starter prompts</h2>
${promptBlocks}
<h2 style="color:#e6edf3;font-size:1rem">Raw reference JSON</h2>
<pre>${escHtml(pj)}</pre>
<script>
document.querySelectorAll('button[data-c]').forEach(function(b){
  b.onclick=function(){var id=b.getAttribute('data-c');var el=document.getElementById(id);
  if(el)navigator.clipboard.writeText(el.textContent||'');};
});
</script>
</body></html>`;
}

function startDashboard() {
  if (!dashboardEnabled()) return;
  const base = Number(process.env.RENOISE_MCP_DASHBOARD_PORT || 3849);
  let attempt = 0;
  const handler = (req, res) => {
    const u = req.url || '/';
    if (u === '/' || u.startsWith('/?')) {
      res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
      res.end(dashboardHtml());
    } else if (u.startsWith('/api/reference')) {
      res.writeHead(200, {
        'Content-Type': 'application/json',
        'Cache-Control': 'no-store',
      });
      res.end(JSON.stringify(referenceJson(), null, 2));
    } else {
      res.writeHead(404);
      res.end();
    }
  };
  const tryListen = () => {
    if (attempt >= 12) {
      log('dashboard could not bind a port');
      return;
    }
    const port = base + attempt;
    attempt += 1;
    const srv = http.createServer(handler);
    srv.on('error', () => tryListen());
    srv.listen(port, '127.0.0.1', () => {
      log('dashboard http://127.0.0.1:' + port + '/');
    });
  };
  tryListen();
}

function targetUrl() {
  const fromEnv = process.env.RENOISE_MCP_URL;
  const fromArg = process.argv[2];
  const u = fromEnv || fromArg || 'http://127.0.0.1:19714/mcp';
  try {
    return new URL(u);
  } catch (e) {
    log('Bad URL:', u, e);
    process.exit(1);
  }
}

async function connectUpstream(url) {
  const retries = Number(process.env.RENOISE_BRIDGE_RETRIES || 60);
  const delayMs = Number(process.env.RENOISE_BRIDGE_DELAY_MS || 500);
  let lastErr;
  for (let i = 0; i < retries; i++) {
    const client = new Client({ name: 'renoise-bridge', version: BRIDGE_VERSION });
    if (process.env.RENOISE_BRIDGE_DEBUG === '1') {
      client.onerror = (err) => log('upstream client error:', err);
    }
    try {
      const t1 = new StreamableHTTPClientTransport(url);
      await client.connect(t1);
      log('connected (streamable HTTP) ->', url.href);
      return { client, transport: t1 };
    } catch (e1) {
      lastErr = e1;
      try {
        const client2 = new Client({ name: 'renoise-bridge', version: BRIDGE_VERSION });
        if (process.env.RENOISE_BRIDGE_DEBUG === '1') {
          client2.onerror = (err) => log('upstream SSE client error:', err);
        }
        const t2 = new SSEClientTransport(url);
        await client2.connect(t2);
        log('connected (SSE fallback) ->', url.href);
        return { client: client2, transport: t2 };
      } catch (e2) {
        lastErr = e2;
      }
    }
    if (i === 0 || (i + 1) % 10 === 0) {
      log(
        `waiting for ReMCP (${i + 1}/${retries}):`,
        lastErr?.message || lastErr,
      );
    }
    await new Promise((r) => setTimeout(r, delayMs));
  }
  log('giving up. Start Renoise + ReMCP (Tools -> Renoise MCP -> Start Server) first.');
  log('last error:', lastErr?.message || lastErr);
  process.exit(1);
}

async function main() {
  const url = targetUrl();
  log('target', url.href);
  const { client: upstream } = await connectUpstream(url);
  _cachedUpstreamUrl = url.href;
  await refreshToolCache(upstream);
  startDashboard();

  const server = new Server(
    { name: 'renoise-mcp-bridge', version: BRIDGE_VERSION },
    { capabilities: { tools: {} } },
  );

  server.setRequestHandler(ListToolsRequestSchema, async (request) => {
    return upstream.listTools(request.params ?? {});
  });

  server.setRequestHandler(CallToolRequestSchema, async (request) => {
    return upstream.callTool(request.params);
  });

  const stdio = new StdioServerTransport();
  await server.connect(stdio);
}

main().catch((e) => {
  log('fatal:', e);
  process.exit(1);
});
