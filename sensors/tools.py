"""
sensors/tools.py — expose the architectural sensor on m1frame's tool surface.

Registered into the default registry by tools.builtin.register_builtins(), so agents,
`GET /tools` and the MCP server all see these alongside the built-ins.

`sentrux_gate` with `save=True` writes a `.sentrux/` baseline into the repo, so the
tool is marked `dangerous` — `POST /tools/call` 403s it without `approve: true`,
exactly like `write_file`.
"""
from __future__ import annotations

from .gate import StructuralGate
from .sentrux import DEFAULT_TIMEOUT, SentruxClient

# One config read, shared by every surface. Previously the HTTP route read
# config.yaml while the ToolRegistry and MCP surfaces used hardcoded defaults, so
# `sensors.enforce: true` was silently ignored on two of three entry points. A
# safety-relevant flag honoured in only one place is a bug, not a nuance.


def sensor_config() -> dict:
    """`sensors:` from config.yaml, with safe defaults. Never raises."""
    defaults = {"enabled": True, "binary": None, "timeout": DEFAULT_TIMEOUT,
                "pass_threshold": 7.0, "concern_threshold": 5.0, "enforce": False}
    try:
        from llm_client import load_config
        cfg = (load_config() or {}).get("sensors") or {}
    except Exception:      # noqa: BLE001 — config problems must not disable the sensor
        cfg = {}
    return {**defaults, **{k: v for k, v in cfg.items() if k in defaults}}


def client(timeout: int | None = None) -> SentruxClient:
    """A config-honouring SentruxClient — the single constructor all surfaces use."""
    c = sensor_config()
    return SentruxClient(binary=c["binary"],
                         timeout=int(timeout if timeout is not None else c["timeout"]))


def gate(enforce: bool | None = None) -> StructuralGate:
    """A config-honouring StructuralGate — the single constructor all surfaces use."""
    c = sensor_config()
    return StructuralGate(float(c["pass_threshold"]), float(c["concern_threshold"]),
                          enforce=bool(c["enforce"] if enforce is None else enforce))


def sentrux_available() -> dict:
    """Is a Sentrux binary installed, which one, and where?"""
    c = client()
    argv = c.resolve()
    return {"available": argv is not None, "binary": argv[0] if argv else None,
            "flavour": c.flavour(), "mcp_command": c.mcp_command(),
            "install": "pip install sentrux"}


def sentrux_scan(path: str = ".", timeout: int | None = None) -> dict:
    """Headless structural measurement of a directory inside the workspace."""
    return client(timeout).scan(path).to_dict()


def sentrux_check(path: str = ".", timeout: int | None = None) -> dict:
    """Validate .sentrux/rules.toml architectural constraints."""
    return client(timeout).check(path).to_dict()


def sentrux_gate(path: str = ".", save: bool = False,
                 timeout: int | None = None) -> dict:
    """Compare against the saved baseline (save=True writes one — dangerous)."""
    return client(timeout).gate(path, save=bool(save)).to_dict()


def structural_verdict(path: str = ".", council_score: float | None = None,
                       enforce: bool | None = None) -> dict:
    """Measure, then fuse with a council score into one QA verdict.

    `enforce=None` means "use config"; pass True/False to override per call.
    """
    result = client().scan(path)
    return {"verdict": gate(enforce).fuse(council_score, result).to_dict(),
            "sensor": result.to_dict()}


def register_sensor_tools(reg):
    """Register the sensor tools into a ToolRegistry."""
    from tools.registry import Tool
    reg.register(Tool("sentrux_available", "Check whether the Sentrux binary is installed.",
                      sentrux_available, {}))
    reg.register(Tool("sentrux_scan", "Architectural scan of a path (0-10000 quality signal).",
                      sentrux_scan, {"path": "string (optional)", "timeout": "int (optional)"}))
    reg.register(Tool("sentrux_check", "Validate .sentrux/rules.toml constraints.",
                      sentrux_check, {"path": "string (optional)", "timeout": "int (optional)"}))
    reg.register(Tool("sentrux_gate", "Compare structure against a saved baseline.",
                      sentrux_gate, {"path": "string (optional)", "save": "bool (writes baseline)",
                                     "timeout": "int (optional)"}, dangerous=True))
    reg.register(Tool("structural_verdict", "Fuse a structural measurement with a council score.",
                      structural_verdict, {"path": "string (optional)",
                                           "council_score": "number (optional)",
                                           "enforce": "bool (optional)"}))
    return reg
