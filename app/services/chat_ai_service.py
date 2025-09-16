"""
Chat AI Service - Direct ChatGPT Integration for Natural Conversations

This service provides direct access to ChatGPT for conversational AI,
separate from the AI Consensus service which is ONLY for trade validation.

NO MOCKS, NO PLACEHOLDERS - Real ChatGPT integration only.
"""

import asyncio
import json
import time
from typing import Dict, List, Optional, Any, AsyncGenerator
from datetime import datetime
import httpx
import structlog

from app.core.config import get_settings
from app.core.logging import LoggerMixin

settings = get_settings()
logger = structlog.get_logger(__name__)


class ChatAIService(LoggerMixin):
    """
    Direct ChatGPT integration for natural language conversations.
    
    This is NOT for trade validation - that's AI Consensus.
    This is ONLY for natural, fast, conversational responses.
    """
    
    def __init__(self):
        """Initialize ChatGPT service with real configuration."""
        self.api_key = settings.OPENAI_API_KEY
        self.model = settings.CHAT_AI_MODEL if hasattr(settings, 'CHAT_AI_MODEL') else "gpt-4"
        self.temperature = float(settings.CHAT_AI_TEMPERATURE) if hasattr(settings, 'CHAT_AI_TEMPERATURE') else 0.7
        self.timeout = int(settings.CHAT_AI_TIMEOUT) if hasattr(settings, 'CHAT_AI_TIMEOUT') else 30
        
        # API configuration
        self.api_url = "https://api.openai.com/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Performance tracking
        self.request_count = 0
        self.total_tokens = 0
        self.total_cost = 0.0
        
        self.logger.info(
            "ChatAI Service initialized",
            model=self.model,
            temperature=self.temperature,
            timeout=self.timeout
        )
    
    async def generate_response(
        self,
        prompt: str,
        system_message: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        user_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate a conversational response using ChatGPT.
        
        Args:
            prompt: The user's message or prompt
            system_message: Optional system context
            temperature: Override default temperature
            max_tokens: Maximum response tokens
            user_context: Additional context for personalization
            
        Returns:
            Dict containing response and metadata
        """
        start_time = time.time()
        
        try:
            # Build messages
            messages = []
            if system_message:
                messages.append({"role": "system", "content": system_message})
            messages.append({"role": "user", "content": prompt})
            
            # Build request
            request_data = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature or self.temperature,
                "stream": False
            }
            
            if max_tokens:
                request_data["max_tokens"] = max_tokens
            
            # Make API call with timeout
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.api_url,
                    headers=self.headers,
                    json=request_data
                )
                
                response.raise_for_status()
                result = response.json()
            
            # Extract response
            if result.get("choices") and len(result["choices"]) > 0:
                content = result["choices"][0]["message"]["content"]
                
                # Track usage
                usage = result.get("usage", {})
                self.request_count += 1
                self.total_tokens += usage.get("total_tokens", 0)
                
                # Calculate cost (GPT-4 pricing as of 2024)
                prompt_tokens = usage.get("prompt_tokens", 0)
                completion_tokens = usage.get("completion_tokens", 0)
                
                if self.model.startswith("gpt-4"):
                    # GPT-4 pricing: $0.03 per 1K prompt tokens, $0.06 per 1K completion tokens
                    cost = (prompt_tokens * 0.03 + completion_tokens * 0.06) / 1000
                else:
                    # GPT-3.5-turbo pricing: $0.001 per 1K prompt tokens, $0.002 per 1K completion tokens
                    cost = (prompt_tokens * 0.001 + completion_tokens * 0.002) / 1000
                
                self.total_cost += cost
                
                elapsed_time = time.time() - start_time
                
                self.logger.info(
                    "ChatGPT response generated",
                    elapsed_time=f"{elapsed_time:.2f}s",
                    tokens=usage.get("total_tokens", 0),
                    cost=f"${cost:.4f}",
                    model=self.model
                )
                
                return {
                    "success": True,
                    "content": content,
                    "usage": usage,
                    "cost": cost,
                    "elapsed_time": elapsed_time,
                    "model": self.model
                }
            else:
                self.logger.error("No response from ChatGPT", result=result)
                return {
                    "success": False,
                    "error": "No response generated",
                    "elapsed_time": time.time() - start_time
                }
                
        except httpx.TimeoutException:
            elapsed_time = time.time() - start_time
            self.logger.error(
                "ChatGPT request timed out",
                timeout=self.timeout,
                elapsed_time=elapsed_time
            )
            return {
                "success": False,
                "error": f"Request timed out after {self.timeout} seconds",
                "elapsed_time": elapsed_time
            }
            
        except httpx.HTTPStatusError as e:
            elapsed_time = time.time() - start_time
            self.logger.error(
                "ChatGPT API error",
                status_code=e.response.status_code,
                error=str(e),
                elapsed_time=elapsed_time
            )
            
            # Parse error message
            try:
                error_data = e.response.json()
                error_message = error_data.get("error", {}).get("message", str(e))
            except:
                error_message = str(e)
            
            return {
                "success": False,
                "error": error_message,
                "status_code": e.response.status_code,
                "elapsed_time": elapsed_time
            }
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            self.logger.exception(
                "Unexpected error in ChatGPT service",
                error=str(e),
                elapsed_time=elapsed_time
            )
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}",
                "elapsed_time": elapsed_time
            }
    
    async def stream_response(
        self,
        prompt: str,
        system_message: Optional[str] = None,
        temperature: Optional[float] = None,
        user_context: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[str, None]:
        """
        Stream a conversational response using ChatGPT with Server-Sent Events.
        
        Yields response chunks in real-time for a natural conversation feel.
        """
        start_time = time.time()
        
        try:
            # Build messages
            messages = []
            if system_message:
                messages.append({"role": "system", "content": system_message})
            messages.append({"role": "user", "content": prompt})
            
            # Build request for streaming
            request_data = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature or self.temperature,
                "stream": True
            }
            
            # Stream API call
            async with httpx.AsyncClient(timeout=httpx.Timeout(60.0, read=5.0)) as client:
                async with client.stream(
                    "POST",
                    self.api_url,
                    headers=self.headers,
                    json=request_data
                ) as response:
                    response.raise_for_status()
                    
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data = line[6:]  # Remove "data: " prefix
                            
                            if data == "[DONE]":
                                break
                            
                            try:
                                chunk = json.loads(data)
                                if chunk.get("choices") and len(chunk["choices"]) > 0:
                                    delta = chunk["choices"][0].get("delta", {})
                                    if "content" in delta:
                                        yield delta["content"]
                            except json.JSONDecodeError:
                                continue
            
            elapsed_time = time.time() - start_time
            self.logger.info(
                "ChatGPT streaming completed",
                elapsed_time=f"{elapsed_time:.2f}s",
                model=self.model
            )
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            self.logger.exception(
                "Error in ChatGPT streaming",
                error=str(e),
                elapsed_time=elapsed_time
            )
            yield f"\n\n[Error: {str(e)}]"
    
    async def analyze_intent(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Quick intent analysis for routing conversations.
        
        This is a fast, focused call just for understanding intent,
        not for generating full responses.
        """
        prompt = f"""Analyze this user message for a cryptocurrency trading platform.

User Message: "{message}"

Context: {json.dumps(context or {}, indent=2)}

Return a JSON object with:
1. primary_intent: The main intent (portfolio, trading, strategy, market, risk, help, etc.)
2. entities: List of entities mentioned (coins, amounts, actions, etc.)
3. sentiment: User sentiment (positive, negative, neutral, urgent)
4. complexity: Query complexity (simple, moderate, complex)
5. requires_action: Boolean if user wants to perform an action
6. confidence: Your confidence in this analysis (0.0-1.0)

Respond ONLY with valid JSON."""

        response = await self.generate_response(
            prompt=prompt,
            temperature=0.3,  # Lower temperature for more consistent analysis
            max_tokens=500
        )
        
        if response["success"]:
            try:
                # Parse JSON response
                content = response["content"]
                # Handle code blocks if present
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()
                
                intent_data = json.loads(content)
                return {
                    "success": True,
                    "intent_data": intent_data,
                    "elapsed_time": response["elapsed_time"]
                }
            except json.JSONDecodeError as e:
                self.logger.error("Failed to parse intent analysis", error=str(e))
                return {
                    "success": False,
                    "error": "Failed to parse intent analysis",
                    "raw_response": response["content"]
                }
        else:
            return response
    
    async def get_service_status(self) -> Dict[str, Any]:
        """Get current service status and statistics."""
        return {
            "service": "ChatAI",
            "status": "operational",
            "model": self.model,
            "requests_total": self.request_count,
            "tokens_used": self.total_tokens,
            "total_cost": f"${self.total_cost:.2f}",
            "average_cost_per_request": f"${self.total_cost / max(1, self.request_count):.4f}",
            "configuration": {
                "model": self.model,
                "temperature": self.temperature,
                "timeout": self.timeout
            }
        }
    
    async def health_check(self) -> bool:
        """
        Perform a health check on the ChatGPT service.
        
        Returns True if service is operational.
        """
        try:
            response = await self.generate_response(
                prompt="Hello",
                max_tokens=10
            )
            return response["success"]
        except:
            return False


# Global instance
chat_ai_service = ChatAIService()