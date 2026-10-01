# Security Policy

## Supported versions

| Version | Supported |
|---|---|
| 1.x.x | âœ… Yes |

## Reporting a vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

Email: security@m1frame.dev (or open a private GitHub Security Advisory).

Please include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

You will receive acknowledgement within 48 hours and a resolution timeline within 7 days.

## Scope

### In scope
- Prompt injection vulnerabilities in agent system prompts
- API key leakage via logs or error messages
- Dependency vulnerabilities in `requirements.txt`
- Arbitrary code execution via wiki ingest or config parsing

### Out of scope
- Issues in the upstream LLM providers (Anthropic, OpenAI, Ollama)
- Rate limiting or cost overruns from API usage
- Social engineering attacks

## Security model

m1frame passes your goals and outputs through LLM APIs. Be aware:

1. **API keys** â€” stored in `.env`, never logged. Never commit `.env` to git.
2. **Wiki content** â€” saved as plain Markdown to disk. Sanitise inputs if deploying in a multi-user environment.
3. **Config** â€” `config.yaml` controls which backend and model is used. Restrict write access in production.
4. **LLM outputs** â€” m1frame does not sanitise LLM outputs before writing to wiki. Review wiki pages before sharing.


## Local service boundary (v1.10.1)

Studio is a single-owner workspace service. Without `M1FRAME_API_TOKEN`, only
loopback requests addressed to localhost/127.0.0.1/::1 are accepted. Cross-origin
browser requests are rejected. With a token, clients supply `Authorization:
Bearer <token>`; browsers may use HTTP Basic authentication with any username
and the token as password. Use TLS at a trusted proxy for remote access. Docker
Compose binds its published port to loopback and requires the token. Gateway
webhooks also require this authentication; a trusted gateway proxy must inject it.

MCP HTTP binds to loopback only. Put an authenticated reverse proxy in front of
it for remote clients. The Studio API token does not authenticate the MCP service.
Stdio MCP inherits its host's permissions. Custom tool plugins are trusted Python
code; approval gating does not make them an operating-system sandbox.

Built-in file tools deny hidden paths and common credential filenames, including
Windows alternate data streams. This is a safeguard, not secret classification:
do not put secrets in ordinary workspace documents. Static demo servers expose
only the Studio HTML, demo fixture and generated dashboard (no arbitrary files).

Untrusted HTTP tool and webhook destinations are resolved once, checked for public
addresses, and connected using that same address. HTTPS retains hostname checks;
redirects and environment proxies are disabled. Network policy remains appropriate
for deployments with unusual routing. Regex execution uses a timeout; arithmetic,
file reads, request bodies and active runs have bounds.

The supplied service runs as one process. Multi-worker scheduling and adversarial
local filesystem races are outside this release's supported deployment model.
Prompt injection checks and council reviews are fallible and do not certify content.
