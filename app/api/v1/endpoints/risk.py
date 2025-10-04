"""Risk management endpoints for portfolio analytics and controls."""

from typing import Any, Dict, List, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, validator

from app.api.v1.endpoints.auth import get_current_user
from app.models.user import User
from app.services.portfolio_risk_core import PortfolioRiskServiceExtended
from app.services.emergency_manager import emergency_manager, EmergencyLevel


logger = structlog.get_logger(__name__)

router = APIRouter()

risk_service = PortfolioRiskServiceExtended()


DEFAULT_RISK_GUIDELINES = [
    "Limit any single asset to 10% or less of total trading capital.",
    "Always attach stop-loss orders at or tighter than the recommended threshold.",
    "Target a minimum 2:1 reward-to-risk ratio before entering new positions.",
    "Reduce leverage and size when annualised volatility exceeds 60%.",
    "Rebalance if portfolio correlation to the market climbs above 0.80."
]


class RiskDashboardResponse(BaseModel):
    """Shape of the risk dashboard payload."""

    success: bool
    metrics: Optional[Dict[str, Any]] = None
    portfolio_value: Optional[float] = None
    analysis_parameters: Optional[Dict[str, Any]] = None
    risk_alerts: Optional[List[Dict[str, Any]]] = None
    guidelines: List[str] = Field(default_factory=list)
    risk_controls: Dict[str, Any]
    emergency_policies: Dict[str, Any]
    last_updated: Optional[str] = None


class PositionSizingRequest(BaseModel):
    symbol: str = Field(..., min_length=1, description="Asset ticker to size a position for")
    expected_return: float = Field(..., gt=-1000, lt=1000, description="Expected percentage return of the setup")
    confidence: float = Field(..., ge=0, le=100, description="Confidence score from 0-100")
    mode: str = Field("balanced", description="Trading mode: conservative, balanced, aggressive, beast_mode")
    stop_loss_pct: Optional[float] = Field(2.0, gt=0, lt=100, description="Preferred stop loss percentage")
    take_profit_pct: Optional[float] = Field(4.0, gt=0, lt=200, description="Preferred take profit percentage")

    @validator("symbol")
    def normalize_symbol(cls, value: str) -> str:
        return value.upper().strip()


class PositionSizingResponse(BaseModel):
    success: bool
    position_sizing: Optional[Dict[str, Any]] = None
    guidelines: List[str]
    risk_controls: Dict[str, Any]


class EmergencyPolicyUpdateRequest(BaseModel):
    opt_in: Optional[bool] = None
    thresholds: Optional[Dict[str, float]] = None


def _normalize_threshold_keys(thresholds: Dict[str, float]) -> Dict[EmergencyLevel, float]:
    """Convert client-provided threshold keys into EmergencyLevel values."""

    normalized: Dict[EmergencyLevel, float] = {}

    for key, value in thresholds.items():
        if value is None:
            continue

        try:
            level = EmergencyLevel(key.lower())
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported emergency level '{key}'."
            ) from exc

        normalized[level] = float(value)

    return normalized


def _validate_threshold_sequence(thresholds: Dict[EmergencyLevel, float]) -> None:
    """Ensure thresholds escalate in the correct order."""

    warning = thresholds.get(EmergencyLevel.WARNING, emergency_manager.circuit_breakers[EmergencyLevel.WARNING]["loss_threshold_pct"])
    critical = thresholds.get(EmergencyLevel.CRITICAL, emergency_manager.circuit_breakers[EmergencyLevel.CRITICAL]["loss_threshold_pct"])
    emergency = thresholds.get(EmergencyLevel.EMERGENCY, emergency_manager.circuit_breakers[EmergencyLevel.EMERGENCY]["loss_threshold_pct"])

    if not (warning < critical < emergency):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Emergency thresholds must increase: warning < critical < emergency."
        )


@router.get("/dashboard", response_model=RiskDashboardResponse)
async def get_risk_dashboard(
    lookback_days: int = 252,
    current_user: User = Depends(get_current_user)
) -> RiskDashboardResponse:
    """Return portfolio risk analytics derived from the risk calculation engine."""

    user_id = str(current_user.id)

    try:
        result = await risk_service.risk_analysis(user_id, lookback_days=lookback_days)
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.error("risk.dashboard.failed", user_id=user_id, error=str(exc), exc_info=True)
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to calculate portfolio risk") from exc

    if not result.get("success"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=result.get("error", "Risk analysis unavailable"))

    metrics = result.get("risk_metrics", {})

    enriched_metrics = {
        "var_95": metrics.get("var_95", 0.0),
        "var_95_percent": metrics.get("var_95_percent", 0.0),
        "var_99": metrics.get("var_99", 0.0),
        "var_99_percent": metrics.get("var_99_percent", 0.0),
        "expected_shortfall": metrics.get("expected_shortfall", 0.0),
        "expected_shortfall_percent": metrics.get("expected_shortfall", 0.0) * 100,
        "volatility_annual": metrics.get("volatility_annual", 0.0),
        "volatility_percent": metrics.get("volatility_annual", 0.0) * 100,
        "sharpe_ratio": metrics.get("sharpe_ratio", 0.0),
        "sortino_ratio": metrics.get("sortino_ratio", 0.0),
        "beta": metrics.get("beta", 0.0),
        "alpha": metrics.get("alpha", 0.0),
        "correlation_to_market": metrics.get("correlation_to_market", 0.0),
        "maximum_drawdown": metrics.get("maximum_drawdown", 0.0),
        "maximum_drawdown_percent": metrics.get("maximum_drawdown", 0.0) * 100,
    }

    emergency_policies = emergency_manager.get_policy_overview(user_id)

    risk_controls = {
        "position_limits": {
            "max_single_position_pct": 10.0,
            "sizing_engine": "kelly_fraction_with_risk_overlays",
            "enforced": True,
        },
        "execution_rules": {
            "stop_loss_required": True,
            "stop_loss_guidance": "Attach stop-loss orders at or tighter than the recommended threshold from the position sizing engine.",
            "take_profit_required": True,
            "take_profit_guidance": "Respect the suggested take-profit targets to lock in gains.",
        },
        "monitoring": {
            "volatility_review_trigger_pct": enriched_metrics.get("volatility_percent", 0.0),
            "correlation_trigger_threshold": 0.80,
        },
        "circuit_breakers": [
            {
                "level": policy.get("level"),
                "loss_threshold_pct": policy.get("loss_threshold_pct"),
                "action": policy.get("action"),
                "halt_new_trades": policy.get("halt_new_trades"),
                "description": policy.get("description"),
            }
            for policy in emergency_policies.get("policies", [])
        ],
    }

    return RiskDashboardResponse(
        success=True,
        metrics=enriched_metrics,
        portfolio_value=result.get("portfolio_value"),
        analysis_parameters=result.get("analysis_parameters", {}),
        risk_alerts=result.get("risk_alerts", []),
        guidelines=DEFAULT_RISK_GUIDELINES,
        risk_controls=risk_controls,
        emergency_policies=emergency_policies,
        last_updated=result.get("timestamp")
    )


@router.post("/position-sizing", response_model=PositionSizingResponse)
async def calculate_position_sizing(
    payload: PositionSizingRequest,
    current_user: User = Depends(get_current_user)
) -> PositionSizingResponse:
    """Return recommended position sizing using the Kelly-based engine."""

    user_id = str(current_user.id)

    opportunity: Dict[str, Any] = {
        "symbol": payload.symbol,
        "confidence": payload.confidence,
        "expected_return": payload.expected_return,
        "stop_loss_pct": payload.stop_loss_pct,
        "take_profit_pct": payload.take_profit_pct,
    }

    try:
        result = await risk_service.position_sizing(opportunity, user_id, mode=payload.mode)
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("risk.position_sizing.failed", user_id=user_id, error=str(exc), exc_info=True)
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unable to calculate position size") from exc

    if not result.get("success"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=result.get("error", "Position sizing unavailable"))

    sizing = result.get("position_sizing", {})
    position_value = float(sizing.get("position_value_usd", 0.0))
    stop_loss_pct = payload.stop_loss_pct or 2.0
    take_profit_pct = payload.take_profit_pct or 4.0

    risk_controls = {
        "max_position_pct": 10.0,
        "recommended_stop_loss_pct": stop_loss_pct,
        "recommended_take_profit_pct": take_profit_pct,
        "stop_loss_usd": position_value * (stop_loss_pct / 100),
        "take_profit_usd": position_value * (take_profit_pct / 100),
        "portfolio_context": result.get("portfolio_context", {}),
    }

    guidelines = [
        "Limit any single asset to 10% or less of total capital.",
        "Respect the recommended stop-loss and take-profit levels on every trade.",
        "Scale into positions gradually when the recommended size exceeds 5% of capital.",
    ]

    return PositionSizingResponse(
        success=True,
        position_sizing=sizing,
        guidelines=guidelines,
        risk_controls=risk_controls
    )


@router.get("/emergency-policies")
async def get_emergency_policies(current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
    """Expose emergency manager policies and user-specific preferences."""

    user_id = str(current_user.id)
    overview = emergency_manager.get_policy_overview(user_id)
    overview.update({"success": True})
    return overview


@router.post("/emergency-policies")
async def update_emergency_policies(
    payload: EmergencyPolicyUpdateRequest,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Allow users to opt into emergency automation and set custom thresholds."""

    user_id = str(current_user.id)

    try:
        if payload.thresholds:
            normalized = _normalize_threshold_keys(payload.thresholds)

            overview = emergency_manager.get_policy_overview(user_id)
            effective_thresholds = {
                EmergencyLevel.WARNING: emergency_manager.circuit_breakers[EmergencyLevel.WARNING]["loss_threshold_pct"],
                EmergencyLevel.CRITICAL: emergency_manager.circuit_breakers[EmergencyLevel.CRITICAL]["loss_threshold_pct"],
                EmergencyLevel.EMERGENCY: emergency_manager.circuit_breakers[EmergencyLevel.EMERGENCY]["loss_threshold_pct"],
            }

            for policy in overview.get("policies", []):
                try:
                    level = EmergencyLevel(policy.get("level", ""))
                except ValueError:
                    continue

                try:
                    effective_thresholds[level] = float(policy.get("loss_threshold_pct", effective_thresholds[level]))
                except (TypeError, ValueError):
                    continue

            effective_thresholds.update(normalized)

            _validate_threshold_sequence(effective_thresholds)
            emergency_manager.update_user_thresholds(user_id, normalized)

        if payload.opt_in is not None:
            emergency_manager.set_user_opt_in(user_id, payload.opt_in)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    overview = emergency_manager.get_policy_overview(user_id)
    overview.update({"success": True})
    return overview
