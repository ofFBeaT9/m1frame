"""
sensors/sentrux.py — adapter for the Sentrux architectural analyser.

Sentrux is a standalone Rust binary (MIT). We shell out to it, parse its JSON, and
hand back a typed result. Three rules govern everything here:

1. **It never raises into a run.** A missing binary, a crash, a timeout, garbage on
   stdout — all become a `SensorResult` with `ok=False`. m1frame's runs are guarded
   the same way its gateways and skill loop are: a sensor can inform a run, never
   kill one.
2. **It never touches a shell.** Arguments are passed as a list with `shell=False`,
   so a path can't smuggle in a command.
3. **It never leaves the workspace.** Paths are resolved and jailed to the repo root
   *before* a subprocess is spawned, reusing the same contract as tools/builtin.py.

Resolution order for the binary: explicit `binary=` argument → `$SENTRUX_BIN` →
`PATH`. Deliberately no config lookup — `sensors/` stays free of m1frame's config
layer so the dependency arrow points one way (config → tools → sensors, never back).
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent   # sensors are jailed to the workspace
_MAX_RAW = 20_000                                # cap stdout kept in memory / returned by the API
DEFAULT_TIMEOUT = 60                             # a full-repo scan is bounded, not open-ended

# Two different tools answer to the name `sentrux`, and they are NOT the same project:
#
#   "rust"   github.com/sentrux/sentrux — the project this adapter targets. A Rust
#            binary. Its `scan` subcommand OPENS A GUI, so we must never call it
#            headlessly; `check`/`gate` are the CI-safe commands and print a
#            `Quality: NNNN` line. Structured data comes from `sentrux mcp`.
#   "python" PyPI `sentrux` — a pure-Python package with no project URLs that is
#            not published by the Rust project. Its `scan --json` emits
#            {"quality_score": {"overall_score": N}}.
#
# We detect which one is on PATH and drive it correctly, rather than assuming.
FLAVOUR_RUST, FLAVOUR_PYTHON, FLAVOUR_UNKNOWN = "rust", "python", "unknown"

# `check` and `gate --save` print a single number (`Quality: 7342`), but the `gate`
# comparison prints both sides: `Quality:      6891 -> 7342` (before -> after — see
# print_gate_results in sentrux-bin/src/main_impl.rs). Taking the first number there
# would report the PRE-session score and silently miss the regression the gate exists
# to catch, so the post-arrow value wins whenever there is one.
_QUALITY_LINE = re.compile(r"Quality:\s*(\d+)(?:\s*->\s*(\d+))?")


MAX_TIMEOUT = 600        # hard ceiling: a caller-supplied timeout can't pin a worker


def _safe_path(path: str | None) -> Path:
    """Resolve `path` inside the workspace, or raise. Mirrors tools.builtin._safe_path."""
    raw = str(path or ".")
    if "\x00" in raw:    # rejected here, not left to subprocess's own argv guard
        raise ValueError("path contains a null byte")
    p = (_ROOT / raw).resolve()
    if p != _ROOT and _ROOT not in p.parents:
        raise ValueError(f"path escapes workspace: {path}")
    return p


def _clamp_timeout(value) -> int:
    try:
        t = int(value)
    except Exception:    # noqa: BLE001
        return DEFAULT_TIMEOUT
    return max(1, min(MAX_TIMEOUT, t))


def _scrub_argv(argv: list[str]) -> list[str]:
    """Basenames for the binary, workspace-relative for paths — no absolute paths out."""
    out = []
    for i, a in enumerate(argv or []):
        s = str(a)
        try:
            p = Path(s)
            if i == 0 or p.is_absolute():
                if p.is_absolute() and (_ROOT == p or _ROOT in p.parents):
                    s = str(p.relative_to(_ROOT)).replace("\\", "/") or "."
                else:
                    s = p.name
        except Exception:      # noqa: BLE001
            pass
        out.append(s)
    return out


def _truncate(text: str) -> tuple[str, bool]:
    text = text or ""
    return (text[:_MAX_RAW], True) if len(text) > _MAX_RAW else (text, False)


@dataclass(frozen=True)
class SensorResult:
    """The outcome of one sensor invocation. Always returned; never thrown."""
    sensor: str = "sentrux"
    command: list[str] = field(default_factory=list)
    available: bool = False          # was the sensor binary found at all?
    ok: bool = False                 # did it run and exit 0?
    exit_code: int | None = None
    data: dict = field(default_factory=dict)     # parsed JSON, {} if stdout wasn't JSON
    raw: str = ""                                # stdout (truncated to _MAX_RAW)
    truncated: bool = False
    error: str = ""
    duration_ms: int = 0

    def to_dict(self) -> dict:
        """JSON-serialisable view — what the API and tool layer return.

        `command` is scrubbed of absolute paths: the resolved binary lives under a
        user profile directory, so echoing it verbatim leaks the OS username to
        every caller of the HTTP API.
        """
        return {"sensor": self.sensor, "command": _scrub_argv(self.command),
                "available": self.available, "ok": self.ok, "exit_code": self.exit_code,
                "data": self.data, "raw": self.raw, "truncated": self.truncated,
                "error": self.error, "duration_ms": self.duration_ms}

    @property
    def quality_signal(self) -> int | None:
        """The 0–10000 structural score, whichever shape the tool reported it in.

        Four known encodings, checked in order. All verified against the tools'
        own source rather than assumed:
          1. `quality_signal`                    — sentrux MCP (mcp_server/handlers.rs)
          2. `quality_score.overall_score`       — PyPI `sentrux` JSON
          3. `Quality: NNNN`                     — Rust `check` / `gate --save`
          4. `Quality:  BBBB -> AAAA`            — Rust `gate` comparison; the
             AFTER value is the current state and the one that matters.
        """
        v = self.data.get("quality_signal")
        if isinstance(v, int | float):
            return int(v)
        qs = self.data.get("quality_score")
        if isinstance(qs, dict) and isinstance(qs.get("overall_score"), int | float):
            return int(qs["overall_score"])
        m = _QUALITY_LINE.search(self.raw or "")
        if not m:
            return None
        return int(m.group(2) or m.group(1))     # `before -> after`: after wins


class SentruxClient:
    """Locate and drive the `sentrux` binary. Degrades to `available=False`, silently."""

    def __init__(self, binary: str | list[str] | None = None,
                 timeout: int = DEFAULT_TIMEOUT) -> None:
        self._binary = binary
        self.timeout = _clamp_timeout(timeout)
        self._flavour: str | None = None

    # ── discovery ───────────────────────────────────────────────────────────

    def resolve(self) -> list[str] | None:
        """The argv prefix that invokes Sentrux, or None if it isn't installed."""
        if isinstance(self._binary, list) and self._binary:
            return list(self._binary)
        if isinstance(self._binary, str) and self._binary.strip():
            found = shutil.which(self._binary) or (
                self._binary if Path(self._binary).exists() else None)
            return [found] if found else None
        env = os.environ.get("SENTRUX_BIN", "").strip()
        if env:
            found = shutil.which(env) or (env if Path(env).exists() else None)
            if found:
                return [found]
        found = shutil.which("sentrux")
        if found:
            return [found]
        # `pip install --user` puts console scripts in a directory that is NOT on
        # PATH by default on Windows — the ordinary outcome of `pip install sentrux`.
        # Reporting an installed tool as missing because of that is a bad answer,
        # so check the interpreter's own script directories too.
        import sysconfig
        schemes = ["nt_user", "posix_user"] if os.name == "nt" else ["posix_user"]
        for scheme in schemes:
            try:
                base = sysconfig.get_path("scripts", scheme=scheme)
            except Exception:      # noqa: BLE001 — scheme absent on this platform
                continue
            if base:
                for cand in (Path(base)/"sentrux.exe", Path(base)/"sentrux"):
                    if cand.exists():
                        return [str(cand)]
        base = sysconfig.get_path("scripts")
        if base:
            for cand in (Path(base)/"sentrux.exe", Path(base)/"sentrux"):
                if cand.exists():
                    return [str(cand)]
        return None

    def available(self) -> bool:
        return self.resolve() is not None

    # ── invocation ──────────────────────────────────────────────────────────

    def _run(self, args: list[str]) -> SensorResult:
        argv_prefix = self.resolve()
        if argv_prefix is None:
            return SensorResult(
                command=list(args), available=False, ok=False,
                error="sentrux not found. This adapter targets the Rust project "
                      "(github.com/sentrux/sentrux) — install it via Homebrew, its "
                      "install.sh, or a GitHub release binary, then set $SENTRUX_BIN "
                      "if it is not on PATH. Note that `pip install sentrux` fetches "
                      "a DIFFERENT project that merely shares the name.")
        argv = argv_prefix + list(args)
        started = time.perf_counter()
        try:
            proc = subprocess.run(                      # noqa: S603 — list argv, shell=False
                argv, shell=False, capture_output=True, text=True,
                timeout=self.timeout, cwd=str(_ROOT), check=False)
        except subprocess.TimeoutExpired:
            return SensorResult(command=argv, available=True, ok=False,
                                error=f"sentrux timed out after {self.timeout}s",
                                duration_ms=int((time.perf_counter() - started) * 1000))
        except Exception as e:                          # noqa: BLE001 — never raise into a run
            return SensorResult(command=argv, available=True, ok=False,
                                error=f"sentrux failed to start: {e}",
                                duration_ms=int((time.perf_counter() - started) * 1000))

        elapsed = int((time.perf_counter() - started) * 1000)
        raw, truncated = _truncate(proc.stdout)
        data: dict = {}
        try:                                            # stdout may legitimately not be JSON
            parsed = json.loads(proc.stdout)
            if isinstance(parsed, dict):
                data = parsed
        except Exception:                               # noqa: BLE001
            data = {}
        err, _ = _truncate(proc.stderr)
        return SensorResult(command=argv, available=True, ok=(proc.returncode == 0),
                            exit_code=proc.returncode, data=data, raw=raw,
                            truncated=truncated,
                            error="" if proc.returncode == 0 else err.strip(),
                            duration_ms=elapsed)

    # ── the Sentrux surface we use ──────────────────────────────────────────

    def version(self) -> SensorResult:
        return self._run(["--version"])

    def flavour(self) -> str:
        """Which `sentrux` is installed. Cached; costs one `scan --help` invocation.

        Discriminator: only the PyPI package's `scan` accepts `--json`. The Rust
        project's `scan` takes a bare path and opens a GUI.
        """
        if self._flavour is not None:
            return self._flavour
        if not self.available():
            self._flavour = FLAVOUR_UNKNOWN
            return self._flavour
        probe = self._run(["scan", "--help"])
        text = f"{probe.raw}\n{probe.error}"
        self._flavour = FLAVOUR_PYTHON if "--json" in text else (
            FLAVOUR_RUST if probe.available else FLAVOUR_UNKNOWN)
        return self._flavour

    def scan(self, path: str = ".") -> SensorResult:
        """Structural measurement of `path`, headless and CI-safe.

        Never invokes the Rust project's `scan` subcommand: that opens a GUI and
        would hang here until the timeout. For that flavour we use `check`, which
        is the CI-safe command and prints the same `Quality: NNNN` signal.

        KNOWN LIMIT, measured against the real Rust binary (v0.5.7): `check` refuses
        to run unless `<path>/.sentrux/rules.toml` exists — it prints "No
        .sentrux/rules.toml found" on stderr, exits 1, and emits no Quality line at
        all. So on the Rust flavour this returns no signal in any repo that has not
        been set up for sentrux, which is most of them. The tool's intended headless
        agent interface is the MCP server (`sentrux mcp`, see `mcp_command`), whose
        `scan` tool returns `quality_signal` with no config and no side effects;
        wiring m1frame to it is the real fix and is tracked as such. Meanwhile the
        stderr reason is carried through to the gate's `reasons` rather than being
        swallowed, so the sensor's silence is at least explained.
        """
        target = str(_safe_path(path))
        if self.flavour() == FLAVOUR_PYTHON:
            return self._run(["scan", target, "--json"])
        return self._run(["check", target])

    def mcp_command(self) -> list[str] | None:
        """argv for `sentrux mcp` — the Rust project's structured agent interface.

        m1frame's MCP client (tools/mcp_client.py) is the seam that would consume
        this. Returned, not launched: starting a long-lived server is the caller's
        decision, not a side effect of asking a sensor a question.
        """
        argv = self.resolve()
        return (argv + ["mcp"]) if argv else None

    def check(self, path: str = ".") -> SensorResult:
        """Validate `.sentrux/rules.toml` constraints (CI-friendly; non-zero exit on violation)."""
        return self._run(["check", str(_safe_path(path))])

    def gate(self, path: str = ".", save: bool = False) -> SensorResult:
        """Compare against the saved baseline, or write one when `save=True`.

        `save=True` writes a `.sentrux/` baseline into the repo, which is why the
        tool wrapper marks it dangerous and defaults it off.
        """
        target = str(_safe_path(path))
        return self._run(["gate", "--save", target] if save else ["gate", target])
