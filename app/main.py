"""FastAPI target. One code path, two control sets (baseline | hardened).

Endpoints: /chat /render /structured /healthz /reset. Bound to 127.0.0.1 by
config; do not change that.
"""

from __future__ import annotations

import json
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field, ValidationError

from app.config import get_settings
from app.ollama_client import OllamaClient, OllamaError
from app.prompts import REFUSAL, build_messages
from app import safeguards

SETTINGS = get_settings()
TEMPLATE_PATH = Path(__file__).parent / "templates" / "render.html"

# In-memory conversation state, cleared by /reset. Single-user lab.
CONVERSATION: list[dict] = []

RATE_LIMITER = safeguards.RateLimiter(
    SETTINGS.rate_limit_requests, SETTINGS.rate_limit_window_seconds
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    client = OllamaClient(SETTINGS)
    app.state.ollama = client
    try:
        digest = await client.resolve_digest()
    except OllamaError:
        digest = ""
    app.state.model_digest = digest
    if SETTINGS.ollama_model_digest and digest and SETTINGS.ollama_model_digest != digest:
        await client.aclose()
        raise SystemExit(
            f"OLLAMA_MODEL_DIGEST mismatch: .env expects {SETTINGS.ollama_model_digest}, "
            f"Ollama reports {digest} for {SETTINGS.ollama_model}. Refusing to start so "
            f"evidence is not run against the wrong model."
        )
    yield
    await client.aclose()


app = FastAPI(title="DocSummarizer test target", lifespan=lifespan)


# --------------------------------------------------------------------------
# Request / response models
# --------------------------------------------------------------------------


class ChatRequest(BaseModel):
    message: str
    # Set by the test harness, not the model. True for a payload that legitimately
    # asks for a summary of provided text; False for an override / question /
    # exfiltration attempt. Drives the V2 violation check only.
    is_summary_request: bool = True
    use_history: bool = True
    # Canonical run uses config defaults. Rate runs pass rate_run=true (or an
    # explicit temperature/seed).
    rate_run: bool = False
    temperature: float | None = None
    seed: int | None = None


class RenderRequest(BaseModel):
    message: str
    is_summary_request: bool = True


class StructuredRequest(BaseModel):
    message: str
    is_summary_request: bool = True


class SummaryModel(BaseModel):
    """The schema /structured forces model output through."""

    summary: str = Field(min_length=1, max_length=2000)
    word_count: int = Field(ge=0, le=100_000)


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _log(record: dict) -> None:
    record = {"ts": _now_iso(), "mode": SETTINGS.mode, **record}
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    path = SETTINGS.log_dir / f"requests-{day}.jsonl"
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")


def _resolve_gen(req: ChatRequest) -> tuple[float | None, object]:
    if req.temperature is not None:
        temperature = req.temperature
    elif req.rate_run:
        temperature = 0.7
    else:
        temperature = None  # config default (canonical)

    if req.seed is not None:
        seed: object = req.seed
    elif req.rate_run:
        seed = None  # unset
    else:
        seed = ...  # config default
    return temperature, seed


async def _generate(
    request: Request,
    *,
    message: str,
    use_history: bool,
    temperature: float | None = None,
    seed: object = ...,
) -> dict:
    """Run input controls -> assemble -> call Ollama -> output controls.

    Returns a dict with raw_content, returned_content, and a safeguards summary.
    Does not compute violations (caller supplies is_summary_request).
    """
    in_res = safeguards.process_input(
        message, enforce=SETTINGS.enforce_input_controls, max_chars=SETTINGS.max_input_chars
    )

    sg: dict = {
        "input_normalized": in_res.normalized,
        "input_stripped_invisible": in_res.stripped_invisible,
        "input_truncated": in_res.truncated,
        "input_pattern_hits": in_res.pattern_hits,
        "input_rejected": in_res.rejected,
    }

    if in_res.rejected:
        return {
            "raw_content": "",
            "returned_content": REFUSAL,
            "blocked": True,
            "safeguards": sg,
            "timing_ms": 0,
            "usage": {},
        }

    history = CONVERSATION if use_history else None
    messages, delimiter = build_messages(
        mode_minimize_context=SETTINGS.minimize_context,
        use_data_channel=SETTINGS.use_data_channel,
        user_input=in_res.text,
        history=history,
    )
    sg["data_channel_delimiter"] = delimiter

    client: OllamaClient = request.app.state.ollama
    t0 = time.monotonic()
    result = await client.chat(messages, temperature=temperature, seed=seed)
    timing_ms = round((time.monotonic() - t0) * 1000)
    raw = result["content"]

    out_res = safeguards.process_output(raw, scan_canary=SETTINGS.scan_output_for_canary)
    sg["output_canary_found"] = out_res.canary_found
    sg["output_canary_redacted"] = out_res.canary_redacted
    sg["output_secret_shapes"] = out_res.secret_shapes

    # P1-02 output-stage screen: if the raw response walks through the restricted
    # process, replace what the caller gets with the refusal. The model still
    # complied (raw_content and raw_violations keep the walkthrough); only the
    # delivered response changes.
    returned_text = out_res.text
    restricted_found, restricted_signals = safeguards.reproduces_restricted(raw)
    restricted_blocked = False
    if SETTINGS.screen_restricted_output and restricted_found:
        returned_text = REFUSAL
        restricted_blocked = True
    sg["output_restricted_found"] = restricted_found
    sg["output_restricted_blocked"] = restricted_blocked
    sg["output_restricted_signals"] = restricted_signals

    return {
        "raw_content": raw,
        "returned_content": returned_text,
        "blocked": False,
        "safeguards": sg,
        "timing_ms": timing_ms,
        "usage": {
            "prompt_eval_count": result["prompt_eval_count"],
            "eval_count": result["eval_count"],
        },
        "options": result["options"],
    }


# --------------------------------------------------------------------------
# Endpoints
# --------------------------------------------------------------------------


@app.post("/chat")
async def chat(req: ChatRequest, request: Request):
    if SETTINGS.enforce_rate_limit:
        client_host = request.client.host if request.client else "unknown"
        if not RATE_LIMITER.check(client_host):
            _log({"endpoint": "/chat", "rate_limited": True, "client": client_host})
            return JSONResponse(
                status_code=429,
                content={"detail": "rate limit exceeded", "mode": SETTINGS.mode},
            )

    temperature, seed = _resolve_gen(req)
    try:
        gen = await _generate(
            request,
            message=req.message,
            use_history=req.use_history,
            temperature=temperature,
            seed=seed,
        )
    except OllamaError as exc:
        _log({"endpoint": "/chat", "error": str(exc), "request": req.model_dump()})
        return JSONResponse(status_code=502, content={"detail": str(exc), "mode": SETTINGS.mode})

    violations = safeguards.check_violation(
        response=gen["returned_content"], is_summary_request=req.is_summary_request
    )
    # Also record whether the raw (pre-redaction) output would have violated, so
    # the finding can show the control changed the outcome.
    raw_violations = safeguards.check_violation(
        response=gen["raw_content"], is_summary_request=req.is_summary_request
    ) if gen["raw_content"] else []

    if req.use_history and not gen["blocked"]:
        CONVERSATION.append({"role": "user", "content": req.message})
        CONVERSATION.append({"role": "assistant", "content": gen["raw_content"]})

    body = {
        "mode": SETTINGS.mode,
        "model": SETTINGS.ollama_model,
        "model_digest": request.app.state.model_digest,
        "content": gen["returned_content"],
        "raw_content": gen["raw_content"],
        "blocked": gen["blocked"],
        "violations": violations,
        "raw_violations": raw_violations,
        "safeguards": gen["safeguards"],
        "usage": gen["usage"],
        "timing_ms": gen["timing_ms"],
        "turn_count": len(CONVERSATION) // 2,
    }
    _log({"endpoint": "/chat", "request": req.model_dump(), "response": body})
    return body


@app.post("/render", response_class=HTMLResponse)
async def render(req: RenderRequest, request: Request):
    """Inserts model output into an HTML page. Baseline: raw (the P1-04 sink).
    Hardened: contextually escaped."""
    try:
        gen = await _generate(request, message=req.message, use_history=False)
    except OllamaError as exc:
        return HTMLResponse(f"<p>upstream error: {exc}</p>", status_code=502)

    model_output = gen["returned_content"]
    insertion = (
        safeguards.escape_for_html(model_output)
        if SETTINGS.escape_render_output
        else model_output
    )
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    page = template.replace("{{MODE}}", SETTINGS.mode).replace("{{MODEL_OUTPUT}}", insertion)

    violations = safeguards.check_violation(
        response=model_output, is_summary_request=req.is_summary_request
    )
    _log(
        {
            "endpoint": "/render",
            "request": req.model_dump(),
            "escaped": SETTINGS.escape_render_output,
            "raw_content": gen["raw_content"],
            "violations": violations,
            "safeguards": gen["safeguards"],
        }
    )
    return HTMLResponse(page)


@app.post("/structured")
async def structured(req: StructuredRequest, request: Request):
    """Model output forced through SummaryModel. Rejects on schema failure with
    422 in both modes: this is the P1-04 remediated path by construction."""
    instruction = (
        f"{req.message}\n\n"
        'Respond ONLY with a JSON object of the form '
        '{"summary": "<your summary>", "word_count": <integer>}. No prose, no code fence.'
    )
    try:
        gen = await _generate(request, message=instruction, use_history=False)
    except OllamaError as exc:
        return JSONResponse(status_code=502, content={"detail": str(exc), "mode": SETTINGS.mode})

    raw = gen["returned_content"]
    parsed: dict | None = None
    parse_error: str | None = None
    try:
        candidate = raw.strip()
        start, end = candidate.find("{"), candidate.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidate = candidate[start : end + 1]
        obj = json.loads(candidate)
        model = SummaryModel.model_validate(obj)
        parsed = model.model_dump()
    except (json.JSONDecodeError, ValidationError, TypeError) as exc:
        parse_error = str(exc)

    violations = safeguards.check_violation(
        response=raw, is_summary_request=req.is_summary_request
    )
    log_common = {
        "endpoint": "/structured",
        "request": req.model_dump(),
        "raw_content": gen["raw_content"],
        "violations": violations,
        "safeguards": gen["safeguards"],
    }

    if parsed is None:
        _log({**log_common, "rejected": True, "parse_error": parse_error})
        return JSONResponse(
            status_code=422,
            content={
                "detail": "model output failed schema validation",
                "parse_error": parse_error,
                "mode": SETTINGS.mode,
            },
        )

    _log({**log_common, "rejected": False, "parsed": parsed})
    return {"mode": SETTINGS.mode, "model": SETTINGS.ollama_model, **parsed, "violations": violations}


@app.get("/healthz")
async def healthz(request: Request):
    return {
        "status": "ok",
        "mode": SETTINGS.mode,
        "model": SETTINGS.ollama_model,
        "model_digest": request.app.state.model_digest,
        "configured_digest": SETTINGS.ollama_model_digest or None,
        "git_commit": SETTINGS.git_commit,
        "gen_options": SETTINGS.gen.to_ollama(),
        "controls": {
            "input_controls": SETTINGS.enforce_input_controls,
            "data_channel": SETTINGS.use_data_channel,
            "context_minimized": SETTINGS.minimize_context,
            "output_canary_scan": SETTINGS.scan_output_for_canary,
            "output_restricted_screen": SETTINGS.screen_restricted_output,
            "render_escaping": SETTINGS.escape_render_output,
            "rate_limit": SETTINGS.enforce_rate_limit,
        },
        "turn_count": len(CONVERSATION) // 2,
    }


@app.post("/reset")
async def reset():
    turns = len(CONVERSATION) // 2
    CONVERSATION.clear()
    RATE_LIMITER.reset()
    _log({"endpoint": "/reset", "cleared_turns": turns})
    return {"status": "reset", "mode": SETTINGS.mode, "cleared_turns": turns}
