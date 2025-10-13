"""High-level orchestrator that turns decisions into persona-aligned responses."""

from __future__ import annotations

from typing import Any, Dict, Optional

from app.services.conversation.persona_middleware import PersonaMiddleware, persona_middleware
from app.services.conversation.response_templates import RenderResult, ResponseTemplates
from app.services.conversation.state_hydrator import ConversationStateSnapshot


class UnifiedResponseBuilder:
    """Compose final responses using shared templates and persona rules."""

    def __init__(self, persona: Optional[PersonaMiddleware] = None) -> None:
        self.persona = persona or persona_middleware
        self.templates = ResponseTemplates(self.persona)

    def build(
        self,
        *,
        intent: str,
        request: str,
        recommendation: Dict[str, Any],
        service_result: Dict[str, Any],
        state: ConversationStateSnapshot,
        ai_analysis: Optional[str] = None,
        interface: str = "chat",
        requires_approval: bool = False,
    ) -> RenderResult:
        return self.templates.render(
            intent=intent,
            request=request,
            recommendation=recommendation,
            service_result=service_result,
            state=state,
            ai_analysis=ai_analysis,
            interface=interface,
            requires_approval=requires_approval,
        )

    def clarify(
        self,
        *,
        request: str,
        intent_candidates: Dict[str, float],
        state: ConversationStateSnapshot,
    ) -> str:
        return self.templates.clarifying_question(
            request=request,
            intent_candidates=intent_candidates,
            state=state,
        )


unified_response_builder = UnifiedResponseBuilder()
