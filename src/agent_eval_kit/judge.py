from __future__ import annotations

import json
import re

from .client import OpenAICompatibleClient
from .models import TestCase


class LLMJudge:
    def __init__(self, client: OpenAICompatibleClient, model: str):
        self.client = client
        self.model = model

    def __call__(self, case: TestCase, response: str) -> tuple[float, str]:
        assert case.expect.judge is not None
        prompt = f"""Evaluate an AI response against the criterion below.
Return ONLY JSON with keys `score` (number from 0 to 1) and `reason` (short string).

Criterion:
{case.expect.judge.criteria}

User prompt:
{case.prompt}

Context:
{case.context or '(none)'}

AI response:
{response}
"""
        result = self.client.chat(
            model=self.model,
            prompt=prompt,
            system="You are a strict evaluation judge. Follow the requested JSON output format.",
        )
        text = result.content.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
            text = re.sub(r"\s*```$", "", text)
        data = json.loads(text)
        score = float(data["score"])
        if not 0 <= score <= 1:
            raise ValueError("Judge score must be between 0 and 1.")
        return score, str(data.get("reason", ""))
