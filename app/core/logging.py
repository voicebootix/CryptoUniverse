"""
Logging configuration for structured logging with multiple outputs.

Configures structured JSON logging for production and readable logging
for development environments.
"""

import logging
import sys
from typing import Any, Dict, List, Optional

import structlog
from structlog.processors import JSONRenderer
from structlog.stdlib import add_log_level, add_logger_name

import logging.handlers

from app.core.config import get_settings

settings = get_settings()


def configure_logging(log_level: str = "INFO", environment: str = "development") -> None:
    """
    Configure structured logging for the application.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        environment: Environment name (development, production, etc.)
    """
    # Set logging level
    logging_level = getattr(logging, log_level.upper(), logging.INFO)
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging_level,
    )
    
    # Configure processors based on environment
    processors: List[Any] = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]
    
    # Add environment-specific formatting
    if environment == "development":
        processors.append(structlog.dev.ConsoleRenderer(colors=True))
    else:
        processors.extend([
            structlog.processors.dict_tracebacks,
            JSONRenderer()
        ])
    
    # Configure structlog
    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Silence noisy loggers
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("databases").setLevel(logging.WARNING)
    logging.getLogger("asyncpg").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("ccxt").setLevel(logging.WARNING)

    # Production log rotation
    if settings.ENV == 'production':
        rotating_handler = logging.handlers.RotatingFileHandler(
            'cryptouniverse.log',
            maxBytes=100 * 1024 * 1024,  # 100MB
            backupCount=5
        )
        rotating_handler.setLevel(logging.WARNING)
        rotating_handler.setFormatter(structlog.stdlib.ProcessorFormatter(
            processor=structlog.dev.ConsoleRenderer()
        ))
        logger.addHandler(rotating_handler)
        
        # Set root level to WARNING
        logging.getLogger().setLevel(logging.WARNING)


class LoggerMixin:
    """Mixin class to add structured logging to any class."""
    
    @property
    def logger(self) -> structlog.BoundLogger:
        """Get a logger instance for this class."""
        return structlog.get_logger(self.__class__.__name__)


class TradeLogger:
    """Specialized logger for trading operations."""
    
    def __init__(self):
        self.logger = structlog.get_logger("trading")
    
    def log_trade_executed(
        self,
        user_id: str,
        symbol: str,
        action: str,
        quantity: float,
        price: float,
        exchange: str,
        order_id: str,
        **kwargs
    ) -> None:
        """Log successful trade execution."""
        self.logger.info(
            "Trade executed successfully",
            user_id=user_id,
            symbol=symbol,
            action=action,
            quantity=quantity,
            price=price,
            exchange=exchange,
            order_id=order_id,
            value_usd=quantity * price,
            **kwargs
        )
    
    def log_trade_failed(
        self,
        user_id: str,
        symbol: str,
        action: str,
        quantity: float,
        exchange: str,
        error: str,
        **kwargs
    ) -> None:
        """Log failed trade execution."""
        self.logger.error(
            "Trade execution failed",
            user_id=user_id,
            symbol=symbol,
            action=action,
            quantity=quantity,
            exchange=exchange,
            error=error,
            **kwargs
        )
    
    def log_strategy_signal(
        self,
        strategy_id: str,
        symbol: str,
        signal: str,
        confidence: float,
        reason: str,
        **kwargs
    ) -> None:
        """Log strategy signal generation."""
        self.logger.info(
            "Strategy signal generated",
            strategy_id=strategy_id,
            symbol=symbol,
            signal=signal,
            confidence=confidence,
            reason=reason,
            **kwargs
        )
    
    def log_risk_limit_breach(
        self,
        user_id: str,
        limit_type: str,
        current_value: float,
        limit_value: float,
        action_taken: str,
        **kwargs
    ) -> None:
        """Log risk limit breach."""
        self.logger.warning(
            "Risk limit breached",
            user_id=user_id,
            limit_type=limit_type,
            current_value=current_value,
            limit_value=limit_value,
            action_taken=action_taken,
            **kwargs
        )


class SecurityLogger:
    """Specialized logger for security events."""
    
    def __init__(self):
        self.logger = structlog.get_logger("security")
    
    def log_login_attempt(
        self,
        user_id: Optional[str],
        email: str,
        success: bool,
        ip_address: str,
        user_agent: str,
        **kwargs
    ) -> None:
        """Log login attempt."""
        self.logger.info(
            "Login attempt",
            user_id=user_id,
            email=email,
            success=success,
            ip_address=ip_address,
            user_agent=user_agent,
            **kwargs
        )
    
    def log_api_key_usage(
        self,
        user_id: str,
        exchange: str,
        operation: str,
        success: bool,
        **kwargs
    ) -> None:
        """Log API key usage."""
        self.logger.info(
            "API key used",
            user_id=user_id,
            exchange=exchange,
            operation=operation,
            success=success,
            **kwargs
        )
    
    def log_permission_denied(
        self,
        user_id: str,
        resource: str,
        action: str,
        reason: str,
        **kwargs
    ) -> None:
        """Log permission denied events."""
        self.logger.warning(
            "Permission denied",
            user_id=user_id,
            resource=resource,
            action=action,
            reason=reason,
            **kwargs
        )
    
    def log_security_incident(
        self,
        incident_type: str,
        severity: str,
        description: str,
        user_id: Optional[str] = None,
        **kwargs
    ) -> None:
        """Log security incident."""
        self.logger.error(
            "Security incident",
            incident_type=incident_type,
            severity=severity,
            description=description,
            user_id=user_id,
            **kwargs
        )


class BusinessLogger:
    """Specialized logger for business events."""
    
    def __init__(self):
        self.logger = structlog.get_logger("business")
    
    def log_user_registration(
        self,
        user_id: str,
        email: str,
        subscription_tier: str,
        referral_code: Optional[str] = None,
        **kwargs
    ) -> None:
        """Log user registration."""
        self.logger.info(
            "User registered",
            user_id=user_id,
            email=email,
            subscription_tier=subscription_tier,
            referral_code=referral_code,
            **kwargs
        )
    
    def log_subscription_change(
        self,
        user_id: str,
        old_tier: str,
        new_tier: str,
        reason: str,
        **kwargs
    ) -> None:
        """Log subscription tier change."""
        self.logger.info(
            "Subscription changed",
            user_id=user_id,
            old_tier=old_tier,
            new_tier=new_tier,
            reason=reason,
            **kwargs
        )
    
    def log_credit_transaction(
        self,
        user_id: str,
        transaction_type: str,
        amount: int,
        balance_before: int,
        balance_after: int,
        reason: str,
        **kwargs
    ) -> None:
        """Log credit transactions."""
        self.logger.info(
            "Credit transaction",
            user_id=user_id,
            transaction_type=transaction_type,
            amount=amount,
            balance_before=balance_before,
            balance_after=balance_after,
            reason=reason,
            **kwargs
        )
    
    def log_revenue_event(
        self,
        revenue_type: str,
        amount_usd: float,
        user_id: Optional[str] = None,
        strategy_id: Optional[str] = None,
        **kwargs
    ) -> None:
        """Log revenue-generating events."""
        self.logger.info(
            "Revenue event",
            revenue_type=revenue_type,
            amount_usd=amount_usd,
            user_id=user_id,
            strategy_id=strategy_id,
            **kwargs
        )


# Global logger instances
trade_logger = TradeLogger()
security_logger = SecurityLogger()
business_logger = BusinessLogger()


# Audit logging decorator
def audit_log(event_type: str, **metadata):
    """
    Decorator for audit logging.
    
    Args:
        event_type: Type of event being audited
        **metadata: Additional metadata to log
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            logger = structlog.get_logger("audit")
            
            try:
                result = await func(*args, **kwargs)
                logger.info(
                    "Audit event",
                    event_type=event_type,
                    function=func.__name__,
                    success=True,
                    **metadata
                )
                return result
            except Exception as e:
                logger.error(
                    "Audit event failed",
                    event_type=event_type,
                    function=func.__name__,
                    success=False,
                    error=str(e),
                    **metadata
                )
                raise
        
        return wrapper
    return decorator
