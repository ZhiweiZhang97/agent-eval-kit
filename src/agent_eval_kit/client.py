from __future__ import annotations

import json
import random
import threading
import time
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from typing import Any

import httpx

from .models import ToolCall


@dataclass
class ChatResponse:
    content: str
    latency_ms: float
    raw: dict[str, Any]
    tool_calls: list[ToolCall]


def normalize_tool_calls(message: dict[str, Any]) -> list[ToolCall]:
    calls: list[ToolCall] = []
    for item in message.get("tool_calls") or []:
        function = item.get("function") or {}
        raw_args = function.get("arguments", {})
        arguments: Any = raw_args
        if isinstance(raw_args, str):
            try:
                arguments = json.loads(raw_args)
            except json.JSONDecodeError:
                arguments = raw_args
        calls.append(
            ToolCall(
                name=str(function.get("name", "")),
                arguments=arguments,
                id=str(item["id"]) if item.get("id") is not None else None,
            )
        )

    legacy = message.get("function_call")
    if legacy and not calls:
        raw_args = legacy.get("arguments", {})
        arguments = raw_args
        if isinstance(raw_args, str):
            try:
                arguments = json.loads(raw_args)
            except json.JSONDecodeError:
                arguments = raw_args
        calls.append(ToolCall(name=str(legacy.get("name", "")), arguments=arguments))
    return calls


def _retry_after_seconds(response: httpx.Response) -> float | None:
    value = response.headers.get("Retry-After")
    if not value:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        try:
            target = parsedate_to_datetime(value)
            now = parsedate_to_datetime(response.headers.get("Date", ""))
            return max(0.0, (target - now).total_seconds())
        except (TypeError, ValueError):
            return None


class OpenAICompatibleClient:
    def __init__(
        self,
        base_url: str,
        api_key: str | None = None,
        timeout: float = 60.0,
        retries: int = 2,
        min_interval_ms: float = 0.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.retries = max(0, retries)
        self.min_interval_ms = max(0.0, min_interval_ms)
        self._pace_lock = threading.Lock()
        self._last_request_started = 0.0

    def _pace(self) -> None:
        if self.min_interval_ms <= 0:
            return
        with self._pace_lock:
            now = time.monotonic()
            minimum = self.min_interval_ms / 1000
            remaining = minimum - (now - self._last_request_started)
            if remaining > 0:
                time.sleep(remaining)
            self._last_request_started = time.monotonic()

    def chat(
        self,
        model: str,
        prompt: str,
        system: str | None = None,
        context: str | None = None,
        temperature: float = 0.0,
        tools: list[dict[str, Any]] | None = None,
        tool_choice: Any = None,
    ) -> ChatResponse:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        user_content = prompt
        if context:
            user_content = f"Context:\n{context}\n\nQuestion:\n{prompt}"
        messages.append({"role": "user", "content": user_content})

        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }
        if tools:
            payload["tools"] = tools
        if tool_choice is not None:
            payload["tool_choice"] = tool_choice

        last_error: Exception | None = None
        started = time.perf_counter()

        for attempt in range(self.retries + 1):
            try:
                self._pace()
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.post(
                        f"{self.base_url}/chat/completions",
                        headers=headers,
                        json=payload,
                    )
                    response.raise_for_status()
                    data = response.json()
                message = data["choices"][0]["message"]
                latency_ms = (time.perf_counter() - started) * 1000
                return ChatResponse(
                    content=message.get("content") or "",
                    latency_ms=latency_ms,
                    raw=data,
                    tool_calls=normalize_tool_calls(message),
                )
            except (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError) as exc:
                last_error = exc
                retry_after = None
                retryable = True
                if isinstance(exc, httpx.HTTPStatusError):
                    retryable = exc.response.status_code in {
                        408,
                        409,
                        429,
                        500,
                        502,
                        503,
                        504,
                    }
                    retry_after = _retry_after_seconds(exc.response)
                if attempt >= self.retries or not retryable:
                    break

                fallback = (0.5 * (2**attempt)) + random.uniform(0, 0.2)
                time.sleep(retry_after if retry_after is not None else fallback)

        assert last_error is not None
        raise last_error
