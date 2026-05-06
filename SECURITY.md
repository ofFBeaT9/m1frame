# Security Policy

## Supported versions

| Version | Supported |
|---|---|
| 1.x.x | ✅ Yes |

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

1. **API keys** — stored in `.env`, never logged. Never commit `.env` to git.
2. **Wiki content** — saved as plain Markdown to disk. Sanitise inputs if deploying in a multi-user environment.
3. **Config** — `config.yaml` controls which backend and model is used. Restrict write access in production.
4. **LLM outputs** — m1frame does not sanitise LLM outputs before writing to wiki. Review wiki pages before sharing.
