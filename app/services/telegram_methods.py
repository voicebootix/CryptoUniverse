"""
Telegram Service Additional Methods

Contains the remaining methods to complete the Telegram Commander Service:
- trade_notification
- system_status 
- voice_command
- setup_webhook
"""

import json
from datetime import datetime
from typing import Dict, Any, Optional


async def trade_notification(
    self,
    trade_data: str,
    notification_type: str = "execution",
    priority: str = "high",
    recipient: str = "owner"
) -> Dict[str, Any]:
    """Send trade execution notification via Telegram."""
    
    request_id = self._generate_request_id()
    self.logger.info("Sending trade notification", type=notification_type, request_id=request_id)
    
    try:
        # Parse trade data
        try:
            trade_info = json.loads(trade_data) if isinstance(trade_data, str) else trade_data
        except json.JSONDecodeError:
            return {
                "success": False,
                "error": "Invalid trade data format",
                "function": "trade_notification",
                "request_id": request_id
            }
        
        # Format trade notification message
        notification_message = self._format_trade_notification(trade_info, notification_type)
        
        # Send notification - resolve recipient to chat_id and send directly
        from app.services.telegram_commander import RecipientType

        try:
            recipient_type = RecipientType(recipient)
        except ValueError:
            return {
                "success": False,
                "error": f"Invalid recipient type: {recipient}",
                "function": "trade_notification",
                "request_id": request_id
            }

        chat_id = await self._get_chat_id_for_recipient(recipient_type)

        if not chat_id:
            return {
                "success": False,
                "error": f"No chat ID found for recipient: {recipient}",
                "function": "trade_notification",
                "request_id": request_id
            }

        result = await self.send_direct_message(
            chat_id=chat_id,
            message_content=notification_message,
            message_type="trade",
            priority=priority
        )
        
        return {
            "success": True,
            "function": "trade_notification",
            "request_id": request_id,
            "notification_sent": result.get("success", False),
            "trade_data": trade_info,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        self.logger.error("Trade notification failed", error=str(e), request_id=request_id, exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "function": "trade_notification",
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat()
        }


async def system_status(
    self,
    status_type: str = "health",
    include_metrics: bool = True,
    recipient: str = "owner"
) -> Dict[str, Any]:
    """Send system status update via Telegram."""
    
    request_id = self._generate_request_id()
    self.logger.info("Sending system status", type=status_type, request_id=request_id)
    
    try:
        # Gather system status from all services
        system_status_data = await self._gather_system_status(status_type, include_metrics)
        
        # Format status message
        status_message = self._format_system_status(system_status_data, status_type)
        
        # Determine priority based on status
        priority = "critical" if system_status_data.get("has_critical_issues") else "normal"
        
        # Send status update - resolve recipient to chat_id and send directly
        from app.services.telegram_commander import RecipientType

        try:
            recipient_type = RecipientType(recipient)
        except ValueError:
            return {
                "success": False,
                "error": f"Invalid recipient type: {recipient}",
                "function": "system_status",
                "request_id": request_id
            }

        chat_id = await self._get_chat_id_for_recipient(recipient_type)

        if not chat_id:
            return {
                "success": False,
                "error": f"No chat ID found for recipient: {recipient}",
                "function": "system_status",
                "request_id": request_id
            }

        result = await self.send_direct_message(
            chat_id=chat_id,
            message_content=status_message,
            message_type="system",
            priority=priority
        )
        
        return {
            "success": True,
            "function": "system_status",
            "request_id": request_id,
            "status_sent": result.get("success", False),
            "system_status": system_status_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        self.logger.error("System status failed", error=str(e), request_id=request_id, exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "function": "system_status",
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat()
        }


async def voice_command(
    self,
    voice_data: str,
    command_type: str = "analysis",
    user_id: str = None
) -> Dict[str, Any]:
    """Process voice command and send response."""
    
    request_id = self._generate_request_id()
    self.logger.info("Processing voice command", type=command_type, request_id=request_id)
    
    try:
        # Parse voice command data
        try:
            voice_info = json.loads(voice_data) if isinstance(voice_data, str) else voice_data
        except json.JSONDecodeError:
            voice_info = {"text": voice_data}
        
        # Extract text from voice data
        voice_text = voice_info.get("text", "")
        if not voice_text:
            return {
                "success": False,
                "error": "No text found in voice data",
                "function": "voice_command",
                "request_id": request_id
            }
        
        # Process voice command through AI
        ai_request = {
            "query": voice_text,
            "context": {
                "input_type": "voice",
                "command_type": command_type,
                "user_id": user_id,
                "system_context": "voice_crypto_assistant"
            }
        }
        
        # Get AI response
        from app.services.ai_consensus import ai_consensus_service
        ai_response = await ai_consensus_service.analyze_opportunity(
            json.dumps(ai_request),
            confidence_threshold=70.0,
            ai_models="cost_optimized",
            user_id=user_id
        )
        
        # Format voice response
        if ai_response.get("success"):
            response_text = self._format_voice_response(ai_response, voice_text)
        else:
            response_text = f"🎤 I heard: \"{voice_text}\"\n\n🤖 I'm having trouble processing your voice command right now. Please try again or type your request."
        
        # Send voice response
        chat_id = await self._get_chat_id_for_user(user_id) if user_id else await self._get_chat_id_for_recipient("owner")
        if chat_id:
            result = await self.telegram_api.send_message(
                chat_id=chat_id,
                text=response_text,
                priority="normal"
            )
        else:
            result = {"success": False, "error": "No chat ID available"}
        
        return {
            "success": True,
            "function": "voice_command",
            "request_id": request_id,
            "voice_text": voice_text,
            "response_sent": result.get("success", False),
            "ai_response": ai_response.get("success", False),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        self.logger.error("Voice command failed", error=str(e), request_id=request_id, exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "function": "voice_command",
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat()
        }


async def setup_webhook(
    self,
    webhook_url: str,
    secret_token: Optional[str] = None,
    verify_ssl: bool = True
) -> Dict[str, Any]:
    """Setup Telegram webhook for real-time message processing."""
    
    request_id = self._generate_request_id()
    self.logger.info("Setting up webhook", url=webhook_url, request_id=request_id)
    
    try:
        # Validate webhook URL
        if not webhook_url.startswith('https://') and verify_ssl:
            return {
                "success": False,
                "error": "Webhook URL must use HTTPS",
                "function": "setup_webhook",
                "request_id": request_id
            }
        
        # Setup webhook via Telegram API
        webhook_result = await self.telegram_api.set_webhook(
            webhook_url=webhook_url,
            secret_token=secret_token
        )
        
        if webhook_result.get("success"):
            # Store webhook configuration
            webhook_config = {
                "url": webhook_url,
                "secret_token": secret_token,
                "setup_time": datetime.utcnow().isoformat(),
                "verify_ssl": verify_ssl
            }
            
            # In production, would store in database
            self.webhook_config = webhook_config
            
            return {
                "success": True,
                "function": "setup_webhook",
                "request_id": request_id,
                "webhook_url": webhook_url,
                "webhook_setup": True,
                "configuration": webhook_config,
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            return {
                "success": False,
                "error": webhook_result.get("error", "Webhook setup failed"),
                "function": "setup_webhook",
                "request_id": request_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        
    except Exception as e:
        self.logger.error("Webhook setup failed", error=str(e), request_id=request_id, exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "function": "setup_webhook",
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat()
        }


# Helper methods for formatting and processing

def _format_trade_notification(self, trade_info: Dict[str, Any], notification_type: str) -> str:
    """Format trade notification message."""
    
    symbol = trade_info.get("symbol", "UNKNOWN")
    side = trade_info.get("side", "").upper()
    quantity = trade_info.get("quantity", 0)
    price = trade_info.get("price", 0)
    status = trade_info.get("status", "UNKNOWN")
    exchange = trade_info.get("exchange", "")
    
    side_emoji = "🟢" if side == "BUY" else "🔴" if side == "SELL" else "💱"
    status_emoji = "✅" if status == "FILLED" else "⏳" if status == "PENDING" else "❌"
    
    if notification_type == "execution":
        message_parts = [
            f"{side_emoji} **Trade Executed** {status_emoji}",
            f"**Symbol:** {symbol}",
            f"**Side:** {side}",
            f"**Quantity:** {quantity}",
            f"**Price:** ${price:,.2f}" if price > 0 else "**Price:** Market",
            f"**Status:** {status}",
        ]
        
        if exchange:
            message_parts.append(f"**Exchange:** {exchange}")
        
        if trade_info.get("total_value"):
            message_parts.append(f"**Total:** ${trade_info['total_value']:,.2f}")
        
        message_parts.append(f"\n⏰ {datetime.utcnow().strftime('%H:%M UTC')}")
        
        return "\n".join(message_parts)
    
    elif notification_type == "alert":
        return f"{side_emoji} **Trade Alert**\n\n{symbol} {side} signal detected\nQuantity: {quantity}\nRecommended action required"
    
    else:
        return f"{side_emoji} **{notification_type.title()} Notification**\n\n{symbol}: {side} {quantity} @ ${price:,.2f}"


async def _gather_system_status(self, status_type: str, include_metrics: bool) -> Dict[str, Any]:
    """Gather system status from all services."""
    
    system_status = {
        "overall_status": "HEALTHY",
        "services": {},
        "has_critical_issues": False,
        "metrics": {} if include_metrics else None
    }
    
    # Check all service health
    services_to_check = [
        ("market_analysis", "app.services.market_analysis", "market_analysis_service"),
        ("trade_execution", "app.services.trade_execution", "trade_execution_service"),
        ("trading_strategies", "app.services.trading_strategies", "trading_strategies_service"),
        ("ai_consensus", "app.services.ai_consensus", "ai_consensus_service"),
        ("portfolio_risk", "app.services.portfolio_risk", "portfolio_risk_service")
    ]
    
    for service_name, module_name, service_instance in services_to_check:
        try:
            # Import and check service health
            import importlib
            module = importlib.import_module(module_name)
            service = getattr(module, service_instance)
            
            health_result = await service.health_check()
            
            service_status = "HEALTHY" if health_result.get("healthy") or health_result.get("status") == "HEALTHY" else "UNHEALTHY"
            
            system_status["services"][service_name] = {
                "status": service_status,
                "last_check": datetime.utcnow().isoformat(),
                "details": health_result
            }
            
            if service_status == "UNHEALTHY":
                system_status["has_critical_issues"] = True
                system_status["overall_status"] = "DEGRADED"
                
        except Exception as e:
            system_status["services"][service_name] = {
                "status": "ERROR",
                "error": str(e),
                "last_check": datetime.utcnow().isoformat()
            }
            system_status["has_critical_issues"] = True
            system_status["overall_status"] = "DEGRADED"
    
    # Add system metrics if requested
    if include_metrics:
        # Calculate real system metrics
        import psutil
        import os
        
        # Calculate actual uptime from process start time
        process = psutil.Process(os.getpid())
        uptime_seconds = time.time() - process.create_time()
        uptime_hours = uptime_seconds / 3600
        uptime_str = f"{uptime_hours:.1f}h" if uptime_hours < 24 else f"{uptime_hours/24:.1f}d"
        
        # Get actual memory usage
        memory_info = process.memory_info()
        memory_usage_mb = memory_info.rss / 1024 / 1024  # Convert to MB
        
        # Get average response time from recent requests (if available)
        avg_response_time = getattr(self, '_avg_response_time', 0)
        response_time_str = f"{avg_response_time:.2f}ms" if avg_response_time > 0 else "<1ms"
        
        system_status["metrics"] = {
            "telegram_messages": self.service_metrics.get("total_messages", 0),
            "alerts_sent": self.service_metrics.get("alerts_sent", 0),
            "active_users": self.service_metrics.get("active_users", 0),
            "uptime": uptime_str,
            "memory_usage": f"{memory_usage_mb:.1f}MB",
            "response_time": response_time_str
        }
    
    return system_status


def _format_system_status(self, status_data: Dict[str, Any], status_type: str) -> str:
    """Format system status message."""
    
    overall_status = status_data.get("overall_status", "UNKNOWN")
    services = status_data.get("services", {})
    
    # Status emoji
    status_emoji = {
        "HEALTHY": "🟢",
        "DEGRADED": "🟡", 
        "UNHEALTHY": "🔴",
        "ERROR": "❌"
    }.get(overall_status, "❓")
    
    message_parts = [
        f"{status_emoji} **System Status: {overall_status}**",
        f"**Time:** {datetime.utcnow().strftime('%H:%M UTC')}",
        ""
    ]
    
    if status_type == "health":
        # Add service status
        message_parts.append("**Services:**")
        for service_name, service_info in services.items():
            service_status = service_info.get("status", "UNKNOWN")
            service_emoji = "✅" if service_status == "HEALTHY" else "⚠️" if service_status == "DEGRADED" else "❌"
            message_parts.append(f"{service_emoji} {service_name.replace('_', ' ').title()}: {service_status}")
        
        # Add metrics if available
        metrics = status_data.get("metrics")
        if metrics:
            message_parts.append("")
            message_parts.append("**Metrics:**")
            message_parts.append(f"📨 Messages: {metrics.get('telegram_messages', 0)}")
            message_parts.append(f"🚨 Alerts: {metrics.get('alerts_sent', 0)}")
            message_parts.append(f"👥 Users: {metrics.get('active_users', 0)}")
    
    elif status_type == "brief":
        service_count = len(services)
        healthy_count = sum(1 for s in services.values() if s.get("status") == "HEALTHY")
        message_parts.append(f"**Services:** {healthy_count}/{service_count} healthy")
    
    return "\n".join(message_parts)


def _format_voice_response(self, ai_response: Dict[str, Any], voice_text: str) -> str:
    """Format AI response for voice command."""
    
    response_parts = [
        f"🎤 **Voice Command Processed**",
        f"**You said:** \"{voice_text}\"",
        ""
    ]
    
    # Extract AI analysis
    opportunity_analysis = ai_response.get("opportunity_analysis", {})
    
    if opportunity_analysis:
        recommendation = opportunity_analysis.get("recommendation", "")
        if recommendation:
            response_parts.append(f"🤖 **AI Recommendation:** {recommendation}")
        
        consensus_score = opportunity_analysis.get("consensus_score", 0)
        if consensus_score > 0:
            response_parts.append(f"📊 **Confidence:** {consensus_score:.1f}%")
        
        reasoning = opportunity_analysis.get("reasoning", "")
        if reasoning:
            # Truncate reasoning for voice response
            short_reasoning = reasoning[:200] + "..." if len(reasoning) > 200 else reasoning
            response_parts.append(f"\n💡 {short_reasoning}")
    else:
        response_parts.append("🤖 **Response:** Command processed successfully!")
    
    response_parts.append(f"\n🎙️ You can ask follow-up questions by voice or text!")
    
    return "\n".join(response_parts)


async def _get_chat_id_for_user(self, user_id: str) -> Optional[str]:
    """Get chat ID for specific user - DYNAMIC USER RESOLUTION."""
    try:
        # Real production implementation - get from user database
        from app.core.database import AsyncSessionLocal
        
        async with AsyncSessionLocal() as db:
        
        # Query user's telegram chat ID from database
        user_chat = await db.execute(
            "SELECT telegram_chat_id FROM users WHERE id = %s AND telegram_chat_id IS NOT NULL",
            (user_id,)
        )
        result = user_chat.fetchone()
        
        if result:
            return result[0]
        
        # If no chat ID found, log warning and return None
        self.logger.warning("No Telegram chat ID found for user", user_id=user_id)
        return None
        
    except Exception as e:
        self.logger.error("Failed to resolve user chat ID", user_id=user_id, error=str(e))
        return None
