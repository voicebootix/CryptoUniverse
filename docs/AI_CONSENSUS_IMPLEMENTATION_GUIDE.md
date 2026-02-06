# AI Consensus Implementation Guide — Source Code Reference

> **Purpose**: This guide explains exactly how the AI consensus system works for opportunity scoring and decision-making, with every point backed by the actual production code from this repository. No documentation assumptions — only code-verified facts.

---

## Table of Contents

1. [System Architecture Overview](#1-system-architecture-overview)
2. [AI Model Configuration & Providers](#2-ai-model-configuration--providers)
3. [Circuit Breaker Pattern](#3-circuit-breaker-pattern)
4. [Querying AI Models (GPT-4, Claude, Gemini)](#4-querying-ai-models-gpt-4-claude-gemini)
5. [Confidence Extraction from AI Responses](#5-confidence-extraction-from-ai-responses)
6. [Reasoning Extraction from AI Responses](#6-reasoning-extraction-from-ai-responses)
7. [Weighted Consensus Scoring](#7-weighted-consensus-scoring)
8. [Recommendation Extraction & Consensus Voting](#8-recommendation-extraction--consensus-voting)
9. [Opportunity Analysis Flow](#9-opportunity-analysis-flow)
10. [Enhanced Scoring & Execution Priority](#10-enhanced-scoring--execution-priority)
11. [Trade Validation via AI Consensus](#11-trade-validation-via-ai-consensus)
12. [Risk Assessment Scoring](#12-risk-assessment-scoring)
13. [Final Consensus Decision & Execution Readiness](#13-final-consensus-decision--execution-readiness)
14. [Opportunity Ranking (Conversational Layer)](#14-opportunity-ranking-conversational-layer)
15. [Master Controller 5-Phase Pipeline Integration](#15-master-controller-5-phase-pipeline-integration)
16. [Unified AI Manager Integration](#16-unified-ai-manager-integration)
17. [API Endpoints & Request/Response Models](#17-api-endpoints--requestresponse-models)
18. [Cost Tracking](#18-cost-tracking)
19. [Performance Metrics Tracking](#19-performance-metrics-tracking)
20. [Health Check & Service Status](#20-health-check--service-status)

---

## 1. System Architecture Overview

The AI consensus system is built from three core layers:

| Layer | File | Class |
|-------|------|-------|
| Type Definitions | `app/services/ai_consensus_types.py` | `AIModelProvider`, `CircuitBreakerState`, `AIModelResponse` |
| Core Engine | `app/services/ai_consensus_core.py` | `AIModelConnector`, `ConsensusEngine`, `AIConsensusService` |
| API Exposure | `app/api/v1/endpoints/ai_consensus.py` | FastAPI router with 6 endpoints |
| Re-export | `app/services/ai_consensus.py` | Re-exports from core |

**Service singleton initialization** (`app/services/ai_consensus_core.py`, line 1367-1374):
```python
# Global service instance
ai_consensus_service = AIConsensusService()


# FastAPI dependency
async def get_ai_consensus_service() -> AIConsensusService:
    """Dependency injection for FastAPI."""
    return ai_consensus_service
```

The service is composed of two internal components (`app/services/ai_consensus_core.py`, lines 702-710):
```python
class AIConsensusService(LoggerMixin):
    """COMPLETE AI Consensus Service - MIGRATED FROM FLOWISE"""
    
    def __init__(self):
        self.ai_connector = AIModelConnector()
        self.consensus_engine = ConsensusEngine(self.ai_connector)
        self.request_cache = {}
        self.performance_metrics = {
            "total_requests": 0,
            "successful_consensus": 0,
            "average_confidence": 0.0
        }
```

---

## 2. AI Model Configuration & Providers

Three AI providers are used. Each has a `weight_factor`, `reliability_score`, and `specialty` that directly influence consensus scoring.

**Provider enum** (`app/services/ai_consensus_types.py`, lines 13-17):
```python
class AIModelProvider(str, Enum):
    """AI model provider enumeration."""
    GPT4 = "gpt4"
    CLAUDE = "claude"
    GEMINI = "gemini"
```

**Model configurations** (`app/services/ai_consensus_core.py`, lines 32-69):
```python
class AIModelConfiguration:
    """AI model configurations for production use."""
    
    GPT4_CONFIG = {
        "provider": "openai",
        "model": "gpt-4-turbo-preview", 
        "api_url": "https://api.openai.com/v1/chat/completions",
        "max_tokens": 2000,
        "temperature": 0.3,
        "cost_per_token": 0.00001,
        "reliability_score": 0.95,
        "specialty": "analytical_reasoning",
        "weight_factor": 1.0
    }
    
    CLAUDE_CONFIG = {
        "provider": "anthropic",
        "model": "claude-3-opus-20240229",
        "api_url": "https://api.anthropic.com/v1/messages", 
        "max_tokens": 2000,
        "temperature": 0.3,
        "cost_per_token": 0.000015,
        "reliability_score": 0.93,
        "specialty": "risk_analysis",
        "weight_factor": 1.1
    }
    
    GEMINI_CONFIG = {
        "provider": "google",
        "model": "gemini-1.5-pro",
        "api_url": "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent",
        "max_tokens": 2000,
        "temperature": 0.3,
        "cost_per_token": 0.0000025,
        "reliability_score": 0.90,
        "specialty": "market_analysis",
        "weight_factor": 0.9
    }
```

**Key insight**: Claude has the highest `weight_factor` (1.1) — it's weighted more heavily in consensus. GPT-4 is the baseline (1.0). Gemini is slightly discounted (0.9) but is the cheapest.

**Model selection strategies** (`app/services/ai_consensus_core.py`, lines 82-101):
```python
class ProductionConfiguration:
    """Production-grade configuration for AI Consensus Service."""
    
    MAX_RETRIES = 3
    INITIAL_RETRY_DELAY = 1.0
    REQUEST_TIMEOUT = 30.0
    CIRCUIT_BREAKER_THRESHOLD = 5
    CIRCUIT_BREAKER_RESET_TIME = 300
    
    CONFIDENCE_THRESHOLDS = {
        "low": 70,
        "medium": 75,
        "high": 80,
        "very_high": 85
    }
    
    MODEL_STRATEGIES = {
        "all": [AIModelProvider.GPT4, AIModelProvider.CLAUDE, AIModelProvider.GEMINI],
        "gpt4_claude": [AIModelProvider.GPT4, AIModelProvider.CLAUDE],
        "cost_optimized": [AIModelProvider.GEMINI, AIModelProvider.GPT4]
    }
```

---

## 3. Circuit Breaker Pattern

Each AI provider has an independent circuit breaker that opens after 5 consecutive failures and auto-resets after 300 seconds.

**Circuit breaker state** (`app/services/ai_consensus_types.py`, lines 30-36):
```python
@dataclass
class CircuitBreakerState:
    """Circuit breaker state for AI model."""
    failures: int = 0
    last_failure: Optional[datetime] = None
    is_open: bool = False
    success_count: int = 0
```

**Initialization per provider** (`app/services/ai_consensus_core.py`, lines 108-113):
```python
class AIModelConnector(LoggerMixin):
    def __init__(self):
        self.circuit_breakers = {
            AIModelProvider.GPT4: CircuitBreakerState(),
            AIModelProvider.CLAUDE: CircuitBreakerState(),
            AIModelProvider.GEMINI: CircuitBreakerState()
        }
```

**Check before querying** (`app/services/ai_consensus_core.py`, lines 485-499):
```python
def _is_circuit_breaker_open(self, provider: AIModelProvider) -> bool:
    """Check if circuit breaker is open for provider."""
    breaker = self.circuit_breakers[provider]
    
    if not breaker.is_open:
        return False
    
    if breaker.last_failure:
        time_since_failure = (datetime.utcnow() - breaker.last_failure).total_seconds()
        if time_since_failure > ProductionConfiguration.CIRCUIT_BREAKER_RESET_TIME:
            breaker.is_open = False
            breaker.failures = 0
            return False
    
    return True
```

**Failure recording and tripping** (`app/services/ai_consensus_core.py`, lines 510-518):
```python
def _record_failure(self, provider: AIModelProvider):
    """Record failed API call."""
    breaker = self.circuit_breakers[provider]
    breaker.failures += 1
    breaker.last_failure = datetime.utcnow()
    
    if breaker.failures >= ProductionConfiguration.CIRCUIT_BREAKER_THRESHOLD:
        breaker.is_open = True
        logger.warning(f"Circuit breaker OPENED for {provider}")
```

**Success recording resets the breaker** (`app/services/ai_consensus_core.py`, lines 501-508):
```python
def _record_success(self, provider: AIModelProvider):
    """Record successful API call."""
    breaker = self.circuit_breakers[provider]
    breaker.success_count += 1
    
    if breaker.is_open:
        breaker.is_open = False
        breaker.failures = 0
```

---

## 4. Querying AI Models (GPT-4, Claude, Gemini)

Each query goes through the `query_ai_model` method which checks the circuit breaker, then calls `_execute_with_retry` with exponential backoff.

**Main query entry point** (`app/services/ai_consensus_core.py`, lines 120-161):
```python
async def query_ai_model(
    self,
    provider: AIModelProvider,
    prompt: str,
    context: Dict[str, Any] = None,
    request_id: str = None
) -> AIModelResponse:
    """Query specific AI model with circuit breaker protection."""
    
    if self._is_circuit_breaker_open(provider):
        return AIModelResponse(
            provider=provider,
            content="",
            confidence=0.0,
            reasoning="Circuit breaker is open",
            cost=0.0,
            response_time=0.0,
            success=False,
            error="Circuit breaker is open"
        )
    
    start_time = time.time()
    
    try:
        response = await self._execute_with_retry(provider, prompt, context, request_id)
        self._record_success(provider)
        self._track_cost(provider, response.cost)
        response.response_time = time.time() - start_time
        return response
        
    except Exception as e:
        self._record_failure(provider)
        return AIModelResponse(
            provider=provider,
            content="",
            confidence=0.0,
            reasoning=f"Query failed: {str(e)}",
            cost=0.0,
            response_time=time.time() - start_time,
            success=False,
            error=str(e)
        )
```

**Retry with exponential backoff** (`app/services/ai_consensus_core.py`, lines 163-192):
```python
async def _execute_with_retry(
    self,
    provider: AIModelProvider,
    prompt: str,
    context: Dict[str, Any],
    request_id: str
) -> AIModelResponse:
    """Execute AI query with exponential backoff retry."""
    
    config = AIModelConfiguration.get_config(provider)
    last_exception = None
    
    for attempt in range(ProductionConfiguration.MAX_RETRIES):
        try:
            if attempt > 0:
                delay = ProductionConfiguration.INITIAL_RETRY_DELAY * (2 ** attempt)
                await asyncio.sleep(delay)
            
            if provider == AIModelProvider.GPT4:
                return await self._query_gpt4(prompt, context, config, request_id)
            elif provider == AIModelProvider.CLAUDE:
                return await self._query_claude(prompt, context, config, request_id)
            elif provider == AIModelProvider.GEMINI:
                return await self._query_gemini(prompt, context, config, request_id)
            
        except Exception as e:
            last_exception = e
            self.logger.warning(f"AI query attempt {attempt + 1} failed", provider=provider, error=str(e))
    
    raise last_exception or Exception(f"All retry attempts failed for {provider}")
```

**AI response container** (`app/services/ai_consensus_types.py`, lines 39-49):
```python
@dataclass
class AIModelResponse:
    """AI model response container."""
    provider: AIModelProvider
    content: str
    confidence: float
    reasoning: str
    cost: float
    response_time: float
    success: bool
    error: Optional[str] = None
```

---

## 5. Confidence Extraction from AI Responses

The system parses AI response text to extract a confidence score (0-100). It uses regex patterns to find confidence/score/certainty mentions. If none found, it uses a heuristic based on response length.

**Code** (`app/services/ai_consensus_core.py`, lines 439-461):
```python
def _extract_confidence(self, content: str) -> float:
    """Extract confidence score from AI response."""
    import re
    
    confidence_patterns = [
        r"confidence[:\s]*(\d+)%",
        r"(\d+)%\s*confidence",
        r"score[:\s]*(\d+)",
        r"certainty[:\s]*(\d+)%"
    ]
    
    for pattern in confidence_patterns:
        match = re.search(pattern, content.lower())
        if match:
            return float(match.group(1))
    
    # Default confidence based on response quality
    if len(content) > 500 and "analysis" in content.lower():
        return 75.0
    elif len(content) > 200:
        return 65.0
    else:
        return 50.0
```

**How it works**:
1. First tries regex patterns: `"confidence: 85%"`, `"85% confidence"`, `"score: 85"`, `"certainty: 85%"`
2. Falls back to heuristic: 75.0 for detailed responses (>500 chars with "analysis"), 65.0 for moderate responses (>200 chars), 50.0 for short responses

> **Reliability note**: The heuristic fallbacks (response length-based) can produce inconsistent confidence scores when AI models don't explicitly state confidence. The prompts in the system (see Section 9) explicitly request `"Confidence score (1-100) with reasoning"` and `"Include confidence percentage"` to maximize regex match rates. If no regex matches, the length-based defaults act as a conservative safety net.

---

## 6. Reasoning Extraction from AI Responses

The system extracts key reasoning sentences from the AI response by looking for causal language.

**Code** (`app/services/ai_consensus_core.py`, lines 463-481):
```python
def _extract_reasoning(self, content: str) -> str:
    """Extract key reasoning from AI response."""
    sentences = content.split('.')
    
    reasoning_words = ['because', 'due to', 'given that', 'analysis shows', 'indicates']
    reasoning_sentences = []
    
    for sentence in sentences:
        if any(word in sentence.lower() for word in reasoning_words):
            reasoning_sentences.append(sentence.strip())
    
    if reasoning_sentences:
        return '. '.join(reasoning_sentences[:2])
    
    for sentence in sentences:
        if len(sentence.strip()) > 50:
            return sentence.strip()
    
    return "Analysis completed based on provided data."
```

**How it works**:
1. Splits response into sentences by period
2. Searches for sentences containing causal keywords: "because", "due to", "given that", "analysis shows", "indicates"
3. Returns up to 2 such sentences joined
4. Fallback: first sentence longer than 50 chars
5. Final fallback: generic message

---

## 7. Weighted Consensus Scoring

This is the **core scoring algorithm**. It queries all selected AI models in parallel, then calculates a weighted consensus score.

**Parallel model querying** (`app/services/ai_consensus_core.py`, lines 560-591):
```python
async def generate_consensus(
    self,
    prompt: str,
    context: Dict[str, Any],
    confidence_threshold: float,
    model_strategy: str,
    request_id: str
) -> Dict[str, Any]:
    """Generate multi-AI consensus decision."""
    
    selected_models = self._select_models(model_strategy)
    
    # Query all selected models in parallel
    tasks = []
    for provider in selected_models:
        task = self.ai_connector.query_ai_model(provider, prompt, context, request_id)
        tasks.append(task)
    
    responses = await asyncio.gather(*tasks, return_exceptions=True)
    
    successful_responses = [
        resp for resp in responses 
        if isinstance(resp, AIModelResponse) and resp.success
    ]
    
    if not successful_responses:
        return {
            "success": False,
            "error": "No AI models provided successful responses",
            "consensus_score": 0.0,
            "timestamp": datetime.utcnow().isoformat()
        }
```

**Weighted consensus calculation** (`app/services/ai_consensus_core.py`, lines 625-663):
```python
def _calculate_weighted_consensus(self, responses: List[AIModelResponse]) -> Dict[str, Any]:
    """Calculate weighted consensus from AI responses."""
    
    total_weight = 0.0
    weighted_confidence = 0.0
    recommendations = []
    reasoning_parts = []
    
    for response in responses:
        config = AIModelConfiguration.get_config(response.provider)
        performance = self.model_performance.get(response.provider, {"accuracy": 0.8})
        
        base_weight = config.get("weight_factor", 1.0)
        performance_weight = performance["accuracy"]
        confidence_weight = response.confidence / 100.0
        
        final_weight = base_weight * performance_weight * confidence_weight
        
        total_weight += final_weight
        weighted_confidence += response.confidence * final_weight
        
        recommendation = self._extract_recommendation(response.content)
        recommendations.append(recommendation)
        reasoning_parts.append(response.reasoning)
    
    if total_weight > 0:
        final_confidence = weighted_confidence / total_weight
    else:
        final_confidence = 0.0
    
    consensus_recommendation = self._determine_consensus_recommendation(recommendations)
    combined_reasoning = "; ".join(reasoning_parts[:3])
    
    return {
        "consensus_score": final_confidence,
        "recommendation": consensus_recommendation,
        "reasoning": combined_reasoning,
        "model_count": len(responses)
    }
```

**Weight formula per model**:
```
final_weight = base_weight × performance_accuracy × (model_confidence / 100)
```

**Where**:
- `base_weight` = config `weight_factor` (GPT-4: 1.0, Claude: 1.1, Gemini: 0.9)
- `performance_accuracy` = tracked accuracy (GPT-4: 0.85, Claude: 0.82, Gemini: 0.78)
- `confidence_weight` = model's self-reported confidence / 100

**Final consensus score**:
```
consensus_score = Σ(confidence_i × weight_i) / Σ(weight_i)
```

**Model performance baselines** (`app/services/ai_consensus_core.py`, lines 552-558):
```python
class ConsensusEngine(LoggerMixin):
    def __init__(self, ai_connector: AIModelConnector):
        self.ai_connector = ai_connector
        self.model_performance = {
            AIModelProvider.GPT4: {"accuracy": 0.85, "response_time": 2.5},
            AIModelProvider.CLAUDE: {"accuracy": 0.82, "response_time": 3.2},
            AIModelProvider.GEMINI: {"accuracy": 0.78, "response_time": 1.8}
        }
```

---

## 8. Recommendation Extraction & Consensus Voting

The system extracts a trading recommendation from each AI response's text, then uses majority voting.

**Recommendation extraction** (`app/services/ai_consensus_core.py`, lines 665-680):
```python
def _extract_recommendation(self, content: str) -> str:
    """Extract trading recommendation from AI response."""
    content_lower = content.lower()
    
    if "strong buy" in content_lower or "bullish" in content_lower:
        return "STRONG_BUY"
    elif "buy" in content_lower or "long" in content_lower:
        return "BUY"
    elif "strong sell" in content_lower or "bearish" in content_lower:
        return "STRONG_SELL"
    elif "sell" in content_lower or "short" in content_lower:
        return "SELL"
    elif "hold" in content_lower or "wait" in content_lower:
        return "HOLD"
    else:
        return "NEUTRAL"
```

**Majority voting** (`app/services/ai_consensus_core.py`, lines 682-696):
```python
def _determine_consensus_recommendation(self, recommendations: List[str]) -> str:
    """Determine consensus recommendation from individual recommendations."""
    if not recommendations:
        return "NEUTRAL"
    
    rec_counts = {}
    for rec in recommendations:
        rec_counts[rec] = rec_counts.get(rec, 0) + 1
    
    most_common = max(rec_counts.items(), key=lambda x: x[1])
    
    if most_common[1] > len(recommendations) / 2:
        return most_common[0]
    
    return "HOLD"
```

**How it works**: If >50% of models agree on a recommendation, that wins. Otherwise, defaults to "HOLD" (safe fallback).

> **Edge case — 3-way split**: With 3 models and all giving different recommendations (e.g., STRONG_BUY, HOLD, STRONG_SELL), no recommendation exceeds 50% (each has 1/3 = 33%). The system defaults to "HOLD" — a conservative safety mechanism that prevents action when there is no consensus.

---

## 9. Opportunity Analysis Flow

This is the main entry point for analyzing a trading opportunity.

**Code** (`app/services/ai_consensus_core.py`, lines 712-766):
```python
async def analyze_opportunity(
    self,
    analysis_request: str,
    confidence_threshold: float = 80.0,
    ai_models: str = "all",
    user_id: str = None
) -> Dict[str, Any]:
    """Analyze trading opportunity using multi-AI consensus."""
    
    request_id = self._generate_request_id()
    self.logger.info("Analyzing opportunity", request_id=request_id, user_id=user_id)
    
    try:
        try:
            opportunity_data = json.loads(analysis_request) if isinstance(analysis_request, str) else analysis_request
        except json.JSONDecodeError:
            return {
                "success": False,
                "error": "Invalid analysis_request format. Must be valid JSON.",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        prompt = self._build_opportunity_analysis_prompt(opportunity_data)
        
        consensus_result = await self.consensus_engine.generate_consensus(
            prompt=prompt,
            context=opportunity_data,
            confidence_threshold=confidence_threshold,
            model_strategy=ai_models,
            request_id=request_id
        )
        
        if not consensus_result["success"]:
            return consensus_result
        
        enhanced_result = await self._enhance_opportunity_analysis(consensus_result, opportunity_data)
        await self._update_performance_metrics(consensus_result, "analyze_opportunity")
        
        return {
            "success": True,
            "function": "analyze_opportunity",
            "request_id": request_id,
            "opportunity_analysis": enhanced_result,
            "timestamp": datetime.utcnow().isoformat()
        }
```

**The prompt sent to AI models** (`app/services/ai_consensus_core.py`, lines 1045-1061):
```python
def _build_opportunity_analysis_prompt(self, opportunity_data: Dict[str, Any]) -> str:
    """Build sophisticated opportunity analysis prompt."""
    return f"""
    Analyze this cryptocurrency trading opportunity with institutional rigor:
    
    Opportunity Data: {json.dumps(opportunity_data, indent=2)}
    
    Provide analysis covering:
    1. Technical indicators and momentum
    2. Risk/reward ratio assessment
    3. Market timing considerations
    4. Liquidity and execution risks
    5. Confidence score (1-100) with reasoning
    6. Specific recommendation (STRONG_BUY, BUY, HOLD, SELL, STRONG_SELL)
    
    Format your response with clear sections and include a confidence percentage.
    """
```

---

## 10. Enhanced Scoring & Execution Priority

After the raw consensus score is calculated, the system enhances it with execution metadata.

**Code** (`app/services/ai_consensus_core.py`, lines 1101-1109):
```python
async def _enhance_opportunity_analysis(self, consensus: Dict, data: Dict) -> Dict[str, Any]:
    """Enhance opportunity analysis with additional metrics."""
    return {
        **consensus,
        "opportunity_score": consensus["consensus_score"],
        "execution_priority": "HIGH" if consensus["consensus_score"] > 85 else "MEDIUM",
        "suggested_allocation": min(consensus["consensus_score"] / 10, 10),
        "time_horizon": "SHORT_TERM" if data.get("urgency") == "high" else "MEDIUM_TERM"
    }
```

**Scoring rules**:
- `opportunity_score` = the raw consensus_score
- `execution_priority` = "HIGH" if score > 85, "MEDIUM" otherwise
- `suggested_allocation` = score / 10, capped at 10 (so a score of 90 → 9% allocation)
- `time_horizon` = "SHORT_TERM" if urgency is "high", else "MEDIUM_TERM"

---

## 11. Trade Validation via AI Consensus

Before any trade executes, it goes through AI consensus validation.

**Code** (`app/services/ai_consensus_core.py`, lines 1111-1119):
```python
async def _enhance_trade_validation(self, consensus: Dict, data: Dict) -> Dict[str, Any]:
    """Enhance trade validation with additional checks."""
    return {
        **consensus,
        "validation_score": consensus["consensus_score"],
        "approval_status": "APPROVED" if consensus["consensus_score"] > 80 else "REVIEW_REQUIRED",
        "risk_adjusted_size": data.get("quantity", 0) * (consensus["consensus_score"] / 100),
        "execution_window": "IMMEDIATE" if consensus["consensus_score"] > 90 else "FLEXIBLE"
    }
```

**Trade validation prompt** (`app/services/ai_consensus_core.py`, lines 1063-1080):
```python
def _build_trade_validation_prompt(self, trade_data: Dict[str, Any]) -> str:
    """Build trade validation prompt."""
    return f"""
    Validate this trading decision with multi-factor analysis:
    
    Trade Details: {json.dumps(trade_data, indent=2)}
    
    Validation criteria:
    1. Entry/exit point optimization
    2. Position sizing appropriateness
    3. Risk management adequacy
    4. Market condition alignment
    5. Execution timing assessment
    6. Overall trade quality score (1-100)
    
    Provide validation decision: APPROVE, APPROVE_WITH_MODIFICATIONS, or REJECT
    Include confidence percentage and key reasoning.
    """
```

**Approval rules**:
- Score > 80 → `APPROVED`
- Score ≤ 80 → `REVIEW_REQUIRED`
- Score > 90 → `IMMEDIATE` execution window
- Position size is risk-adjusted: `quantity × (score / 100)`

---

## 12. Risk Assessment Scoring

**Code** (`app/services/ai_consensus_core.py`, lines 1121-1130):
```python
async def _enhance_risk_assessment(self, consensus: Dict, data: Dict) -> Dict[str, Any]:
    """Enhance risk assessment with quantitative metrics."""
    risk_score = 100 - consensus["consensus_score"]
    return {
        **consensus,
        "risk_score": risk_score,
        "risk_level": "HIGH" if risk_score > 70 else "MEDIUM" if risk_score > 40 else "LOW",
        "max_position_size": max(0.01, 0.1 * (100 - risk_score) / 100),
        "required_stops": risk_score > 60
    }
```

**Risk scoring**:
- `risk_score` = 100 − consensus_score (inverse relationship)
- Risk levels: >70 = HIGH, >40 = MEDIUM, ≤40 = LOW
- `max_position_size` = 0.1 × (100 − risk_score) / 100, minimum 0.01
- Stop-losses required when risk_score > 60

---

## 13. Final Consensus Decision & Execution Readiness

The `consensus_decision` function is the final go/no-go gate with the highest default confidence threshold (85.0).

**Function signature** (`app/services/ai_consensus_core.py`, lines 966-973):
```python
async def consensus_decision(
    self,
    decision_request: str,
    confidence_threshold: float = 85.0,
    ai_models: str = "all",
    user_id: str = None
) -> Dict[str, Any]:
    """Make final consensus decision using all AI models - NO HARDCODED LIMITATIONS."""
```

**Decision enhancement with execution details** (`app/services/ai_consensus_core.py`, lines 1221-1254):
```python
async def _enhance_consensus_decision(self, consensus: Dict, data: Dict) -> Dict[str, Any]:
    """Enhance consensus decision with execution details."""
    score = consensus["consensus_score"]
    
    if score > 85:
        recommendation = "STRONG_BUY" if data.get("sentiment", "") == "bullish" else "STRONG_SELL"
        execution_ready = True
        urgency = "IMMEDIATE"
    elif score > 70:
        recommendation = "BUY" if data.get("sentiment", "") == "bullish" else "SELL"
        execution_ready = True
        urgency = "PLANNED"
    elif score > 50:
        recommendation = "HOLD"
        execution_ready = False
        urgency = "CONDITIONAL"
    else:
        recommendation = "WAIT"
        execution_ready = False
        urgency = "NONE"
    
    return {
        **consensus,
        "final_recommendation": recommendation,
        "execution_ready": execution_ready,
        "urgency_level": urgency,
        "confidence_level": "HIGH" if score > 80 else "MEDIUM" if score > 60 else "LOW",
        "position_sizing": min(score / 100 * 0.15, 0.15),  # Max 15% per position
        "risk_management": {
            "stop_loss_required": score < 75,
            "position_monitoring": "ACTIVE" if score > 70 else "PASSIVE",
            "review_frequency": "DAILY" if score > 80 else "WEEKLY"
        }
    }
```

**Decision matrix**:

| Consensus Score | Recommendation | Execution Ready | Urgency | Position Sizing | Stop Loss |
|----------------|---------------|----------------|---------|-----------------|-----------|
| > 85 | STRONG_BUY/SELL | ✅ Yes | IMMEDIATE | Up to 15% | Not required |
| 70-85 | BUY/SELL | ✅ Yes | PLANNED | 10.5-12.75% | Required (<75) |
| 50-70 | HOLD | ❌ No | CONDITIONAL | 7.5-10.5% | Required |
| < 50 | WAIT | ❌ No | NONE | < 7.5% | Required |

> **Position sizing formula**: `min(score / 100 × 0.15, 0.15)`. For score=70: 70/100 × 0.15 = 10.5%. For score=85: 85/100 × 0.15 = 12.75%. Maximum is capped at 15% per position.

---

## 14. Opportunity Ranking (Conversational Layer)

A separate ranker normalizes and scores opportunities for the conversational UI layer.

**Scoring formula** (`app/services/conversation/opportunity_ranker.py`, lines 44-88):
```python
def rank_opportunities(
    raw_result: Any,
    *,
    risk_profile: str,
    portfolio_value: float,
    limit: int = 5,
) -> List[RankedOpportunity]:
    """Flatten opportunity payloads and score them for conversational output."""

    opportunities = _extract_opportunity_iterable(raw_result)
    ranked: List[RankedOpportunity] = []

    for item in opportunities:
        normalized = _normalize_opportunity(item)
        if not normalized:
            continue

        risk_penalty = _risk_penalty(normalized["risk_level"], risk_profile)
        win_probability = normalized.get("win_probability") or 0.0
        expected_return = normalized.get("expected_return") or 0.0
        potential_usd = normalized.get("potential_usd")

        # Score emphasizes probability alignment with risk appetite and availability of rationale
        score = (
            win_probability * 0.4
            + expected_return * 0.3
            + (1.0 - risk_penalty) * 0.2
            + (0.1 if normalized.get("rationale") else 0.0)
        )

        ranked.append(
            RankedOpportunity(
                symbol=normalized.get("symbol", "UNKNOWN"),
                direction=normalized.get("direction", ""),
                potential_usd=potential_usd,
                allocation=_suggest_allocation(normalized, portfolio_value),
                win_probability=win_probability,
                risk_level=normalized.get("risk_level", "unknown"),
                rationale=normalized.get("rationale"),
                score=score,
            )
        )

    ranked.sort(key=lambda opp: opp.score, reverse=True)
    return ranked[:limit]
```

**Ranker scoring formula**:
```
score = win_probability × 0.4 + expected_return × 0.3 + (1.0 − risk_penalty) × 0.2 + rationale_bonus × 0.1
```

**Risk penalty calculation** (`app/services/conversation/opportunity_ranker.py`, lines 169-172):
```python
def _risk_penalty(opportunity_risk: str, user_risk: str) -> float:
    opp_score = RISK_MAP.get(opportunity_risk.lower(), 0.6)
    user_score = RISK_MAP.get(user_risk.lower(), 0.5)
    return abs(opp_score - user_score)
```

**Risk map** (`app/services/conversation/opportunity_ranker.py`, lines 8-17):
```python
RISK_MAP = {
    "low": 0.2,
    "medium": 0.5,
    "medium-low": 0.4,
    "medium-high": 0.6,
    "balanced": 0.5,
    "moderate": 0.5,
    "elevated": 0.7,
    "high": 0.85,
}
```

**Key insight**: Risk penalty measures the mismatch between the opportunity's risk and the user's risk profile. A "high" risk opportunity for a "low" risk user = penalty of |0.85 − 0.2| = 0.65. This penalty is applied in the scoring formula as `(1.0 − risk_penalty) × 0.2`, so a 0.65 penalty contributes (1.0 − 0.65) × 0.2 = 0.07 to the total score (out of a maximum 0.2 from this factor). While the weight factor is 20% of the total score, a high mismatch effectively zeroes out most of that component.

---

## 15. Master Controller 5-Phase Pipeline Integration

The master controller uses AI consensus as **Phase 4** in a 5-phase execution pipeline.

**Phase 4: AI Consensus Validation** (`app/services/master_controller.py`, lines 3399-3439):
```python
# =============================================================================
# PHASE 4: AI CONSENSUS SERVICE - VALIDATION
# =============================================================================

if sized_position.get("success"):
    phase_4_start = time.time()
    self.logger.info("🧠 Phase 4: AI Consensus Starting", cycle_id=cycle_id)
    
    try:
        from app.services.ai_consensus_core import ai_consensus_service
        
        validation = await ai_consensus_service.validate_trade(
            analysis_request=json.dumps({
                "signal": trade_signal.get("signal", {}),
                "position_size": sized_position.get("position_size_usd", 0),
                "risk_metrics": sized_position.get("risk_metrics", {}),
                "market_context": market_data.get("assessment", {}),
                "user_id": user_id
            }),
            confidence_threshold=75.0,
            ai_models="all"
        )
        
        phase_4_time = (time.time() - phase_4_start) * 1000
        pipeline_result["phases"]["phase_4"] = {
            "status": "completed",
            "service": "ai_consensus",
            "execution_time_ms": phase_4_time,
            "approved": validation.get("approved", False),
            "consensus_confidence": validation.get("consensus_confidence", 0)
        }
```

**Also in the 5-phase validated execution flow** (`app/services/master_controller.py`, lines 1211-1240):
```python
# PHASE 4: AI Validation
phase_start = time.time()

# Prepare validation request
validation_data = {
    "signal": best_signal["signal"],
    "position_sizing": sizing_result.get("position_sizing", {}),
    "market_context": market_result
}

mode_config = self.mode_configs[self.current_mode]

# Use your sophisticated AI consensus service for validation
validation_result = await ai_consensus_service.validate_trade(
    analysis_request=json.dumps(validation_data),
    confidence_threshold=mode_config.validation_threshold,
    ai_models="all",  # Use all AI models for maximum consensus
    user_id=user_id
)

# ...

# PHASE 5: Execution (if validated)
if (validation_result.get("success") and 
    validation_result.get("trade_validation", {}).get("approval_status") == "APPROVED"):
```

**Key insight**: Trade execution only proceeds if `approval_status == "APPROVED"` (consensus score > 80).

---

## 16. Unified AI Manager Integration

The Unified AI Manager uses AI consensus to validate and format service results before presenting them to users.

**Code** (`app/services/unified_ai_manager.py`, lines 255-267):
```python
# Then use AI consensus to VALIDATE and format the service result
enhanced_context = {
    **{k: v for k, v in decision_context.items() if k != "state_snapshot"},
    "service_result": service_result,
    "analysis_type": "validation_and_formatting",
}

ai_response = await self.ai_consensus.analyze_opportunity(
    json.dumps(enhanced_context, default=str),
    confidence_threshold=75.0,
    ai_models="all",
    user_id=user_id,
)
```

**Result broadcasting via WebSocket** (`app/services/unified_ai_manager.py`, lines 1797-1829):
```python
async def process_ai_consensus_result(
    self,
    user_id: str,
    function: str,
    result: Dict[str, Any],
    interface: InterfaceType
):
    """
    Process AI consensus results and broadcast to all interfaces.
    """
    
    try:
        # Generate natural language explanation
        explanation = await self._generate_consensus_explanation(function, result)
        
        # Broadcast via WebSocket to Command Center
        await manager.broadcast_ai_consensus_update(user_id, {
            "function": function,
            "result": result,
            "explanation": explanation,
            "consensus_score": result.get("consensus_score", 0),
            "recommendation": result.get("recommendation", "HOLD"),
            "model_responses": result.get("model_responses", []),
            "cost_summary": result.get("cost_summary", {}),
            "confidence_threshold_met": result.get("confidence_threshold_met", False),
            "timestamp": result.get("timestamp", datetime.utcnow().isoformat())
        })
```

---

## 17. API Endpoints & Request/Response Models

**API routes** (`app/api/v1/router.py`, lines 60-61):
```python
api_router.include_router(ai_consensus.router, prefix="/ai-consensus", tags=["AI Consensus"])
api_router.include_router(ai_consensus.router, prefix="/ai", tags=["AI Consensus (Compatibility)"])
```

**Request model for opportunity analysis** (`app/api/v1/endpoints/ai_consensus.py`, lines 222-242):
```python
class OpportunityAnalysisRequest(AIConsensusRequest):
    """Opportunity analysis request."""
    symbol: str = "BTC/USDT"
    analysis_type: str = "opportunity"  # opportunity, technical, fundamental
    timeframe: str = "4h"
    include_risk_metrics: bool = True
    
    def get_analysis_data(self) -> Dict[str, Any]:
        """Get analysis data from either analysis_request or individual fields."""
        if self.analysis_request:
            try:
                return json.loads(self.analysis_request)
            except json.JSONDecodeError:
                pass
        
        return {
            "symbol": self.symbol,
            "analysis_type": self.analysis_type,
            "timeframe": self.timeframe,
            "include_risk_metrics": self.include_risk_metrics
        }
```

**Base request model with validation** (`app/api/v1/endpoints/ai_consensus.py`, lines 141-160):
```python
class AIConsensusRequest(BaseModel):
    """Base AI consensus request."""
    analysis_request: Optional[str] = None
    confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD
    ai_models: str = "all"  # "all", "gpt4_claude", "cost_optimized"
    
    @field_validator('confidence_threshold')
    @classmethod
    def validate_confidence_threshold(cls, v):
        if not MIN_CONFIDENCE_THRESHOLD <= v <= MAX_CONFIDENCE_THRESHOLD:
            raise ValueError(f'Confidence threshold must be between {MIN_CONFIDENCE_THRESHOLD} and {MAX_CONFIDENCE_THRESHOLD}')
        return v
    
    @field_validator('ai_models')
    @classmethod
    def validate_ai_models(cls, v):
        valid_strategies = ["all", "gpt4_claude", "cost_optimized"]
        if v not in valid_strategies:
            raise ValueError(f'AI models strategy must be one of: {valid_strategies}')
        return v
```

**Endpoint handler** (`app/api/v1/endpoints/ai_consensus.py`, lines 303-345):
```python
@router.post("/analyze-opportunity")
async def analyze_opportunity_endpoint(
    request: OpportunityAnalysisRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Analyze trading opportunity using multi-AI consensus.
    """
    
    logger.info(
        "AI opportunity analysis requested",
        user_id=str(current_user.id),
        symbol=request.symbol,
        analysis_type=request.analysis_type,
        confidence_threshold=request.confidence_threshold
    )
    
    try:
        call_start_time = datetime.utcnow()
        
        analysis_data = request.get_analysis_data()
        analysis_data.update({
            "user_id": str(current_user.id),
            "timestamp": call_start_time.isoformat()
        })
        
        result = await ai_consensus_service.analyze_opportunity(
            analysis_request=json.dumps(analysis_data),
            confidence_threshold=request.confidence_threshold,
            ai_models=request.ai_models,
            user_id=str(current_user.id)
        )
```

**Result flattening for unified processing** (`app/api/v1/endpoints/ai_consensus.py`, lines 56-85):
```python
def flatten_ai_consensus_result(result: Dict[str, Any], function: str) -> Dict[str, Any]:
    """
    Flatten nested AI consensus result for UnifiedAI processing.
    """
    
    function_data = result.get(function, {})
    
    flattened = {
        "success": result.get("success", False),
        "consensus_score": function_data.get("consensus_score") or result.get("consensus_score", 0),
        "recommendation": function_data.get("recommendation") or result.get("recommendation", "HOLD"),
        "reasoning": function_data.get("reasoning") or result.get("reasoning", ""),
        "confidence_threshold_met": function_data.get("confidence_threshold_met") or result.get("confidence_threshold_met", False),
        "model_responses": function_data.get("model_responses") or result.get("model_responses", []),
        "cost_summary": function_data.get("cost_summary") or result.get("cost_summary", {}),
        "timestamp": function_data.get("timestamp") or result.get("timestamp", ""),
        "function": function,
        "raw_result": result
    }
    
    return flattened
```

**AI model weight validation** (`app/api/v1/endpoints/ai_consensus.py`, lines 279-299):
```python
class AIModelWeightsRequest(BaseModel):
    """AI model weights update request."""
    ai_model_weights: Dict[str, float]
    autonomous_frequency_minutes: Optional[int] = None
    
    @field_validator('ai_model_weights')
    @classmethod
    def validate_weights(cls, v):
        total = sum(v.values())
        if abs(total - EXACT_WEIGHT_SUM) > WEIGHT_SUM_TOLERANCE:
            raise ValueError(f'AI model weights must sum to {EXACT_WEIGHT_SUM}, got {total:.3f}')
        
        for model, weight in v.items():
            if model not in ["gpt4", "claude", "gemini"]:
                raise ValueError(f'Invalid AI model: {model}. Must be one of: gpt4, claude, gemini')
            if not MIN_MODEL_WEIGHT <= weight <= MAX_MODEL_WEIGHT:
                raise ValueError(f'Weight for {model} must be between {MIN_MODEL_WEIGHT} and {MAX_MODEL_WEIGHT}, got {weight}')
        
        return v
```

---

## 18. Cost Tracking

Every AI query tracks its cost based on tokens used × cost per token.

**Cost tracking** (`app/services/ai_consensus_core.py`, lines 520-528):
```python
def _track_cost(self, provider: AIModelProvider, cost: float):
    """Track API costs."""
    self.cost_tracker["total_cost"] += cost
    self.cost_tracker["requests_today"] += 1
    
    if provider not in self.cost_tracker["cost_by_model"]:
        self.cost_tracker["cost_by_model"][provider] = 0.0
    
    self.cost_tracker["cost_by_model"][provider] += cost
```

**Cost report** (`app/services/ai_consensus_core.py`, lines 530-546):
```python
def get_cost_report(self) -> Dict[str, Any]:
    """Get cost tracking report."""
    return {
        "total_cost_usd": round(self.cost_tracker["total_cost"], 4),
        "requests_today": self.cost_tracker["requests_today"],
        "cost_by_model": {
            str(k): round(v, 4) for k, v in self.cost_tracker["cost_by_model"].items()
        },
        "circuit_breaker_status": {
            str(provider): {
                "is_open": breaker.is_open,
                "failures": breaker.failures,
                "success_count": breaker.success_count
            }
            for provider, breaker in self.circuit_breakers.items()
        }
    }
```

**Per-query cost calculation examples**:
- GPT-4: `tokens_used × 0.00001` (from `result["usage"]["total_tokens"]`)
- Claude: `(input_tokens + output_tokens) × 0.000015`
- Gemini: `estimated_tokens × 0.0000025` (estimated from word count since Gemini doesn't always return usage)

---

## 19. Performance Metrics Tracking

**Code** (`app/services/ai_consensus_core.py`, lines 1275-1288):
```python
async def _update_performance_metrics(self, result: Dict, function: str):
    """Update performance metrics."""
    self.performance_metrics["total_requests"] += 1
    
    if result["success"]:
        self.performance_metrics["successful_consensus"] += 1
        
        current_avg = self.performance_metrics["average_confidence"]
        total_requests = self.performance_metrics["total_requests"]
        new_confidence = result.get("consensus_score", 0)
        
        self.performance_metrics["average_confidence"] = (
            (current_avg * (total_requests - 1) + new_confidence) / total_requests
        )
```

**Running average formula**:
```
new_avg = (old_avg × (n-1) + new_score) / n
```

---

## 20. Health Check & Service Status

**Health check** (`app/services/ai_consensus_core.py`, lines 1290-1313):
```python
async def health_check(self) -> Dict[str, Any]:
    """Health check for AI consensus service."""
    try:
        cost_report = self.ai_connector.get_cost_report()
        
        return {
            "service": "ai_consensus",
            "status": "HEALTHY",
            "performance_metrics": self.performance_metrics,
            "cost_report": cost_report,
            "ai_models_status": {
                model.value: "ONLINE" if not breaker.is_open else "CIRCUIT_OPEN"
                for model, breaker in self.ai_connector.circuit_breakers.items()
            },
            "timestamp": datetime.utcnow().isoformat()
        }
```

**Service status with API key checks** (`app/services/ai_consensus_core.py`, lines 1319-1364):
```python
async def get_service_status(self) -> Dict[str, Any]:
    """Get current service status and health information."""
    try:
        circuit_status = {}
        all_healthy = True
        
        for provider, breaker in self.ai_connector.circuit_breakers.items():
            is_healthy = not breaker.is_open
            circuit_status[provider.value] = {
                "healthy": is_healthy,
                "failures": breaker.failures,
                "success_count": breaker.success_count,
                "is_open": breaker.is_open
            }
            if not is_healthy:
                all_healthy = False
        
        if all_healthy:
            status = "operational"
        elif any(not cb["is_open"] for cb in circuit_status.values()):
            status = "degraded"
        else:
            status = "error"
        
        return {
            "status": status,
            "healthy": all_healthy,
            "circuit_breakers": circuit_status,
            "api_keys_configured": {
                "openai": bool(settings.OPENAI_API_KEY),
                "anthropic": bool(settings.ANTHROPIC_API_KEY),
                "google": bool(settings.GOOGLE_AI_API_KEY)
            },
            "timestamp": datetime.utcnow().isoformat()
        }
```

---

## Complete Data Flow Summary

```
User Request
    │
    ▼
API Endpoint (ai_consensus.py)
    │  validates input, rate limits
    ▼
AIConsensusService (ai_consensus_core.py)
    │  builds prompt, generates request_id
    ▼
ConsensusEngine.generate_consensus()
    │  selects models based on strategy
    ▼
AIModelConnector.query_ai_model() × 3 (parallel)
    │  checks circuit breaker → retry with backoff → call API
    ▼
_extract_confidence() + _extract_reasoning()
    │  regex patterns → heuristic fallback
    ▼
_calculate_weighted_consensus()
    │  weight = base_weight × accuracy × (confidence/100)
    │  score = Σ(confidence × weight) / Σ(weight)
    ▼
_extract_recommendation() per model
    │  keyword matching → STRONG_BUY/BUY/HOLD/SELL/STRONG_SELL
    ▼
_determine_consensus_recommendation()
    │  majority vote (>50% agreement), default HOLD
    ▼
_enhance_*() methods
    │  adds execution_priority, position_sizing, risk_management
    ▼
Result returned + metrics updated + cost tracked
    │
    ▼
flatten_ai_consensus_result()
    │
    ▼
unified_ai_manager.process_ai_consensus_result()
    │  generates explanation, broadcasts via WebSocket
    ▼
User sees consensus result in UI
```

---

## Source Files Reference

| File | Purpose |
|------|---------|
| `app/services/ai_consensus_types.py` | Enums, dataclasses (AIModelProvider, CircuitBreakerState, AIModelResponse) |
| `app/services/ai_consensus_core.py` | Full implementation (AIModelConnector, ConsensusEngine, AIConsensusService) |
| `app/services/ai_consensus.py` | Re-export module |
| `app/api/v1/endpoints/ai_consensus.py` | FastAPI endpoints, request/response models, result flattening |
| `app/services/conversation/opportunity_ranker.py` | Conversational opportunity scoring with risk-profile alignment |
| `app/services/master_controller.py` | 5-phase pipeline using AI consensus as Phase 4 validation |
| `app/services/unified_ai_manager.py` | Orchestrates AI consensus with service routing and WebSocket broadcasting |
| `app/models/ai.py` | Database models (AIModel, AIConsensus, AISignal) |
| `app/api/v1/router.py` | Route registration at `/ai-consensus` and `/ai` |
