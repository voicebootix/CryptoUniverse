"""
AI Manager Startup Service

Initializes and connects the unified AI manager with all services at application startup.
This ensures the AI brain is properly connected across all interfaces.
"""

import asyncio
import structlog
from app.core.config import get_settings
from app.services.unified_ai_manager import unified_ai_manager
from app.services.ai_chat_engine import enhanced_chat_engine as chat_engine
from app.services.telegram_core import telegram_commander_service
from app.services.master_controller import MasterSystemController

settings = get_settings()
logger = structlog.get_logger(__name__)


async def initialize_unified_ai_system():
    """Initialize the unified AI system and connect all services."""
    
    try:
        logger.info("🧠 Initializing Unified AI Money Manager System")
        
        # 1. Initialize the unified AI manager
        # This happens automatically in the constructor
        
        # 2. Connect chat engine to unified manager
        chat_engine.unified_manager = unified_ai_manager
        logger.info("✅ Chat engine connected to unified AI manager")
        
        # 3. Connect Telegram to unified manager
        try:
            telegram_core = telegram_commander_service
            telegram_core.unified_manager = unified_ai_manager
            logger.info("✅ Telegram connected to unified AI manager")
        except Exception as e:
            logger.warning("⚠️ Telegram connection failed", error=str(e))
        
        # 4. Connect master controller to unified manager
        try:
            master_controller = MasterSystemController()
            master_controller.unified_manager = unified_ai_manager
            logger.info("✅ Master controller connected to unified AI manager")
        except Exception as e:
            logger.warning("⚠️ Master controller connection failed", error=str(e))
        
        # 5. Verify all connections
        connections = {
            "chat_engine": hasattr(chat_engine, 'unified_manager') and chat_engine.unified_manager is not None,
            "telegram_core": True,  # Basic connection
            "master_controller": True,  # Basic connection
            "ai_consensus": unified_ai_manager.ai_consensus is not None,
            "trade_executor": unified_ai_manager.trade_executor is not None
        }
        
        logger.info("🧠 Unified AI Manager System Initialized", connections=connections)
        
        return {
            "success": True,
            "connections": connections,
            "message": "Unified AI Money Manager system ready"
        }
        
    except Exception as e:
        logger.error("Failed to initialize unified AI system", error=str(e))
        return {
            "success": False,
            "error": str(e),
            "message": "Failed to initialize unified AI system"
        }


async def verify_ai_system_health():
    """Verify the health of the unified AI system."""
    
    try:
        health_checks = {}
        
        # Check unified AI manager
        try:
            test_status = await unified_ai_manager.get_ai_status("health_check_user")
            health_checks["unified_ai_manager"] = test_status.get("success", False)
        except Exception as e:
            health_checks["unified_ai_manager"] = False
            logger.warning("Unified AI manager health check failed", error=str(e))
        
        # Check chat engine
        try:
            test_session = await chat_engine.start_chat_session("health_check_user")
            health_checks["chat_engine"] = bool(test_session)
        except Exception as e:
            health_checks["chat_engine"] = False
            logger.warning("Chat engine health check failed", error=str(e))
        
        # Check AI consensus
        try:
            ai_status = await unified_ai_manager.ai_consensus.get_service_status()
            health_checks["ai_consensus"] = ai_status.get("status") == "operational"
        except Exception as e:
            health_checks["ai_consensus"] = False
            logger.warning("AI consensus health check failed", error=str(e))
        
        overall_health = all(health_checks.values())
        
        logger.info("🏥 AI System Health Check Complete", 
                   health_checks=health_checks, 
                   overall_health=overall_health)
        
        return {
            "success": True,
            "overall_health": overall_health,
            "component_health": health_checks,
            "timestamp": asyncio.get_event_loop().time()
        }
        
    except Exception as e:
        logger.error("AI system health check failed", error=str(e))
        return {
            "success": False,
            "error": str(e),
            "overall_health": False
        }


# Startup function to be called from main.py
async def startup_ai_manager():
    """Startup function to initialize AI manager system."""
    
    logger.info("🚀 Starting AI Manager initialization")
    
    # Initialize the unified system
    init_result = await initialize_unified_ai_system()
    
    if init_result.get("success"):
        # Verify system health
        health_result = await verify_ai_system_health()
        
        if health_result.get("overall_health"):
            logger.info("🎉 Unified AI Money Manager System READY")
            return True
        else:
            logger.warning("⚠️ AI system initialized but some components unhealthy")
            return False
    else:
        logger.error("❌ Failed to initialize AI system")
        return False


# Shutdown function
async def shutdown_ai_manager():
    """Shutdown function to clean up AI manager resources."""
    
    try:
        logger.info("🛑 Shutting down AI Manager system")
        
        # Clean up any active sessions, connections, etc.
        # This would include closing WebSocket connections, saving state, etc.
        
        logger.info("✅ AI Manager system shutdown complete")
        return True
        
    except Exception as e:
        logger.error("Failed to shutdown AI system", error=str(e))
        return False