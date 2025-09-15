"""
Admin Testing Endpoints

Dedicated endpoints for admin to test all strategies without purchase requirements.
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any, Optional
from app.api.v1.endpoints.auth import get_current_user
from app.models.user import User
from app.services.trading_strategies import trading_strategies_service
import structlog

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/admin/testing", tags=["Admin Testing"])


@router.post("/strategy/execute")
async def admin_test_strategy(
    function: str,
    symbol: str = "BTC/USDT",
    parameters: Optional[Dict[str, Any]] = None,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Admin-only endpoint to test any strategy without purchase requirements.
    
    This bypasses all purchase and credit checks for testing purposes.
    """
    
    # Verify admin access
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        logger.info("Admin testing strategy", 
                   function=function, 
                   symbol=symbol,
                   admin_user=current_user.email)
        
        # Execute strategy directly without purchase checks
        result = await trading_strategies_service.execute_strategy(
            function=function,
            symbol=symbol,
            parameters=parameters or {},
            user_id=str(current_user.id),
            simulation_mode=True
        )
        
        return {
            "success": True,
            "admin_testing": True,
            "function": function,
            "execution_result": result,
            "bypass_purchase_check": True,
            "timestamp": "admin_testing_mode"
        }
        
    except Exception as e:
        logger.error("Admin strategy testing failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Strategy testing failed: {str(e)}")


@router.get("/strategy/list-all")
async def admin_list_all_strategies(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Admin-only endpoint to list all available strategy functions.
    """
    
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Get all strategy functions via introspection
    all_functions = []
    
    for attr_name in dir(trading_strategies_service):
        attr = getattr(trading_strategies_service, attr_name)
        
        if (callable(attr) and 
            not attr_name.startswith('_') and 
            not attr_name in ['logger', 'log', 'async_init', 'cleanup'] and
            hasattr(attr, '__code__')):
            
            all_functions.append({
                "function_name": attr_name,
                "is_strategy": True,
                "testable": True
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
    functions: list[str],
    symbol: str = "BTC/USDT",
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Admin-only endpoint to test multiple strategies in bulk.
    """
    
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    results = []
    
    for function in functions:
        try:
            result = await trading_strategies_service.execute_strategy(
                function=function,
                symbol=symbol,
                parameters={},
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
        "total_tested": len(functions),
        "successful": successful,
        "success_rate": f"{successful/len(functions)*100:.1f}%",
        "results": results,
        "admin_testing": True
    }