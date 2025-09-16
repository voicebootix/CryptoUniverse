"""
Admin Testing Endpoints

Dedicated endpoints for admin to test all strategies without purchase requirements.
"""

from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from app.api.v1.endpoints.auth import get_current_user
from app.models.user import User
from app.services.trading_strategies import trading_strategies_service
import structlog
import os
import inspect

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/admin/testing", tags=["Admin Testing"])


class AdminStrategyTestRequest(BaseModel):
    """Request model for admin strategy testing."""
    function: str = Field(..., description="Strategy function name to test")
    symbol: str = Field(default="BTC/USDT", description="Trading symbol")
    parameters: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Strategy parameters")


class AdminBulkTestRequest(BaseModel):
    """Request model for admin bulk strategy testing."""
    functions: List[str] = Field(..., description="List of strategy functions to test")
    symbol: str = Field(default="BTC/USDT", description="Trading symbol")
    parameters: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Common parameters")


@router.post("/strategy/execute")
async def admin_test_strategy(
    request: AdminStrategyTestRequest,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Admin-only endpoint to test any strategy without purchase requirements.
    
    This bypasses all purchase and credit checks for testing purposes.
    """
    
    # Verify admin access (call the method, not just reference it)
    if not current_user.is_admin():
        raise HTTPException(status_code=403, detail="Admin access required")

    # Check environment gate for admin override
    if os.getenv("ADMIN_OVERRIDE_ENABLED", "false").lower() != "true":
        raise HTTPException(status_code=403, detail="Admin override disabled in environment")

    try:
        logger.info("Admin testing strategy", 
                   function=request.function, 
                   symbol=request.symbol,
                   admin_user=current_user.email)
        
        # Execute strategy directly without purchase checks
        result = await trading_strategies_service.execute_strategy(
            function=request.function,
            symbol=request.symbol,
            parameters=request.parameters,
            user_id=str(current_user.id),
            simulation_mode=True
        )
        
        return {
            "success": True,
            "admin_testing": True,
            "function": request.function,
            "execution_result": result,
            "bypass_purchase_check": True,
            "timestamp": "admin_testing_mode"
        }
        
    except Exception as e:
        logger.exception("Admin strategy testing failed")
        raise HTTPException(status_code=500, detail=f"Strategy testing failed: {str(e)}") from e


@router.get("/strategy/list-all")
async def admin_list_all_strategies(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Admin-only endpoint to list all available strategy functions.
    """
    
    if not current_user.is_admin():
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Get all strategy functions via introspection (including bound methods)
    all_functions = []
    excluded_names = {'logger', 'log', 'async_init', 'cleanup'}

    for name, member in inspect.getmembers(trading_strategies_service):
        # Skip private/protected names and excluded methods
        if name.startswith('_') or name in excluded_names:
            continue

        # Check if it's a callable method or function
        if inspect.ismethod(member) or inspect.isfunction(member):
            # For bound methods, check the underlying function's __code__
            func = member.__func__ if inspect.ismethod(member) else member
            if hasattr(func, '__code__'):
                all_functions.append({
                    "function_name": name,
                    "is_strategy": True,
                    "testable": True,
                    "type": "method" if inspect.ismethod(member) else "function"
                })
    
    return {
        "success": True,
        "total_functions": len(all_functions),
        "functions": all_functions,
        "admin_access": True,
        "testing_mode": True
    }


@router.post("/strategy/bulk-test")
async def admin_bulk_test_strategies(
    request: AdminBulkTestRequest,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Admin-only endpoint to test multiple strategies in bulk.
    """

    if not current_user.is_admin():
        raise HTTPException(status_code=403, detail="Admin access required")

    # Check environment gate for admin override (mirror admin_test_strategy)
    if os.getenv("ADMIN_OVERRIDE_ENABLED", "false").lower() != "true":
        raise HTTPException(status_code=403, detail="Admin override disabled in environment")
    
    results = []
    
    for function in request.functions:
        try:
            result = await trading_strategies_service.execute_strategy(
                function=function,
                symbol=request.symbol,
                parameters=request.parameters,
                user_id=str(current_user.id),
                simulation_mode=True
            )
            
            results.append({
                "function": function,
                "success": result.get("success", False),
                "result": result
            })
            
        except Exception as e:
            results.append({
                "function": function,
                "success": False,
                "error": str(e)
            })
    
    successful = len([r for r in results if r.get("success", False)])
    
    return {
        "success": True,
        "total_tested": len(request.functions),
        "successful": successful,
        "success_rate": f"{successful/len(request.functions)*100:.1f}%" if len(request.functions) > 0 else "0.0%",
        "results": results,
        "admin_testing": True
    }