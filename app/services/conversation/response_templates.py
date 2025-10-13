"""Reusable natural-language templates for the unified AI advisor."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from app.services.conversation.persona_middleware import PersonaMiddleware, persona_middleware
from app.services.conversation.opportunity_ranker import rank_opportunities
from app.services.conversation.state_hydrator import ConversationStateSnapshot


@dataclass
class RenderResult:
    content: str
    metadata: Dict[str, Any]


class ResponseTemplates:
    """Craft consistent advisor responses independent of interface."""

    def __init__(self, persona: Optional[PersonaMiddleware] = None) -> None:
        self.persona = persona or persona_middleware

    def render(
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
        intent_lower = (intent or "").lower()

        if "portfolio" in intent_lower:
            message, meta = self._portfolio_response(state, service_result, recommendation)
        elif "strategy" in intent_lower:
            message, meta = self._strategy_response(state, service_result)
        elif "credit" in intent_lower:
            message, meta = self._credit_response(state)
        elif "opportun" in intent_lower:
            message, meta = self._opportunity_response(state, service_result, recommendation)
        elif intent_lower in {"greeting", "help"}:
            message, meta = self._greeting_response(state)
        else:
            message, meta = self._general_response(state, recommendation or {}, ai_analysis, intent_lower)

        if requires_approval:
            meta["requires_approval"] = True

        enriched = self.persona.apply(message, state=state, intent=intent_lower)
        return RenderResult(enriched, meta)

    def clarifying_question(
        self,
        *,
        request: str,
        intent_candidates: Dict[str, float],
        state: ConversationStateSnapshot,
    ) -> str:
        sorted_candidates = sorted(
            intent_candidates.items(), key=lambda item: item[1], reverse=True
        )
        if sorted_candidates:
            top_candidate = sorted_candidates[0][0].replace("_", " ")
            alt_candidate = sorted_candidates[1][0].replace("_", " ") if len(sorted_candidates) > 1 else None
        else:
            top_candidate, alt_candidate = "portfolio", None

        pieces = [
            f"I want to make sure I understood your note about '{request}'."
        ]
        follow_options: List[str] = []
        follow_options.append(f"a rundown of your {top_candidate}")
        if alt_candidate:
            follow_options.append(f"insight on {alt_candidate}")
        follow_text = " or ".join(follow_options)
        pieces.append(f"Are you looking for {follow_text}? If not, let me know what you'd like me to analyze.")
        return self.persona.apply(" ".join(pieces), state=state, intent="clarifying")

    def _portfolio_response(
        self,
        state: ConversationStateSnapshot,
        service_result: Dict[str, Any],
        recommendation: Dict[str, Any],
    ) -> tuple[str, Dict[str, Any]]:
        portfolio = state.portfolio or {}
        total_value = state.portfolio_value
        holdings = state.summarize_holdings()
        risk = (portfolio.get("risk_level") or state.risk_profile or "balanced").lower()
        exchanges = portfolio.get("exchanges_connected") or len(portfolio.get("exchanges", []) or [])
        change = portfolio.get("daily_pnl")
        change_pct = portfolio.get("daily_pnl_pct")

        lines: List[str] = []
        if total_value > 0:
            lines.append(
                f"Your portfolio is sitting at ${total_value:,.2f} across {exchanges or 'your connected'} exchanges."
            )
        if holdings:
            holding_sentence = ", ".join(
                f"{symbol} ({pct:.0f}%)" for symbol, pct in holdings
            )
            lines.append(
                f"Top weights are {holding_sentence}—a healthy spread for your {risk} risk posture."
            )
        if change is not None and change_pct is not None:
            lines.append(
                f"We're {('up' if change >= 0 else 'down')} ${abs(change):,.2f} ({change_pct:.2f}%) on the last 24 hours."
            )
        if not lines:
            lines.append("I don't see live balances yet, so we're in monitoring mode until new data syncs.")

        lines.append("Want me to zoom in on a position or scan for a rebalance?")

        metadata = {
            "portfolio_value": total_value,
            "risk_level": risk,
            "top_positions": holdings,
        }
        return " ".join(lines), metadata

    def _strategy_response(
        self,
        state: ConversationStateSnapshot,
        service_result: Dict[str, Any],
    ) -> tuple[str, Dict[str, Any]]:
        strategies = state.strategies.active
        marketplace = state.strategies.marketplace_highlights
        lines: List[str] = []
        if strategies:
            names = [s.get("name") or s.get("strategy_name") for s in strategies[:3]]
            cleaned_names = ", ".join(filter(None, names))
            lines.append(
                f"You're currently in manual mode with {len(strategies)} strategies staged: {cleaned_names}."
            )
        else:
            lines.append("You're not running automated strategies yet—we're in manual guidance mode.")

        if marketplace:
            categories = {item.get("category", "market") for item in marketplace[:5]}
            lines.append(
                "We can activate marketplace models in "
                + ", ".join(sorted(filter(None, categories)))
                + " whenever you want."
            )
        else:
            lines.append(
                "Marketplace access is available if you'd like Kelly optimization, pattern recognition, or derivatives coverage."
            )

        lines.append("Should I stage a paper run or pull today's best signals from a category?")
        metadata = {
            "active_strategy_count": len(strategies),
            "marketplace_samples": [item.get("name") for item in marketplace[:5]],
        }
        return " ".join(lines), metadata

    def _credit_response(self, state: ConversationStateSnapshot) -> tuple[str, Dict[str, Any]]:
        credit = state.credit
        available = credit.available_credits
        profit_potential = credit.profit_potential_usd
        ratio = credit.credit_to_usd_ratio

        lines: List[str] = []
        if available > 0:
            lines.append(
                f"You have {available} credits live, which unlock about ${profit_potential:,.0f} in profit runway at the current conversion."
            )
        else:
            lines.append("You currently have 0 credits, so we're in analysis mode until you top up.")

        lines.append(
            "Each credit currently maps to roughly ${:.2f} in commission capacity."
            .format(ratio)
        )
        lines.append("Want me to start a credit upgrade or reallocate toward paper trades instead?")

        metadata = {
            "available_credits": available,
            "profit_potential_usd": profit_potential,
            "credit_to_usd_ratio": ratio,
            "tier": credit.tier,
        }
        return " ".join(lines), metadata

    def _opportunity_response(
        self,
        state: ConversationStateSnapshot,
        service_result: Dict[str, Any],
        recommendation: Dict[str, Any],
    ) -> tuple[str, Dict[str, Any]]:
        ranked = rank_opportunities(
            service_result or recommendation,
            risk_profile=state.risk_profile,
            portfolio_value=state.portfolio_value,
        )

        lines: List[str] = []
        if ranked:
            lines.append(
                f"I'm tracking {len(ranked)} setups that fit your {state.risk_profile} profile."
            )
            highlights = []
            for idx, opp in enumerate(ranked[:3], start=1):
                potential_text = (
                    f"${opp.potential_usd:,.0f}" if opp.potential_usd else "portfolio-aligned"
                )
                probability = (
                    f"{opp.win_probability * 100:.0f}%" if opp.win_probability else "solid"
                )
                risk_text = opp.risk_level.replace("_", " ")
                rationale = opp.rationale or "momentum + structure"
                highlights.append(
                    f"{idx}. {opp.symbol} {opp.direction or 'opportunity'} – {potential_text} potential, {probability} probability, {risk_text} risk. Rationale: {rationale}."
                )
            lines.append(" ".join(highlights))
        else:
            lines.append(
                "I'm scanning live feeds but don't have a clean setup that matches your risk bands yet. I'll alert you as soon as one clears our filters."
            )

        lines.append("Do you want me to reserve capital for one of these or widen the search?")
        metadata = {
            "ranked_opportunities": [opp.to_dict() for opp in ranked],
        }
        return " ".join(lines), metadata

    def _greeting_response(
        self,
        state: ConversationStateSnapshot,
    ) -> tuple[str, Dict[str, Any]]:
        if state.portfolio_value > 0:
            message = (
                f"Welcome back. Your portfolio is synced at ${state.portfolio_value:,.2f}."
            )
        else:
            message = "Welcome back. I'm monitoring your accounts and ready when you are."
        message += " Ask for your balance, today's opportunities, or tell me what position you want to review."
        return message, {}

    def _general_response(
        self,
        state: ConversationStateSnapshot,
        recommendation: Dict[str, Any],
        ai_analysis: Optional[str],
        intent: str,
    ) -> tuple[str, Dict[str, Any]]:
        analysis_text = recommendation.get("analysis") if isinstance(recommendation, dict) else None
        if not analysis_text:
            analysis_text = ai_analysis or "I completed the analysis you asked for."
        message = analysis_text
        if intent == "general_query" and state.portfolio_value == 0:
            message += " Let me know if you'd like me to sync balances or walk through strategy options."
        return message, {"raw_recommendation": recommendation}
