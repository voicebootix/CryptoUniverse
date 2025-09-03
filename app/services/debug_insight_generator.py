"""
Enhanced Debug Insight Generator - AI-Powered System Maintenance

Advanced debugging and AI-powered system maintenance tool that harvests logs,
extracts error patterns, sends context to Claude AI for production-grade fixes,
and provides persistent fix storage with self-healing capabilities.

CORE FEATURES:
- Log harvesting from system and application logs
- Error pattern extraction and deduplication
- Claude AI integration for production-grade fixes  
- Persistent fix storage and retrieval
- Self-healing loops and automated maintenance
- System health monitoring and anomaly detection
- Fix effectiveness tracking and learning

Adapted from Flowise Enhanced Debug Insight Generator to native Python.
"""

import asyncio
import json
import time
import hashlib
import os
import re
import aiofiles
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import uuid

import structlog
import aiohttp
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.core.redis import redis_manager
from app.core.logging import LoggerMixin

settings = get_settings()
logger = structlog.get_logger(__name__)


class AnalysisMode(str, Enum):
    """Log analysis mode enumeration."""
    RECENT = "recent"
    WINDOW = "window" 
    FULL = "full"


class ErrorSeverity(str, Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ErrorSignature:
    """Error signature for deduplication."""
    signature: str
    message: str
    count: int
    first_seen: str
    last_seen: str
    severity: str


@dataclass
class LogEntry:
    """Log entry structure."""
    timestamp: str
    level: str
    message: str
    source: str
    service: Optional[str] = None
    category: Optional[str] = None
    exception_type: Optional[str] = None
    stack_trace: Optional[str] = None


@dataclass
class DebugSession:
    """Debug session tracking."""
    session_id: str
    started_at: str
    analysis_mode: str
    time_range_minutes: int
    focus_services: List[str]
    errors_found: int
    fixes_generated: int
    fixes_applied: int
    status: str


@dataclass
class AIFix:
    """AI-generated fix structure."""
    fix_id: str
    error_signature: str
    target: str
    location_hint: str
    language: str
    replacement_code: str
    confidence: float
    tests: List[str]
    notes: str
    created_at: str
    applied: bool = False
    effectiveness: Optional[float] = None


class EnhancedDebugInsightGenerator(LoggerMixin):
    """
    Enhanced Debug Insight Generator
    
    AI-powered system maintenance tool that provides comprehensive debugging,
    error analysis, and automated fix generation capabilities.
    """
    
    def __init__(self):
        # Configuration
        self.persist_dir = self._get_persist_dir()
        self.registry_path = self.persist_dir / "registry.json"
        self.fixes_dir = self.persist_dir / "fixes"
        self.logs_dir = self.persist_dir / "logs"
        
        # Ensure directories exist
        asyncio.create_task(self._ensure_directories())
        
        # State tracking
        self.active_sessions: Dict[str, DebugSession] = {}
        self.error_registry: Dict[str, ErrorSignature] = {}
        self.applied_fixes: Dict[str, AIFix] = {}
        
        # AI client settings
        self.claude_api_key = settings.ANTHROPIC_API_KEY or settings.OPENAI_API_KEY
        self.claude_model = "claude-3-5-sonnet-latest"
        
        # System monitoring
        self.monitoring_enabled = True
        self.loop_enabled = False
        self.loop_delay_minutes = 5
        
        self.logger.info("Enhanced Debug Insight Generator initialized", 
                        persist_dir=str(self.persist_dir))
    
    def _get_persist_dir(self) -> Path:
        """Get persistent directory for storing fixes and logs."""
        
        # Try environment variable first
        persist_dir = os.getenv("PERSIST_DIR")
        if persist_dir:
            return Path(persist_dir) / "ai_fixes"
        
        # Default to project directory
        return Path.cwd() / "data" / "ai_fixes"
    
    async def _ensure_directories(self):
        """Ensure all required directories exist."""
        
        directories = [self.persist_dir, self.fixes_dir, self.logs_dir]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    async def execute_analysis(
        self,
        analysis_mode: str = "recent",
        time_range_minutes: int = 60,
        focus_services: Optional[str] = None,
        include_project_context: bool = False,
        project_context_url: Optional[str] = None,
        dedupe_window_minutes: int = 120,
        enable_loop: bool = False,
        loop_delay_minutes: int = 5,
        user_id: str = "system"
    ) -> Dict[str, Any]:
        """
        Execute comprehensive debug analysis.
        
        Args:
            analysis_mode: Analysis mode (recent, window, full)
            time_range_minutes: Lookback window for logs
            focus_services: Comma-separated services to focus on
            include_project_context: Include project context for AI
            project_context_url: URL to fetch project context
            dedupe_window_minutes: Deduplication window
            enable_loop: Enable self-loop for continuous monitoring
            loop_delay_minutes: Delay before relaunch
            user_id: User ID for tracking
            
        Returns:
            Dict containing analysis results
        """
        
        session_id = f"debug_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        started_at = datetime.utcnow()
        
        try:
            # Parse focus services
            focus_list = []
            if focus_services:
                focus_list = [s.strip().lower() for s in focus_services.split(",")]
            
            # Create debug session
            session = DebugSession(
                session_id=session_id,
                started_at=started_at.isoformat(),
                analysis_mode=analysis_mode,
                time_range_minutes=time_range_minutes,
                focus_services=focus_list,
                errors_found=0,
                fixes_generated=0,
                fixes_applied=0,
                status="RUNNING"
            )
            
            self.active_sessions[session_id] = session
            
            self.logger.info("Starting debug analysis", 
                           session_id=session_id,
                           analysis_mode=analysis_mode,
                           time_range=time_range_minutes)
            
            # Step 1: Collect logs and errors
            collected_logs = await self._collect_system_logs(
                time_range_minutes=time_range_minutes,
                focus_services=focus_list
            )
            
            # Step 2: Extract error signatures
            error_signatures = await self._extract_error_signatures(
                collected_logs,
                dedupe_window_minutes
            )
            
            session.errors_found = len(error_signatures)
            
            # Step 3: Filter new errors (not recently processed)
            new_errors = await self._filter_new_errors(
                error_signatures,
                dedupe_window_minutes
            )
            
            # Step 4: Generate fixes for new errors
            fixes = []
            if new_errors and self.claude_api_key:
                # Build context bundle
                context = await self._build_context_bundle(
                    collected_logs,
                    include_project_context,
                    project_context_url
                )
                
                # Get AI fixes
                ai_fixes = await self._generate_ai_fixes(
                    new_errors,
                    collected_logs,
                    context
                )
                
                if ai_fixes.get("success"):
                    fixes = ai_fixes.get("fixes", [])
                    session.fixes_generated = len(fixes)
                    
                    # Persist fixes
                    await self._persist_fixes(fixes, session_id)
            
            # Step 5: Update registry
            await self._update_error_registry(error_signatures, session_id)
            
            # Update session status
            session.status = "COMPLETED" if not new_errors or fixes else "PARTIAL"
            
            # Calculate execution time
            execution_time = (datetime.utcnow() - started_at).total_seconds() * 1000
            
            # Step 6: Self-loop if enabled
            loop_result = None
            if enable_loop:
                self.loop_enabled = True
                self.loop_delay_minutes = loop_delay_minutes
                
                # Schedule next run
                asyncio.create_task(self._schedule_next_run(loop_delay_minutes))
                
                loop_result = {
                    "scheduled": True,
                    "delay_minutes": loop_delay_minutes,
                    "next_run": (datetime.utcnow() + timedelta(minutes=loop_delay_minutes)).isoformat()
                }
            
            result = {
                "success": True,
                "session_id": session_id,
                "persist_dir": str(self.persist_dir),
                "started_at": started_at.isoformat(),
                "finished_at": datetime.utcnow().isoformat(),
                "execution_time_ms": execution_time,
                "analysis": {
                    "mode": analysis_mode,
                    "lookback_minutes": time_range_minutes,
                    "focus_services": focus_list,
                    "logs_collected": len(collected_logs),
                    "error_signatures_found": len(error_signatures),
                    "new_errors": len(new_errors),
                    "fixes_generated": len(fixes)
                },
                "loop": {
                    "enabled": enable_loop,
                    "result": loop_result
                },
                "recommendations": self._generate_recommendations(session, fixes)
            }
            
            # Log completion
            self.logger.info("Debug analysis completed",
                           session_id=session_id,
                           errors_found=session.errors_found,
                           fixes_generated=session.fixes_generated)
            
            return result
            
        except Exception as e:
            self.logger.error("Debug analysis failed", 
                            session_id=session_id, 
                            error=str(e), 
                            exc_info=True)
            
            if session_id in self.active_sessions:
                self.active_sessions[session_id].status = "FAILED"
            
            return {
                "success": False,
                "session_id": session_id,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _collect_system_logs(
        self,
        time_range_minutes: int,
        focus_services: List[str]
    ) -> List[LogEntry]:
        """Collect system logs from various sources."""
        
        logs = []
        cutoff_time = datetime.utcnow() - timedelta(minutes=time_range_minutes)
        
        try:
            # Collect from application logs (structured logging)
            app_logs = await self._collect_application_logs(cutoff_time)
            logs.extend(app_logs)
            
            # Collect from system logs if available
            system_logs = await self._collect_system_logs_from_files(cutoff_time)
            logs.extend(system_logs)
            
            # Filter by focus services if specified
            if focus_services and "all" not in focus_services:
                logs = self._filter_logs_by_services(logs, focus_services)
            
            # Sort by timestamp
            logs.sort(key=lambda x: x.timestamp)
            
        except Exception as e:
            self.logger.error("Failed to collect system logs", error=str(e))
        
        return logs
    
    async def _collect_application_logs(self, cutoff_time: datetime) -> List[LogEntry]:
        """Collect logs from application logging system."""
        
        logs = []
        
        try:
            # Read from log files if they exist
            log_file_patterns = [
                "logs/file_*.log",
                "logs/error_*.log", 
                "app.log",
                "error.log"
            ]
            
            for pattern in log_file_patterns:
                for log_file in Path.cwd().glob(pattern):
                    if log_file.exists():
                        file_logs = await self._parse_log_file(log_file, cutoff_time)
                        logs.extend(file_logs)
            
        except Exception as e:
            self.logger.warning("Failed to collect application logs", error=str(e))
        
        return logs
    
    async def _collect_system_logs_from_files(self, cutoff_time: datetime) -> List[LogEntry]:
        """Collect system logs from log files."""
        
        logs = []
        
        try:
            # Common system log locations (Linux/Unix)
            system_log_paths = [
                "/var/log/messages",
                "/var/log/syslog",
                "/var/log/application.log"
            ]
            
            for log_path in system_log_paths:
                if os.path.exists(log_path) and os.access(log_path, os.R_OK):
                    try:
                        file_logs = await self._parse_log_file(Path(log_path), cutoff_time)
                        logs.extend(file_logs)
                    except Exception as e:
                        self.logger.debug(f"Could not read {log_path}", error=str(e))
        
        except Exception as e:
            self.logger.debug("System logs not accessible", error=str(e))
        
        return logs
    
    async def _parse_log_file(self, log_file: Path, cutoff_time: datetime) -> List[LogEntry]:
        """Parse log file and extract entries."""
        
        logs = []
        
        try:
            async with aiofiles.open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                async for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Try to parse the log line
                    log_entry = self._parse_log_line(line, str(log_file))
                    if log_entry and self._is_log_recent(log_entry, cutoff_time):
                        logs.append(log_entry)
        
        except Exception as e:
            self.logger.debug(f"Failed to parse log file {log_file}", error=str(e))
        
        return logs
    
    def _parse_log_line(self, line: str, source: str) -> Optional[LogEntry]:
        """Parse individual log line into LogEntry."""
        
        try:
            # Try JSON format first (structured logging)
            if line.startswith('{'):
                try:
                    log_data = json.loads(line)
                    return LogEntry(
                        timestamp=log_data.get('timestamp', datetime.utcnow().isoformat()),
                        level=log_data.get('level', 'INFO').upper(),
                        message=log_data.get('message', ''),
                        source=source,
                        service=log_data.get('service'),
                        category=log_data.get('category'),
                        exception_type=log_data.get('exception_type'),
                        stack_trace=log_data.get('stack_trace')
                    )
                except json.JSONDecodeError:
                    pass
            
            # Try common log formats
            patterns = [
                # ISO timestamp format: 2024-01-01 12:00:00.000 | ERROR | message
                r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}) \| (\w+) \| (.+)$',
                # Standard format: 2024-01-01 12:00:00 ERROR message
                r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) (\w+) (.+)$',
                # Syslog format: Jan 01 12:00:00 hostname service: message
                r'^(\w{3} \d{1,2} \d{2}:\d{2}:\d{2}) \w+ (\w+): (.+)$'
            ]
            
            for pattern in patterns:
                match = re.match(pattern, line)
                if match:
                    timestamp_str = match.group(1)
                    level = match.group(2).upper()
                    message = match.group(3)
                    
                    # Convert timestamp to ISO format
                    try:
                        if 'T' not in timestamp_str:
                            timestamp_str = timestamp_str.replace(' ', 'T')
                        if '.' not in timestamp_str:
                            timestamp_str += '.000'
                        # Ensure timezone info
                        if not timestamp_str.endswith('Z') and '+' not in timestamp_str:
                            timestamp_str += 'Z'
                    except:
                        timestamp_str = datetime.utcnow().isoformat()
                    
                    return LogEntry(
                        timestamp=timestamp_str,
                        level=level,
                        message=message,
                        source=source
                    )
            
            # Fallback - treat entire line as message with current timestamp
            return LogEntry(
                timestamp=datetime.utcnow().isoformat(),
                level="INFO",
                message=line,
                source=source
            )
        
        except Exception as e:
            self.logger.debug("Failed to parse log line", line=line[:100], error=str(e))
            return None
    
    def _is_log_recent(self, log_entry: LogEntry, cutoff_time: datetime) -> bool:
        """Check if log entry is within the time range."""
        
        try:
            log_time = datetime.fromisoformat(log_entry.timestamp.replace('Z', '+00:00'))
            return log_time >= cutoff_time
        except:
            # If we can't parse timestamp, include it to be safe
            return True
    
    def _filter_logs_by_services(self, logs: List[LogEntry], focus_services: List[str]) -> List[LogEntry]:
        """Filter logs by focus services."""
        
        filtered_logs = []
        
        for log in logs:
            # Check if log mentions any focus service
            log_text = f"{log.message} {log.service or ''} {log.category or ''}".lower()
            
            if any(service in log_text for service in focus_services):
                filtered_logs.append(log)
        
        return filtered_logs
    
    async def _extract_error_signatures(
        self,
        logs: List[LogEntry],
        dedupe_window_minutes: int
    ) -> List[ErrorSignature]:
        """Extract and deduplicate error signatures from logs."""
        
        error_patterns = {}
        
        # Error detection patterns
        error_keywords = [
            "error", "exception", "failed", "failure", "crash", "critical",
            "timeout", "connection refused", "permission denied", "not found",
            "invalid", "unauthorized", "forbidden", "internal server error"
        ]
        
        for log in logs:
            message_lower = log.message.lower()
            
            # Check if this is an error log
            is_error = (
                log.level.upper() in ["ERROR", "CRITICAL", "FATAL"] or
                any(keyword in message_lower for keyword in error_keywords)
            )
            
            if is_error:
                # Create signature from first 200 chars of message
                signature_text = log.message[:200]
                signature_hash = hashlib.sha256(signature_text.encode()).hexdigest()[:16]
                
                if signature_hash not in error_patterns:
                    error_patterns[signature_hash] = {
                        "message": signature_text,
                        "count": 0,
                        "first_seen": log.timestamp,
                        "last_seen": log.timestamp,
                        "severity": self._determine_error_severity(log)
                    }
                
                error_patterns[signature_hash]["count"] += 1
                error_patterns[signature_hash]["last_seen"] = log.timestamp
        
        # Convert to ErrorSignature objects
        signatures = []
        for sig_hash, data in error_patterns.items():
            signatures.append(ErrorSignature(
                signature=sig_hash,
                message=data["message"],
                count=data["count"],
                first_seen=data["first_seen"],
                last_seen=data["last_seen"],
                severity=data["severity"]
            ))
        
        # Sort by count (most frequent first)
        signatures.sort(key=lambda x: x.count, reverse=True)
        
        return signatures[:20]  # Limit to top 20 errors
    
    def _determine_error_severity(self, log: LogEntry) -> str:
        """Determine error severity from log entry."""
        
        message_lower = log.message.lower()
        level = log.level.upper()
        
        # Critical keywords
        critical_keywords = ["critical", "fatal", "crash", "died", "killed"]
        high_keywords = ["error", "exception", "failed", "failure", "timeout"]
        medium_keywords = ["warning", "warn", "deprecated", "invalid"]
        
        if level in ["CRITICAL", "FATAL"] or any(k in message_lower for k in critical_keywords):
            return ErrorSeverity.CRITICAL.value
        elif level == "ERROR" or any(k in message_lower for k in high_keywords):
            return ErrorSeverity.HIGH.value
        elif level == "WARNING" or any(k in message_lower for k in medium_keywords):
            return ErrorSeverity.MEDIUM.value
        else:
            return ErrorSeverity.LOW.value
    
    async def _filter_new_errors(
        self,
        error_signatures: List[ErrorSignature],
        dedupe_window_minutes: int
    ) -> List[ErrorSignature]:
        """Filter out recently processed errors."""
        
        new_errors = []
        current_time = datetime.utcnow()
        
        # Load existing registry
        registry = await self._load_error_registry()
        
        for signature in error_signatures:
            # Check if this error was recently processed
            if signature.signature in registry:
                last_processed = datetime.fromisoformat(registry[signature.signature]["last_processed"])
                time_diff = (current_time - last_processed).total_seconds() / 60
                
                if time_diff < dedupe_window_minutes:
                    continue  # Skip recently processed error
            
            new_errors.append(signature)
        
        return new_errors
    
    async def _build_context_bundle(
        self,
        logs: List[LogEntry],
        include_project_context: bool,
        project_context_url: Optional[str]
    ) -> Dict[str, Any]:
        """Build context bundle for AI analysis."""
        
        context = {
            "summary": {
                "production": True,
                "constraints": [
                    "No simplifications",
                    "No hardcoded mock data", 
                    "Do not remove features",
                    "Fix root cause with production-safe code"
                ],
                "system_info": {
                    "architecture": "Python FastAPI microservices",
                    "database": "PostgreSQL with SQLAlchemy",
                    "cache": "Redis",
                    "deployment": "Docker containers"
                }
            },
            "recent_logs": logs[-100:] if logs else [],  # Last 100 logs
            "log_stats": {
                "total_logs": len(logs),
                "error_logs": len([l for l in logs if l.level == "ERROR"]),
                "warning_logs": len([l for l in logs if l.level == "WARNING"]),
                "time_range": {
                    "start": logs[0].timestamp if logs else None,
                    "end": logs[-1].timestamp if logs else None
                }
            }
        }
        
        # Add project context if requested
        if include_project_context and project_context_url:
            try:
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                    async with session.get(project_context_url) as response:
                        if response.status == 200:
                            project_context = await response.text()
                            context["project_context"] = project_context[:50000]  # Limit size
            except Exception as e:
                self.logger.warning("Failed to fetch project context", 
                                  url=project_context_url, 
                                  error=str(e))
        
        return context
    
    async def _generate_ai_fixes(
        self,
        error_signatures: List[ErrorSignature],
        logs: List[LogEntry],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate AI fixes using Claude API."""
        
        if not self.claude_api_key:
            return {"success": False, "error": "No AI API key configured"}
        
        try:
            # Prepare error summary
            error_summary = []
            for sig in error_signatures[:5]:  # Limit to top 5 errors
                error_summary.append(f"Error: {sig.message[:200]} (Count: {sig.count}, Severity: {sig.severity})")
            
            # Prepare log excerpt
            error_logs = [l for l in logs if l.level in ["ERROR", "CRITICAL"]]
            log_excerpt = []
            for log in error_logs[:20]:  # Limit to 20 error logs
                log_excerpt.append(f"{log.timestamp} {log.level} {log.message[:300]}")
            
            # Build AI prompt
            prompt = self._build_ai_fix_prompt(error_summary, log_excerpt, context)
            
            # Call Claude API
            ai_response = await self._call_claude_api(prompt)
            
            if ai_response.get("success"):
                # Parse AI response into fixes
                fixes = self._parse_ai_fixes(ai_response.get("content", ""), error_signatures)
                return {"success": True, "fixes": fixes}
            else:
                return {"success": False, "error": ai_response.get("error", "Unknown AI error")}
        
        except Exception as e:
            self.logger.error("Failed to generate AI fixes", error=str(e))
            return {"success": False, "error": str(e)}
    
    def _build_ai_fix_prompt(
        self,
        error_summary: List[str],
        log_excerpt: List[str],
        context: Dict[str, Any]
    ) -> str:
        """Build prompt for AI fix generation."""
        
        return f"""You are a Senior Python DevOps Engineer and CTO for a production cryptocurrency trading system.

SYSTEM ARCHITECTURE:
- Python FastAPI microservices
- PostgreSQL with SQLAlchemy ORM
- Redis for caching and sessions
- Docker containerized deployment
- Structured logging with loguru/structlog

TASK: Analyze the following production errors and provide PRODUCTION-READY fixes.

CONSTRAINTS:
- NO mock data or placeholders
- NO simplifications or feature removal
- Fix root causes, not symptoms
- All code must be production-safe
- Preserve all existing functionality

ERROR SIGNATURES:
{chr(10).join(error_summary)}

LOG EXCERPT:
{chr(10).join(log_excerpt[:10])}

SYSTEM INFO:
{json.dumps(context.get("summary", {}), indent=2)}

REQUIRED OUTPUT FORMAT (strict JSON):
{{
  "fixes": [
    {{
      "target": "filename.py or ServiceName",
      "location_hint": "function_name or line_range",
      "language": "python",
      "replacement_code": "// Complete function or code block",
      "confidence": 0.85,
      "description": "Brief fix description",
      "root_cause": "Identified root cause",
      "tests": ["pytest command", "validation step"],
      "risk_level": "low|medium|high"
    }}
  ],
  "notes": "Overall analysis and recommendations"
}}

RESPOND ONLY WITH VALID JSON. NO MARKDOWN. NO PROSE."""
    
    async def _call_claude_api(self, prompt: str) -> Dict[str, Any]:
        """Call Claude API for fix generation."""
        
        try:
            headers = {
                "Content-Type": "application/json",
                "x-api-key": self.claude_api_key,
                "anthropic-version": "2023-06-01"
            }
            
            payload = {
                "model": self.claude_model,
                "max_tokens": 4000,
                "temperature": 0.1,
                "system": "Return only valid JSON. No markdown. No prose. Production-grade fixes only.",
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }
            
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
                async with session.post(
                    "https://api.anthropic.com/v1/messages",
                    headers=headers,
                    json=payload
                ) as response:
                    
                    if response.status == 200:
                        result = await response.json()
                        content = result.get("content", [{}])[0].get("text", "")
                        return {"success": True, "content": content}
                    else:
                        error_text = await response.text()
                        return {"success": False, "error": f"API error {response.status}: {error_text}"}
        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _parse_ai_fixes(self, ai_content: str, error_signatures: List[ErrorSignature]) -> List[AIFix]:
        """Parse AI response into AIFix objects."""
        
        fixes = []
        
        try:
            # Try to parse JSON response
            ai_data = json.loads(ai_content)
            ai_fixes = ai_data.get("fixes", [])
            
            for i, fix_data in enumerate(ai_fixes):
                # Map to error signature if possible
                error_signature = error_signatures[i].signature if i < len(error_signatures) else "unknown"
                
                fix = AIFix(
                    fix_id=f"fix_{int(time.time())}_{uuid.uuid4().hex[:8]}",
                    error_signature=error_signature,
                    target=fix_data.get("target", "unknown"),
                    location_hint=fix_data.get("location_hint", ""),
                    language=fix_data.get("language", "python"),
                    replacement_code=fix_data.get("replacement_code", ""),
                    confidence=float(fix_data.get("confidence", 0.5)),
                    tests=fix_data.get("tests", []),
                    notes=fix_data.get("description", "") + " | " + fix_data.get("root_cause", ""),
                    created_at=datetime.utcnow().isoformat()
                )
                
                fixes.append(fix)
        
        except json.JSONDecodeError as e:
            self.logger.warning("Failed to parse AI response as JSON", error=str(e))
            # Create a generic fix from the raw content
            fix = AIFix(
                fix_id=f"fix_{int(time.time())}_{uuid.uuid4().hex[:8]}",
                error_signature="unknown",
                target="manual_review",
                location_hint="ai_response",
                language="text",
                replacement_code=ai_content[:1000],  # Truncate
                confidence=0.3,
                tests=[],
                notes="AI response needs manual parsing",
                created_at=datetime.utcnow().isoformat()
            )
            fixes.append(fix)
        
        return fixes
    
    async def _persist_fixes(self, fixes: List[AIFix], session_id: str) -> None:
        """Persist fixes to disk for future reference."""
        
        try:
            session_dir = self.fixes_dir / session_id
            session_dir.mkdir(parents=True, exist_ok=True)
            
            for fix in fixes:
                fix_file = session_dir / f"{fix.fix_id}.json"
                
                fix_data = {
                    "fix_id": fix.fix_id,
                    "error_signature": fix.error_signature,
                    "target": fix.target,
                    "location_hint": fix.location_hint,
                    "language": fix.language,
                    "replacement_code": fix.replacement_code,
                    "confidence": fix.confidence,
                    "tests": fix.tests,
                    "notes": fix.notes,
                    "created_at": fix.created_at,
                    "session_id": session_id
                }
                
                async with aiofiles.open(fix_file, 'w') as f:
                    await f.write(json.dumps(fix_data, indent=2))
                
                # Store in memory for quick access
                self.applied_fixes[fix.fix_id] = fix
        
        except Exception as e:
            self.logger.error("Failed to persist fixes", error=str(e))
    
    async def _load_error_registry(self) -> Dict[str, Any]:
        """Load error registry from disk."""
        
        try:
            if self.registry_path.exists():
                async with aiofiles.open(self.registry_path, 'r') as f:
                    content = await f.read()
                    return json.loads(content)
        except Exception as e:
            self.logger.debug("Could not load error registry", error=str(e))
        
        return {}
    
    async def _update_error_registry(
        self,
        error_signatures: List[ErrorSignature],
        session_id: str
    ) -> None:
        """Update error registry with new signatures."""
        
        try:
            registry = await self._load_error_registry()
            current_time = datetime.utcnow().isoformat()
            
            # Update registry with new errors
            for signature in error_signatures:
                registry[signature.signature] = {
                    "message": signature.message,
                    "count": signature.count,
                    "severity": signature.severity,
                    "first_seen": signature.first_seen,
                    "last_seen": signature.last_seen,
                    "last_processed": current_time,
                    "session_id": session_id
                }
            
            # Save registry
            async with aiofiles.open(self.registry_path, 'w') as f:
                await f.write(json.dumps(registry, indent=2))
        
        except Exception as e:
            self.logger.error("Failed to update error registry", error=str(e))
    
    async def _schedule_next_run(self, delay_minutes: int) -> None:
        """Schedule next analysis run."""
        
        try:
            await asyncio.sleep(delay_minutes * 60)
            
            if self.loop_enabled:
                # Run another analysis
                result = await self.execute_analysis(
                    analysis_mode="recent",
                    time_range_minutes=60,
                    enable_loop=True,
                    loop_delay_minutes=self.loop_delay_minutes
                )
                
                self.logger.info("Scheduled analysis completed", result=result.get("success"))
        
        except Exception as e:
            self.logger.error("Scheduled analysis failed", error=str(e))
    
    def _generate_recommendations(
        self,
        session: DebugSession,
        fixes: List[AIFix]
    ) -> List[str]:
        """Generate recommendations based on analysis results."""
        
        recommendations = []
        
        if session.errors_found == 0:
            recommendations.append("✅ No significant errors detected - system appears healthy")
        
        if session.errors_found > 10:
            recommendations.append("⚠️ High error volume detected - prioritize critical fixes")
        
        if fixes:
            high_confidence_fixes = [f for f in fixes if f.confidence > 0.8]
            if high_confidence_fixes:
                recommendations.append(f"🔧 {len(high_confidence_fixes)} high-confidence fixes available for immediate deployment")
        
        if session.focus_services:
            recommendations.append(f"🎯 Focused analysis on: {', '.join(session.focus_services)}")
        
        recommendations.append("📊 Enable continuous monitoring with loop mode for proactive maintenance")
        
        return recommendations
    
    async def get_analysis_history(self, limit: int = 10) -> Dict[str, Any]:
        """Get recent analysis history."""
        
        sessions = list(self.active_sessions.values())
        sessions.sort(key=lambda x: x.started_at, reverse=True)
        
        return {
            "recent_sessions": [
                {
                    "session_id": s.session_id,
                    "started_at": s.started_at,
                    "analysis_mode": s.analysis_mode,
                    "status": s.status,
                    "errors_found": s.errors_found,
                    "fixes_generated": s.fixes_generated
                }
                for s in sessions[:limit]
            ],
            "total_fixes_available": len(self.applied_fixes),
            "monitoring_enabled": self.monitoring_enabled,
            "loop_enabled": self.loop_enabled
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check for debug insight generator."""
        
        return {
            "service": "debug_insight_generator",
            "status": "HEALTHY",
            "persist_dir": str(self.persist_dir),
            "claude_api_configured": bool(self.claude_api_key),
            "active_sessions": len(self.active_sessions),
            "total_fixes_generated": len(self.applied_fixes),
            "monitoring_enabled": self.monitoring_enabled,
            "loop_enabled": self.loop_enabled,
            "timestamp": datetime.utcnow().isoformat()
        }


# Global service instance
debug_insight_generator = EnhancedDebugInsightGenerator()


# FastAPI dependency
async def get_debug_insight_generator() -> EnhancedDebugInsightGenerator:
    """Dependency injection for FastAPI."""
    return debug_insight_generator
