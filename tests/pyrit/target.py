"""PyRIT target that speaks to the DocSummarizer /chat endpoint.

This is the custom target class the build spec (section 5) asks for. It lets
PyRIT's own orchestrators (CrescendoAttack, RedTeamingAttack, and the rest)
drive a conversation against the lab target the same way they would drive one
against a hosted model.

PyRIT is NOT installed in this repo's venv (its dependency tree conflicts with
the pinned requirements.txt, exactly like garak). It goes in its own
environment; see tests/pyrit/README.md. Because of that this module is written
against the pyrit 1.0.x API and is run from the PyRIT venv, not
by the app's test run. The reproducible measurement instrument for P1-02 is
tests/pyrit/crescendo.py, which does not import pyrit; this class is the "the
tool was actually wired up" deliverable.

Design notes
------------
* /chat keeps conversation state server-side (a module-level list cleared by
  /reset). PyRIT also tracks the conversation in its own memory. To keep the
  two in step the target sends only the latest user turn to /chat with
  use_history=true and calls /reset when it sees a new conversation_id. Do the
  reset between orchestrations, never between turns.
* The app's mechanical signals (violations, raw_violations, blocked, the
  safeguards block) are attached to the response message metadata so a PyRIT
  scorer can read them instead of re-deriving them from text.
"""

from __future__ import annotations

import json
import os
from typing import Any

import httpx

try:
    from pyrit.models import (
        Message,
        MessagePiece,
        PromptDataType,
    )
    from pyrit.models import construct_response_from_request
    from pyrit.prompt_target import PromptTarget
    from pyrit.prompt_target.common.target_capabilities import TargetCapabilities
    from pyrit.prompt_target.common.target_configuration import TargetConfiguration
except ImportError as exc:  # pragma: no cover - pyrit not in this venv
    raise ImportError(
        "tests/pyrit/target.py needs pyrit. Install it in its own environment:\n"
        "  python3 -m venv ~/venvs/pyrit && ~/venvs/pyrit/bin/pip install -r tests/pyrit/requirements.txt\n"
        "See tests/pyrit/README.md."
    ) from exc


DEFAULT_BASE_URL = os.getenv("DOCSUMMARIZER_URL", "http://127.0.0.1:8000")


class DocSummarizerTarget(PromptTarget):
    """A multi-turn PyRIT target for POST /chat.

    Parameters
    ----------
    base_url:
        Where the FastAPI target is listening. Defaults to $DOCSUMMARIZER_URL or
        http://127.0.0.1:8000.
    is_summary_request:
        The value sent in the /chat body's is_summary_request field for every
        turn this target sends. For a jailbreak orchestration leave it False so
        the app's V2 check stays meaningful. Set per-instance if a run needs the
        benign framing.
    rate_run:
        Sent as rate_run in the /chat body. True selects temperature 0.7 / seed
        unset on the app side (the rate measurement); False is the canonical
        temperature 0 / seed 42.
    reset_on_new_conversation:
        Call POST /reset the first time a given conversation_id is seen. Keeps
        the server-side history aligned with PyRIT's memory. Leave True.
    """

    # Multi-turn, editable history, system prompt supported: CrescendoAttack
    # requires editable history on its objective target.
    _DEFAULT_CONFIGURATION = TargetConfiguration(
        capabilities=TargetCapabilities(
            supports_multi_turn=True,
            supports_multi_message_pieces=False,
            supports_system_prompt=True,
            supports_editable_history=True,
        )
    )

    def __init__(
        self,
        *,
        base_url: str = DEFAULT_BASE_URL,
        is_summary_request: bool = False,
        rate_run: bool = False,
        reset_on_new_conversation: bool = True,
        timeout: float = 300.0,
        max_requests_per_minute: int | None = None,
    ) -> None:
        super().__init__(
            endpoint=f"{base_url.rstrip('/')}/chat",
            model_name="docsummarizer",
            max_requests_per_minute=max_requests_per_minute,
        )
        self._base_url = base_url.rstrip("/")
        self._is_summary_request = is_summary_request
        self._rate_run = rate_run
        self._reset_on_new_conversation = reset_on_new_conversation
        self._timeout = timeout
        self._client = httpx.Client(timeout=timeout)
        self._seen_conversations: set[str] = set()

    # -- required hook ---------------------------------------------------------

    async def _send_prompt_to_target_async(
        self, *, normalized_conversation: list["Message"]
    ) -> list["Message"]:
        request_message = normalized_conversation[-1]
        piece = request_message.message_pieces[0]
        conversation_id = piece.conversation_id
        user_text = piece.converted_value

        if self._reset_on_new_conversation and conversation_id not in self._seen_conversations:
            self._reset()
            self._seen_conversations.add(conversation_id)

        body = {
            "message": user_text,
            "is_summary_request": self._is_summary_request,
            "use_history": True,
            "rate_run": self._rate_run,
        }
        resp = self._client.post(f"{self._base_url}/chat", json=body)
        resp.raise_for_status()
        data = resp.json()

        answer = data.get("content", "")
        # construct_response_from_request takes the request MessagePiece (not the
        # Message) and merges prompt_metadata at construction. Metadata values
        # must be str/int, so the app's list/dict signals are JSON-encoded; a
        # scorer json.loads() them back.
        response = construct_response_from_request(
            request=piece,
            response_text_pieces=[answer],
            prompt_metadata={
                "violations": json.dumps(data.get("violations", [])),
                "raw_violations": json.dumps(data.get("raw_violations", [])),
                "raw_content": data.get("raw_content", ""),
                "blocked": int(bool(data.get("blocked", False))),
                "safeguards": json.dumps(data.get("safeguards", {})),
                "mode": data.get("mode", ""),
                "turn_count": data.get("turn_count") or 0,
            },
        )
        return [response]

    # -- helpers -------------------------------------------------------------

    def _reset(self) -> None:
        try:
            self._client.post(f"{self._base_url}/reset")
        except httpx.HTTPError:
            pass

    def _validate_request(self, *, normalized_conversation: list["Message"]) -> None:
        last = normalized_conversation[-1]
        if len(last.message_pieces) != 1:
            raise ValueError("DocSummarizerTarget sends one text piece per turn.")
        dtype = last.message_pieces[0].converted_value_data_type
        if dtype != "text":
            raise ValueError(f"DocSummarizerTarget is text only, got {dtype!r}.")

    def health(self) -> dict[str, Any]:
        return self._client.get(f"{self._base_url}/healthz").json()

    def __del__(self) -> None:  # pragma: no cover
        try:
            self._client.close()
        except Exception:
            pass
