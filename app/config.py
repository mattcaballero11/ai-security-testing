"""Configuration and the baseline/hardened mode switch.

Everything that differs between the two modes is expressed as a boolean on the
Settings object so that main.py, safeguards.py, and prompts.py stay readable and
the diff between modes is one place, not scattered.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

REPO_ROOT = Path(__file__).resolve().parent.parent

# The one and only secret in this application. Synthetic. Do not replace with a
# real value. Referenced by prompts.py (goes into the system instruction) and
# safeguards.py (the output-side scan looks for it).
CANARY = "DEMO_SECRET_DO_NOT_USE"

VALID_MODES = ("baseline", "hardened")


def _git_commit() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if out.returncode == 0:
            return out.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return "unknown"


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    return float(raw)


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    return int(raw)


@dataclass(frozen=True)
class GenOptions:
    """The Ollama options block from section 3 of the build spec.

    Rate runs override temperature and seed per request; see ollama_client.py.
    """

    temperature: float = 0.0
    seed: int | None = 42
    top_p: float = 1.0
    num_ctx: int = 4096
    num_predict: int = 512

    def to_ollama(self, temperature: float | None = None, seed: int | None = ...) -> dict:
        # seed sentinel: ... means "use the configured default", None means "unset"
        resolved_seed = self.seed if seed is ... else seed
        opts: dict = {
            "temperature": self.temperature if temperature is None else temperature,
            "top_p": self.top_p,
            "num_ctx": self.num_ctx,
            "num_predict": self.num_predict,
        }
        if resolved_seed is not None:
            opts["seed"] = resolved_seed
        return opts


@dataclass(frozen=True)
class Settings:
    mode: str
    host: str
    port: int

    ollama_host: str
    ollama_model: str
    ollama_model_digest: str
    ollama_timeout: float
    gen: GenOptions

    max_input_chars: int
    rate_limit_requests: int
    rate_limit_window_seconds: int

    log_dir: Path
    git_commit: str = field(default_factory=_git_commit)

    # ----- mode-derived control flags -------------------------------------
    @property
    def is_hardened(self) -> bool:
        return self.mode == "hardened"

    @property
    def enforce_input_controls(self) -> bool:
        return self.is_hardened

    @property
    def use_data_channel(self) -> bool:
        return self.is_hardened

    @property
    def minimize_context(self) -> bool:
        return self.is_hardened

    @property
    def scan_output_for_canary(self) -> bool:
        return self.is_hardened

    @property
    def escape_render_output(self) -> bool:
        return self.is_hardened

    @property
    def enforce_rate_limit(self) -> bool:
        return self.is_hardened


@lru_cache
def get_settings() -> Settings:
    mode = os.getenv("APP_MODE", "baseline").strip().lower()
    if mode not in VALID_MODES:
        raise SystemExit(
            f"APP_MODE must be one of {VALID_MODES}, got {mode!r}. Check your .env."
        )

    log_dir = REPO_ROOT / os.getenv("LOG_DIR", "logs")
    log_dir.mkdir(parents=True, exist_ok=True)

    return Settings(
        mode=mode,
        host=os.getenv("APP_HOST", "127.0.0.1"),
        port=_env_int("APP_PORT", 8000),
        ollama_host=os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/"),
        ollama_model=os.getenv("OLLAMA_MODEL", "llama3.2:3b-instruct-q4_K_M"),
        ollama_model_digest=os.getenv("OLLAMA_MODEL_DIGEST", "").strip(),
        ollama_timeout=_env_float("OLLAMA_TIMEOUT", 120.0),
        gen=GenOptions(
            temperature=_env_float("GEN_TEMPERATURE", 0.0),
            seed=_env_int("GEN_SEED", 42),
            top_p=_env_float("GEN_TOP_P", 1.0),
            num_ctx=_env_int("GEN_NUM_CTX", 4096),
            num_predict=_env_int("GEN_NUM_PREDICT", 512),
        ),
        max_input_chars=_env_int("MAX_INPUT_CHARS", 6000),
        rate_limit_requests=_env_int("RATE_LIMIT_REQUESTS", 30),
        rate_limit_window_seconds=_env_int("RATE_LIMIT_WINDOW_SECONDS", 60),
        log_dir=log_dir,
    )
