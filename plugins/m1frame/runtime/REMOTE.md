# Remote m1frame: any AI, any device

Run m1frame once on a machine that stays on, give it an HTTPS address, and every AI app
you use connects to that same m1frame, with the same tools, wiki memory and run history,
from your laptop, phone or anywhere else.

```
 Claude (web/desktop/phone) ─┐
 ChatGPT (developer mode) ───┤  https://your-address/mcp   (OAuth sign-in, owner password)
 Cursor / VS Code / Gemini ──┤
                             ├──▶  m1frame remote  ──▶  BMAD · Council · OpenPlanter · Miras
 Open WebUI / Jan / n8n ─────┘  https://your-address/v1    (API key)        Karpathy · QA · Wiki
                                                              │
                                                              └─▶ the model in config.yaml
```

The AI app you're chatting in handles the conversation. m1frame does the pipeline work
on whichever model `config.yaml` names, so a phone chat can trigger a full council run.

## Raspberry Pi (one command)

A Pi 4 or 5 (2 GB+ RAM) with 64-bit Raspberry Pi OS makes a good always-on m1frame: low
power, and the heavy thinking happens at your model provider. On the Pi:

```bash
git clone https://github.com/ofFBeaT9/m1frame ~/m1frame
bash ~/m1frame/scripts/install_pi.sh
```

It asks for your AI provider and key (no key yet? answer "n" and add it later with `--set-key`) and an owner password, installs everything in a private
Python environment, gives the Pi a free public HTTPS address with Tailscale Funnel (you sign
in to Tailscale once in a browser link it prints), and runs m1frame as a service that starts
on boot. At the end it prints the URL to paste into Claude, ChatGPT and other apps
(step 5 below). Update later with `bash ~/m1frame/scripts/install_pi.sh --update`.

If Tailscale says Funnel isn't enabled, turn on **HTTPS** and **Funnel** in the Tailscale
admin console (the script prints the link) and run the script again.

The installer also runs **Studio**, the live view of every run, at `https://<your-pi>:8443`
(any username; the password is `M1FRAME_API_TOKEN` from `.env`). Runs started from Claude,
ChatGPT, `/v1` or Telegram show up there as they happen.

**Every module:** `bash ~/m1frame/scripts/install_pi.sh --full` adds Headroom, SkillOpt, vector search,
the scientific skills, Exa/Voyage clients and Sentrux (Rust), and switches on full-pipeline mode for
every request. Use a Pi with 4 GB+ (a Pi 5 with 8 GB is ideal).

The steps below are the manual route for any other machine.

## 1. Choose where it runs

| Option | Cost | Notes |
|---|---|---|
| A Raspberry Pi or other computer at home that stays on | free | Your files and local models (Ollama) stay at home. It's offline when the computer sleeps. |
| A small cloud server (VPS) | ~$5/month | Always on. Use a cloud model backend (Claude, OpenAI, OpenRouter). |

## 2. Configure

```bash
git clone https://github.com/ofFBeaT9/m1frame && cd m1frame
cp .env.example .env
```

In `.env` set:

- a model key (e.g. `ANTHROPIC_API_KEY` or `OPENROUTER_API_KEY`) and the backend, either as `M1FRAME_BACKEND=openrouter` in `.env` (keeps `config.yaml` untouched for updates) or `backend:` in `config.yaml`. `M1FRAME_MODEL` optionally picks the model;
- `M1FRAME_OWNER_PASSWORD`: 12+ characters. You type this on m1frame's sign-in page each time you connect a new app;
- `M1FRAME_API_TOKEN`: a long random string for chat apps that use `/v1` (e.g. `python -c "import secrets;print(secrets.token_urlsafe(32))"`).

## 3. Give it an HTTPS address

Pick one. Then set `M1FRAME_PUBLIC_URL` in `.env` to that address (no trailing slash).

**Tailscale Funnel (easiest, no domain needed).** Install Tailscale on the machine, then
`tailscale funnel --bg 8765`. Your address is `https://<machine>.<tailnet>.ts.net`.

**Cloudflare Tunnel (your own domain).** Create a named tunnel in the Cloudflare dashboard,
route a hostname (e.g. `m1frame.yourdomain.com`) to `http://m1frame-remote:8765`, and put
the tunnel token in `.env` as `CLOUDFLARE_TUNNEL_TOKEN`. Start with `--profile tunnel` below.

**Just trying it:** `cloudflared tunnel --url http://localhost:8765` prints a temporary
`https://….trycloudflare.com` address. It changes each time cloudflared restarts.

**VPS with a domain:** point DNS at the server and put Caddy in front
(`reverse_proxy localhost:8765`), which gets HTTPS certificates automatically.

## 4. Start

```bash
docker compose --profile remote up -d --build                    # m1frame remote on :8765
docker compose --profile remote --profile tunnel up -d --build   # plus the Cloudflare tunnel
```

Without Docker: `pip install -r requirements.txt && python -m remote` (reads the same
environment variables). Check `https://your-address/health`.

## 5. Connect your AI apps

Use `https://your-address/mcp` for every MCP app. When an app connects, m1frame's sign-in page
opens: check the app name and where it will send you back, enter the owner password, and choose **Allow**.

| App | Where |
|---|---|
| Claude (web, desktop, mobile) | Settings → Connectors → Add custom connector → paste the `/mcp` URL |
| ChatGPT (Plus/Pro) | Settings → Connectors → Advanced → Developer mode → create a connector with the `/mcp` URL, OAuth |
| Claude Code | `claude mcp add --transport http m1frame https://your-address/mcp` |
| Cursor, VS Code, Gemini CLI, other MCP clients | add a remote/HTTP MCP server with the `/mcp` URL |
| Open WebUI, Jan, LibreChat, n8n, the `openai` SDK | base URL `https://your-address/v1`, API key = `M1FRAME_API_TOKEN`, model `m1frame`, `m1frame-full` or `m1frame-chat` |

Then just ask, e.g. *"Use m1frame to design the backend for my app"*. The host receives
m1frame's routing instructions when it connects, so it knows when to recall the wiki, call
tools or run the pipeline.

## Tools a connected app gets

| Tool | Use |
|---|---|
| `m1frame_run` | Full 7-pillar pipeline, waits for the result |
| `m1frame_start` → `m1frame_result` | Same, in the background: returns a job id at once. Use when the app might time out (pipelines can take minutes) |
| `m1frame_agent` | Hand the whole prompt to m1frame's own agent; it decides |
| `m1frame_ask` | Recall what earlier runs concluded (offline, cited) |
| `m1frame_context`, `m1frame_list_tools`, `m1frame_list_skills`, `m1frame_call_tool` | Inventory and individual tools |
| `m1frame_scan_architecture`, `m1frame_optimize_skill` | Sensors and skill optimisation |

Studio (the live UI) stays a separate local service (`docker compose up m1frame`, port 8080).

## Security

- Anyone can *start* connecting, but no app gets access until you enter the owner password.
  The login page names the app and its return address so you can spot anything you didn't start.
- Wrong passwords: 8 per address and 32 in total trigger a 15-minute lockout.
- Tokens are stored hashed (`runs/remote_auth.json`), last a day, and refresh silently for 60 days.
- Sign every app out: `docker compose exec m1frame-remote python -m remote --revoke-all`
  (or change the password and revoke).
- Restrict which apps can register: `M1FRAME_ALLOWED_REDIRECT_HOSTS=claude.ai,claude.com,chatgpt.com`.
- File writes through `m1frame_call_tool` need `approve=true`, which the app will ask you about.
  `m1frame_agent` and `/v1` never write files.
- Every pipeline run spends your model credits. Keep the password strong and private.
- The service binds to `127.0.0.1:8765` on the host; only your tunnel or proxy exposes it.

## Troubleshooting

| Symptom | Fix |
|---|---|
| App says it can't connect | Open `https://your-address/health`. Check `M1FRAME_PUBLIC_URL` exactly matches the address you use. |
| Sign-in page says the link expired | Start connecting again from the app (links last 10 minutes). |
| "Too many attempts" | Wait 15 minutes. |
| Long runs time out in the app | Ask it to use `m1frame_start` and `m1frame_result`. |
| Runs fail with a key error | Set the backend in `config.yaml` and its key in `.env`, then restart. |
