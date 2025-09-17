"""
A/B Testing Lab API endpoints for CryptoUniverse.

This module provides endpoints for creating, managing, and analyzing A/B tests
for trading strategies to optimize performance through experimentation.
"""

import uuid
import asyncio
import os
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any
from enum import Enum
from fastapi import APIRouter, HTTPException, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.core.database import get_database
from app.middleware.auth import get_current_user
from app.models.user import User
import structlog

logger = structlog.get_logger(__name__)

router = APIRouter()

# Demo mode feature flag - set via environment variable
# In production, this should be False and use database-backed storage
DEMO_MODE = os.getenv("AB_TESTING_DEMO_MODE", "true").lower() == "true"

if DEMO_MODE:
    logger.warning(
        "ab_testing.demo_mode_enabled",
        message="A/B Testing is running in DEMO MODE with in-memory storage. "
                "This is UNSAFE for production multi-worker deployments!"
    )

# Enums for validation
class SuccessMetric(str, Enum):
    """Valid success metrics for A/B tests with direction-aware comparison."""
    total_return = "total_return"
    sharpe_ratio = "sharpe_ratio"
    win_rate = "win_rate"
    profit_factor = "profit_factor"
    max_drawdown = "max_drawdown"
    volatility = "volatility"
    avg_trade_duration = "avg_trade_duration"
    total_trades = "total_trades"

# Pydantic Models
class ABTestVariantCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., max_length=500)
    strategy_code: str = Field(..., min_length=10)
    parameters: Dict[str, Any] = Field(default_factory=dict)
    allocation_percentage: int = Field(ge=1, le=100)
    is_control: bool = False

class ABTestVariant(BaseModel):
    id: str
    name: str
    description: str
    strategy_code: str
    parameters: Dict[str, Any]
    allocation_percentage: int
    is_control: bool
    status: str

    # Performance Metrics
    total_return: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    total_trades: int = 0
    avg_trade_duration: float = 0.0
    profit_factor: float = 0.0
    volatility: float = 0.0

    # Statistical Significance
    p_value: float = 1.0
    confidence_level: float = 95.0
    statistical_significance: str = "inconclusive"

    # User Metrics
    active_users: int = 0
    user_satisfaction: float = 0.0

    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

class ABTestCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., max_length=1000)
    hypothesis: str = Field(..., min_length=10, max_length=1000)
    success_metric: SuccessMetric = Field(default=SuccessMetric.total_return)
    min_sample_size: int = Field(ge=100, le=100000, default=1000)
    confidence_level: int = Field(ge=90, le=99, default=95)
    test_duration_days: int = Field(ge=1, le=90, default=30)
    traffic_allocation: int = Field(ge=5, le=50, default=20)
    variants: List[ABTestVariantCreate] = Field(min_items=2, max_items=5)

class ABTest(BaseModel):
    id: str
    name: str
    description: str
    hypothesis: str
    success_metric: str
    status: str

    # Test Configuration
    min_sample_size: int
    confidence_level: int
    test_duration_days: int
    traffic_allocation: int

    # Results
    total_participants: int = 0
    winning_variant_id: Optional[str] = None
    statistical_power: float = 0.0
    effect_size: float = 0.0

    variants: List[ABTestVariant]

    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_by: str

class ABTestMetrics(BaseModel):
    total_tests: int
    running_tests: int
    completed_tests: int
    successful_optimizations: int
    avg_improvement: float
    total_participants: int

class ABTestResponse(BaseModel):
    success: bool
    message: str
    test: Optional[ABTest] = None

class ABTestListResponse(BaseModel):
    success: bool
    tests: List[ABTest]
    total_count: int
    page: int
    page_size: int

# In-memory storage - ONLY for demo mode
# TODO: PRODUCTION IMPLEMENTATION REQUIRED
# TODO: Replace with SQLAlchemy-backed repository/service layer using app/models/ab_testing.py
# TODO: Implement proper repository pattern with database transactions
# TODO: Add database migrations for A/B testing tables
# TODO: This current in-memory approach is UNSAFE for concurrent/multi-worker deployments
# TODO: Use database-backed storage with proper connection pooling and async operations
if DEMO_MODE:
    # Thread-safe lock for demo mode operations
    _demo_mode_lock = asyncio.Lock()

    # DEMO STORAGE: In-memory dictionaries (NOT for production!)
    ab_tests_storage: Dict[str, Dict] = {}
    ab_test_metrics_cache: Dict = {
        "total_tests": 0,
        "running_tests": 0,
        "completed_tests": 0,
        "successful_optimizations": 0,
        "avg_improvement": 0.0,
        "total_participants": 0,
        "last_updated": datetime.now(timezone.utc)
    }

    logger.info(
        "ab_testing.demo_storage_initialized",
        message="Demo mode storage initialized - use AB_TESTING_DEMO_MODE=false for production"
    )
else:
    # Production mode - storage should use database-backed repository pattern
    _demo_mode_lock = None
    ab_tests_storage = None
    ab_test_metrics_cache = None

    logger.info(
        "ab_testing.production_mode",
        message="Production mode enabled - database-backed storage required"
    )

# Metric direction mapping for proper winner selection
METRIC_DIRECTIONS = {
    "total_return": "max",
    "sharpe_ratio": "max",
    "win_rate": "max",
    "profit_factor": "max",
    "max_drawdown": "min",  # Lower drawdown is better
    "volatility": "min",    # Lower volatility is often better
    "avg_trade_duration": "min",  # Usually faster is better
    "total_trades": "max",
}

def generate_mock_performance_data():
    """Generate realistic mock performance data for demo purposes."""
    import random
    return {
        "total_return": round(random.uniform(-15.0, 25.0), 2),
        "sharpe_ratio": round(random.uniform(0.5, 2.5), 2),
        "max_drawdown": round(random.uniform(-25.0, -2.0), 2),
        "win_rate": round(random.uniform(45.0, 75.0), 2),
        "total_trades": random.randint(50, 500),
        "avg_trade_duration": round(random.uniform(1.5, 48.0), 1),
        "profit_factor": round(random.uniform(0.8, 2.2), 2),
        "volatility": round(random.uniform(8.0, 35.0), 2),
        "p_value": round(random.uniform(0.01, 0.5), 3),
        "active_users": random.randint(50, 1000),
        "user_satisfaction": round(random.uniform(3.5, 4.8), 1)
    }

def calculate_statistical_significance(p_value: float, confidence_level: float) -> str:
    """Calculate statistical significance based on p-value and confidence level."""
    alpha = (100 - confidence_level) / 100
    if p_value < alpha:
        return "significant"
    elif p_value < alpha * 2:
        return "inconclusive"
    else:
        return "not_significant"

async def _check_demo_mode():
    """Ensure demo mode is enabled for in-memory operations."""
    if not DEMO_MODE:
        logger.error(
            "ab_testing.production_mode_not_implemented",
            message="A/B Testing API called in production mode without database implementation"
        )
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail={
                "error": "A/B Testing production mode not implemented",
                "message": "This feature requires database-backed storage in production mode.",
                "demo_mode": "Set AB_TESTING_DEMO_MODE=true environment variable for demo functionality",
                "implementation_needed": [
                    "Database repository layer implementation",
                    "SQLAlchemy model integration",
                    "Proper connection pooling",
                    "Database migrations"
                ],
                "current_status": "Demo mode only - unsafe for multi-worker deployments"
            }
        )

async def update_metrics_cache():
    """Update the metrics cache based on current tests. Thread-safe for demo mode."""
    await _check_demo_mode()
    global ab_test_metrics_cache

    async with _demo_mode_lock:
        total_tests = len(ab_tests_storage)
        running_tests = len([t for t in ab_tests_storage.values() if t["status"] == "running"])
        completed_tests = len([t for t in ab_tests_storage.values() if t["status"] == "completed"])
        successful_optimizations = len([t for t in ab_tests_storage.values()
                                      if t["status"] == "completed" and t.get("winning_variant_id")])

        improvements = []
        total_participants = 0

        for test in ab_tests_storage.values():
            total_participants += test.get("total_participants", 0)
            if test["status"] == "completed" and test.get("effect_size", 0) > 0:
                improvements.append(test["effect_size"])

        avg_improvement = sum(improvements) / len(improvements) if improvements else 0.0

        ab_test_metrics_cache.update({
            "total_tests": total_tests,
            "running_tests": running_tests,
            "completed_tests": completed_tests,
            "successful_optimizations": successful_optimizations,
            "avg_improvement": avg_improvement,
            "total_participants": total_participants,
            "last_updated": datetime.now(timezone.utc)
        })

@router.get("/metrics", response_model=ABTestMetrics, tags=["A/B Testing"])
async def get_ab_testing_metrics(current_user: User = Depends(get_current_user)):
    """Get A/B testing overview metrics."""
    try:
        await _check_demo_mode()  # Ensure demo mode for in-memory operations
        logger.info("ab_testing.get_metrics", user_id=current_user.id)

        await update_metrics_cache()

        return ABTestMetrics(**ab_test_metrics_cache)

    except Exception as e:
        logger.error("ab_testing.get_metrics_failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve A/B testing metrics: {str(e)}"
        )

@router.get("/tests", response_model=ABTestListResponse, tags=["A/B Testing"])
async def get_ab_tests(
    status_filter: Optional[str] = Query(None, description="Filter by test status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user)
):
    """Get list of A/B tests for the current user."""
    try:
        await _check_demo_mode()  # Ensure demo mode for in-memory operations
        logger.info("ab_testing.get_tests", user_id=current_user.id, status_filter=status_filter)

        # Filter tests by user and status (thread-safe read)
        async with _demo_mode_lock:
            user_tests = [
                test for test in ab_tests_storage.values()
                if test["created_by"] == str(current_user.id)
            ]

        if status_filter and status_filter != "all":
            user_tests = [test for test in user_tests if test["status"] == status_filter]

        # Sort by created_at desc
        user_tests.sort(key=lambda x: x["created_at"], reverse=True)

        # Pagination
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_tests = user_tests[start_idx:end_idx]

        # Convert to Pydantic models
        test_models = []
        for test_data in paginated_tests:
            variants = []
            for variant_data in test_data["variants"]:
                variant = ABTestVariant(**variant_data)
                variants.append(variant)

            test_model = ABTest(
                **{k: v for k, v in test_data.items() if k != "variants"},
                variants=variants
            )
            test_models.append(test_model)

        return ABTestListResponse(
            success=True,
            tests=test_models,
            total_count=len(user_tests),
            page=page,
            page_size=page_size
        )

    except Exception as e:
        logger.error("ab_testing.get_tests_failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve A/B tests: {str(e)}"
        )

@router.post("/tests", response_model=ABTestResponse, tags=["A/B Testing"])
async def create_ab_test(
    test_data: ABTestCreate,
    current_user: User = Depends(get_current_user)
):
    """Create a new A/B test."""
    try:
        await _check_demo_mode()  # Ensure demo mode for in-memory operations
        logger.info("ab_testing.create_test", user_id=current_user.id, test_name=test_data.name)

        # Validate variants allocation
        total_allocation = sum(variant.allocation_percentage for variant in test_data.variants)
        if total_allocation != 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Variant allocations must sum to 100%, got {total_allocation}%"
            )

        # Check for exactly one control variant
        control_variants = [v for v in test_data.variants if v.is_control]
        if len(control_variants) != 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Exactly one variant must be marked as control"
            )

        # Generate test ID
        test_id = str(uuid.uuid4())

        # Create variants with mock performance data
        variants = []
        for variant_data in test_data.variants:
            variant_id = str(uuid.uuid4())
            performance_data = generate_mock_performance_data()

            variant = {
                "id": variant_id,
                "name": variant_data.name,
                "description": variant_data.description,
                "strategy_code": variant_data.strategy_code,
                "parameters": variant_data.parameters,
                "allocation_percentage": variant_data.allocation_percentage,
                "is_control": variant_data.is_control,
                "status": "draft",
                **performance_data,
                "statistical_significance": calculate_statistical_significance(
                    performance_data["p_value"], test_data.confidence_level
                ),
                "confidence_level": test_data.confidence_level,
                "created_at": datetime.now(timezone.utc),
                "started_at": None,
                "completed_at": None
            }
            variants.append(variant)

        # Create test
        test = {
            "id": test_id,
            "name": test_data.name,
            "description": test_data.description,
            "hypothesis": test_data.hypothesis,
            "success_metric": test_data.success_metric.value,
            "status": "draft",
            "min_sample_size": test_data.min_sample_size,
            "confidence_level": test_data.confidence_level,
            "test_duration_days": test_data.test_duration_days,
            "traffic_allocation": test_data.traffic_allocation,
            "total_participants": 0,
            "winning_variant_id": None,
            "statistical_power": 0.0,
            "effect_size": 0.0,
            "variants": variants,
            "created_at": datetime.now(timezone.utc),
            "started_at": None,
            "completed_at": None,
            "created_by": str(current_user.id)
        }

        # Store test (thread-safe write)
        async with _demo_mode_lock:
            ab_tests_storage[test_id] = test

        # Update metrics
        await update_metrics_cache()

        # Convert to response model
        variant_models = [ABTestVariant(**v) for v in variants]
        test_model = ABTest(**{k: v for k, v in test.items() if k != "variants"}, variants=variant_models)

        logger.info("ab_testing.test_created", test_id=test_id, user_id=current_user.id)

        return ABTestResponse(
            success=True,
            message="A/B test created successfully",
            test=test_model
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("ab_testing.create_test_failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create A/B test: {str(e)}"
        )

@router.post("/tests/{test_id}/start", response_model=ABTestResponse, tags=["A/B Testing"])
async def start_ab_test(
    test_id: str,
    current_user: User = Depends(get_current_user)
):
    """Start an A/B test."""
    try:
        await _check_demo_mode()  # Ensure demo mode for in-memory operations
        logger.info("ab_testing.start_test", test_id=test_id, user_id=current_user.id)

        # Get test
        if test_id not in ab_tests_storage:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="A/B test not found"
            )

        test = ab_tests_storage[test_id]

        # Check ownership
        if test["created_by"] != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to modify this test"
            )

        # Check status
        if test["status"] not in ["draft", "paused"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot start test in {test['status']} status"
            )

        # Start test (thread-safe update)
        async with _demo_mode_lock:
            test["status"] = "running"
            test["started_at"] = datetime.now(timezone.utc)

            # Start variants
            for variant in test["variants"]:
                variant["status"] = "running"
                if not variant["started_at"]:
                    variant["started_at"] = datetime.now(timezone.utc)

            # Simulate some participants
            import random
            test["total_participants"] = random.randint(100, 1500)

        # Update metrics
        await update_metrics_cache()

        logger.info("ab_testing.test_started", test_id=test_id, user_id=current_user.id)

        return ABTestResponse(
            success=True,
            message="A/B test started successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("ab_testing.start_test_failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start A/B test: {str(e)}"
        )

@router.post("/tests/{test_id}/pause", response_model=ABTestResponse, tags=["A/B Testing"])
async def pause_ab_test(
    test_id: str,
    current_user: User = Depends(get_current_user)
):
    """Pause a running A/B test."""
    try:
        await _check_demo_mode()  # Ensure demo mode for in-memory operations
        logger.info("ab_testing.pause_test", test_id=test_id, user_id=current_user.id)

        # Get test
        if test_id not in ab_tests_storage:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="A/B test not found"
            )

        test = ab_tests_storage[test_id]

        # Check ownership
        if test["created_by"] != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to modify this test"
            )

        # Check status
        if test["status"] != "running":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot pause test in {test['status']} status"
            )

        # Pause test (thread-safe update)
        async with _demo_mode_lock:
            test["status"] = "paused"

            # Pause variants
            for variant in test["variants"]:
                variant["status"] = "paused"

        # Update metrics
        await update_metrics_cache()

        logger.info("ab_testing.test_paused", test_id=test_id, user_id=current_user.id)

        return ABTestResponse(
            success=True,
            message="A/B test paused successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("ab_testing.pause_test_failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to pause A/B test: {str(e)}"
        )

@router.post("/tests/{test_id}/stop", response_model=ABTestResponse, tags=["A/B Testing"])
async def stop_ab_test(
    test_id: str,
    current_user: User = Depends(get_current_user)
):
    """Stop an A/B test and finalize results."""
    try:
        await _check_demo_mode()  # Ensure demo mode for in-memory operations
        logger.info("ab_testing.stop_test", test_id=test_id, user_id=current_user.id)

        # Get test
        if test_id not in ab_tests_storage:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="A/B test not found"
            )

        test = ab_tests_storage[test_id]

        # Check ownership
        if test["created_by"] != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to modify this test"
            )

        # Check status
        if test["status"] not in ["running", "paused"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot stop test in {test['status']} status"
            )

        # Stop test (thread-safe update)
        async with _demo_mode_lock:
            test["status"] = "completed"
            test["completed_at"] = datetime.now(timezone.utc)

            # Complete variants
            for variant in test["variants"]:
                variant["status"] = "completed"
                variant["completed_at"] = datetime.now(timezone.utc)

            # Determine winner (direction-aware based on selected metric)
            significant_variants = [
                v for v in test["variants"]
                if v["statistical_significance"] == "significant"
            ]

            if significant_variants:
                metric = test["success_metric"]
                direction = METRIC_DIRECTIONS[metric]
                control = next(v for v in test["variants"] if v["is_control"])

                if direction == "max":
                    winner = max(significant_variants, key=lambda x: x[metric])
                    effect = winner[metric] - control[metric]
                else:
                    winner = min(significant_variants, key=lambda x: x[metric])
                    effect = control[metric] - winner[metric]

                test["winning_variant_id"] = winner["id"]
                test["effect_size"] = round(effect, 4)
            else:
                test["winning_variant_id"] = None
                test["effect_size"] = 0.0

            # Set statistical power
            import random
            test["statistical_power"] = round(random.uniform(0.8, 0.95), 2)

        # Update metrics
        await update_metrics_cache()

        logger.info("ab_testing.test_stopped", test_id=test_id, user_id=current_user.id,
                   winner_id=test.get("winning_variant_id"))

        return ABTestResponse(
            success=True,
            message="A/B test completed successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("ab_testing.stop_test_failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stop A/B test: {str(e)}"
        )

@router.get("/tests/{test_id}", response_model=ABTest, tags=["A/B Testing"])
async def get_ab_test(
    test_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get details of a specific A/B test."""
    try:
        await _check_demo_mode()  # Ensure demo mode for in-memory operations
        logger.info("ab_testing.get_test", test_id=test_id, user_id=current_user.id)

        # Get test
        if test_id not in ab_tests_storage:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="A/B test not found"
            )

        test = ab_tests_storage[test_id]

        # Check ownership
        if test["created_by"] != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view this test"
            )

        # Convert to response model
        variants = [ABTestVariant(**v) for v in test["variants"]]
        test_model = ABTest(**{k: v for k, v in test.items() if k != "variants"}, variants=variants)

        return test_model

    except HTTPException:
        raise
    except Exception as e:
        logger.error("ab_testing.get_test_failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve A/B test: {str(e)}"
        )

@router.delete("/tests/{test_id}", response_model=ABTestResponse, tags=["A/B Testing"])
async def delete_ab_test(
    test_id: str,
    current_user: User = Depends(get_current_user)
):
    """Delete an A/B test (only if in draft status)."""
    try:
        await _check_demo_mode()  # Ensure demo mode for in-memory operations
        logger.info("ab_testing.delete_test", test_id=test_id, user_id=current_user.id)

        # Get test
        if test_id not in ab_tests_storage:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="A/B test not found"
            )

        test = ab_tests_storage[test_id]

        # Check ownership
        if test["created_by"] != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this test"
            )

        # Check status
        if test["status"] != "draft":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Can only delete tests in draft status"
            )

        # Delete test (thread-safe delete)
        async with _demo_mode_lock:
            del ab_tests_storage[test_id]

        # Update metrics
        await update_metrics_cache()

        logger.info("ab_testing.test_deleted", test_id=test_id, user_id=current_user.id)

        return ABTestResponse(
            success=True,
            message="A/B test deleted successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("ab_testing.delete_test_failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete A/B test: {str(e)}"
        )