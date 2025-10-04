"""Persona enforcement utilities for the unified AI money manager."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional, Any
import re


@dataclass
class PersonaProfile:
    """Configuration for the enterprise advisor persona."""

    name: str = "Alex"
    title: str = "Senior Portfolio Manager"
    experience_years: int = 15
    voice_anchor: str = (
        "I keep your cross-exchange portfolio, credits, and risk posture synchronized in real time."
    )
    tone_guidelines: Dict[str, str] = field(
        default_factory=lambda: {
            "confidence": "Speak with measured confidence that reflects institutional experience.",
            "warmth": "Stay approachable and collaborative—sound like a trusted human advisor.",
            "transparency": "Acknowledge uncertainty or risk explicitly when relevant.",
        }
    )
    closing_prompt: str = "Let me know where you'd like me to focus next."
    signature: str = "—Alex"


class PersonaMiddleware:
    """Normalize responses so every interface hears the same advisor."""

    bullet_pattern = re.compile(r"^[\-\*•\u2022\u25AA\u25CF]+\s*")

    def __init__(self, profile: Optional[PersonaProfile] = None) -> None:
        self.profile = profile or PersonaProfile()

    def apply(
        self,
        content: str,
        *,
        state: Optional[Any] = None,
        intent: Optional[str] = None,
        include_intro: bool = False,
    ) -> str:
        """Apply persona tone and formatting safeguards to the outgoing message."""

        if not content:
            return content

        sanitized = self._sanitize_text(content)
        if not sanitized:
            return sanitized

        segments = []
        if include_intro:
            segments.append(self._build_intro(state))

        segments.append(sanitized)

        enriched = self._append_closing(" ".join(filter(None, segments)))
        return enriched.strip()

    def _sanitize_text(self, content: str) -> str:
        """Collapse multi-line templated output into conversational prose."""

        lines = [line.strip() for line in content.splitlines() if line.strip()]
        if not lines:
            return ""

        normalized_lines = []
        for line in lines:
            if self.bullet_pattern.match(line):
                line = self.bullet_pattern.sub("", line)
            # Strip lingering emojis commonly used as bullets
            line = re.sub(r"^[\u23FA-\u2BFF\u2600-\u27BF]+\s*", "", line)
            line = re.sub(r"\s{2,}", " ", line)
            normalized_lines.append(line.strip())

        # Keep short lists as sentences separated by spaces
        normalized = " ".join(normalized_lines)
        normalized = re.sub(r"\s([,.;])", r"\1", normalized)
        return normalized.strip()

    def _append_closing(self, message: str) -> str:
        """Ensure the closing reflects the persona voice and invitation."""

        message = message.rstrip()
        if not message.endswith(('.', '!', '?')):
            message = f"{message}."

        if self.profile.closing_prompt not in message:
            message = f"{message} {self.profile.closing_prompt}"

        if self.profile.signature not in message:
            if not message.endswith(('.', '!', '?')):
                message = f"{message}."
            message = f"{message} {self.profile.signature}"

        return re.sub(r"\s{2,}", " ", message).strip()

    def _build_intro(self, state: Optional[Any]) -> str:
        """Construct an optional intro line referencing current context."""

        intro = f"{self.profile.name} here—your {self.profile.title}."
        if state and getattr(state, "portfolio", None):
            total_value = state.portfolio.get("total_value") if isinstance(state.portfolio, dict) else None
            if total_value:
                intro += f" Your portfolio is synced at ${float(total_value):,.2f}."
        intro += f" {self.profile.voice_anchor}"
        return intro.strip()


# Global singleton to avoid re-instantiation across modules
persona_middleware = PersonaMiddleware()
