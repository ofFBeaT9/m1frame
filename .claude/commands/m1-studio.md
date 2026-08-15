---
description: Launch the m1frame Studio UI (real-time deliberation theatre)
---

Start the m1frame Studio and open it for the user.

1. Launch the server in the background: `python api/server.py` (honours `$PORT`, default 8080).
   - No API key? It serves in demo mode automatically. For live runs, set a key or use `backend: claudecli`.
2. Tell the user the URL: **http://localhost:8080**.
3. If a preview/browser tool is available, open it and show the Studio.

The Studio has seven surfaces: live **Studio** deliberation, grounded **Chat**, the knowledge **Graph**,
replayable **Runs**, learned **Skills**, the **Wiki**, and **Settings** (backend switch, 47 tools, gateways,
model registry).
