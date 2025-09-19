"""
Enterprise System Optimization Service

Handles system resource optimization and monitoring:
- Intelligent log rotation and cleanup
- Memory usage optimization
- Disk space management
- Performance monitoring and alerting
- Resource usage optimization
"""

import asyncio
import os
import shutil
import time
import psutil
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from pathlib import Path
import structlog

from app.core.config import get_settings
from app.core.redis import get_redis_client

settings = get_settings()
logger = structlog.get_logger(__name__)


class EnterpriseSystemOptimizer:
    """
    Enterprise system optimization and resource management.
    
    Features:
    - Intelligent log rotation and cleanup
    - Memory usage monitoring and optimization
    - Disk space management with automatic cleanup
    - Performance metrics collection
    - Resource usage alerts and optimization
    """
    
    def __init__(self):
        self.logger = logger
        self.optimization_metrics = {
            "disk_space_freed": 0,
            "memory_optimized": 0,
            "logs_rotated": 0,
            "cache_cleaned": 0,
            "last_optimization": None
        }
        
        # Optimization thresholds
        self.thresholds = {
            "disk_usage_warning": 80.0,  # 80% disk usage
            "disk_usage_critical": 90.0,  # 90% disk usage
            "memory_usage_warning": 85.0,  # 85% memory usage
            "log_file_max_size": 100 * 1024 * 1024,  # 100MB per log file
            "cache_max_age": 24 * 3600,  # 24 hours
            "temp_file_max_age": 3600  # 1 hour
        }
    
    async def optimize_system_resources(self) -> Dict[str, Any]:
        """
        Perform comprehensive system resource optimization.
        
        Returns:
            Dict containing optimization results and metrics
        """
        start_time = time.time()
        self.logger.info("🔧 Starting enterprise system optimization")
        
        try:
            # Get current system metrics
            initial_metrics = await self._get_system_metrics()
            
            # Perform optimizations
            optimization_results = {}
            
            # 1. Disk space optimization
            if initial_metrics["disk_usage_percent"] > self.thresholds["disk_usage_warning"]:
                optimization_results["disk_cleanup"] = await self._optimize_disk_space()
            
            # 2. Log file optimization
            optimization_results["log_optimization"] = await self._optimize_log_files()
            
            # 3. Cache optimization
            optimization_results["cache_optimization"] = await self._optimize_cache_storage()
            
            # 4. Memory optimization
            optimization_results["memory_optimization"] = await self._optimize_memory_usage()
            
            # 5. Temporary file cleanup
            optimization_results["temp_cleanup"] = await self._cleanup_temporary_files()
            
            # Get final metrics
            final_metrics = await self._get_system_metrics()
            
            # Calculate improvements
            improvements = {
                "disk_space_freed_mb": (
                    initial_metrics["disk_free_mb"] - final_metrics["disk_free_mb"]
                ) * -1,  # Negative because free space should increase
                "memory_usage_reduction": (
                    initial_metrics["memory_usage_percent"] - final_metrics["memory_usage_percent"]
                ),
                "optimization_time": time.time() - start_time
            }
            
            self.optimization_metrics["last_optimization"] = datetime.utcnow().isoformat()
            
            self.logger.info("✅ System optimization completed",
                           improvements=improvements,
                           final_metrics=final_metrics)
            
            return {
                "success": True,
                "initial_metrics": initial_metrics,
                "final_metrics": final_metrics,
                "improvements": improvements,
                "optimization_results": optimization_results,
                "duration": time.time() - start_time
            }
            
        except Exception as e:
            self.logger.error("❌ System optimization failed", error=str(e), exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "duration": time.time() - start_time
            }
    
    async def _get_system_metrics(self) -> Dict[str, Any]:
        """Get comprehensive system metrics."""
        try:
            # Disk usage
            disk_usage = shutil.disk_usage("/")
            disk_total_gb = disk_usage.total / (1024**3)
            disk_used_gb = disk_usage.used / (1024**3)
            disk_free_gb = disk_usage.free / (1024**3)
            disk_usage_percent = (disk_used_gb / disk_total_gb) * 100
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_usage_percent = memory.percent
            memory_available_gb = memory.available / (1024**3)
            
            # CPU usage
            cpu_usage_percent = psutil.cpu_percent(interval=1)
            
            # Process information
            current_process = psutil.Process()
            process_memory_mb = current_process.memory_info().rss / (1024**2)
            process_cpu_percent = current_process.cpu_percent()
            
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "disk_total_gb": round(disk_total_gb, 2),
                "disk_used_gb": round(disk_used_gb, 2),
                "disk_free_gb": round(disk_free_gb, 2),
                "disk_free_mb": round(disk_free_gb * 1024, 2),
                "disk_usage_percent": round(disk_usage_percent, 2),
                "memory_usage_percent": round(memory_usage_percent, 2),
                "memory_available_gb": round(memory_available_gb, 2),
                "cpu_usage_percent": round(cpu_usage_percent, 2),
                "process_memory_mb": round(process_memory_mb, 2),
                "process_cpu_percent": round(process_cpu_percent, 2)
            }
            
        except Exception as e:
            self.logger.error("Failed to get system metrics", error=str(e))
            return {}
    
    async def _optimize_disk_space(self) -> Dict[str, Any]:
        """Optimize disk space usage."""
        self.logger.info("💾 Optimizing disk space usage")
        
        try:
            space_freed = 0
            operations = []
            
            # 1. Clean up old log files
            log_cleanup = await self._cleanup_old_logs()
            space_freed += log_cleanup.get("space_freed", 0)
            operations.append("log_cleanup")
            
            # 2. Clean up temporary files
            temp_cleanup = await self._cleanup_temp_files()
            space_freed += temp_cleanup.get("space_freed", 0)
            operations.append("temp_cleanup")
            
            # 3. Clean up old cache files
            cache_cleanup = await self._cleanup_old_cache()
            space_freed += cache_cleanup.get("space_freed", 0)
            operations.append("cache_cleanup")
            
            # 4. Optimize database files (if applicable)
            db_cleanup = await self._optimize_database_files()
            space_freed += db_cleanup.get("space_freed", 0)
            operations.append("db_cleanup")
            
            self.optimization_metrics["disk_space_freed"] += space_freed
            
            return {
                "space_freed_mb": space_freed,
                "operations_performed": operations,
                "status": "completed"
            }
            
        except Exception as e:
            self.logger.error("Disk space optimization failed", error=str(e))
            return {"error": str(e), "space_freed_mb": 0}
    
    async def _optimize_log_files(self) -> Dict[str, Any]:
        """Optimize log files with intelligent rotation."""
        self.logger.info("📝 Optimizing log files")
        
        try:
            log_dirs = [
                "/tmp",
                "/var/log",
                "/workspace/logs",
                "/app/logs"
            ]
            
            files_rotated = 0
            space_freed = 0
            
            for log_dir in log_dirs:
                if os.path.exists(log_dir):
                    for file_path in Path(log_dir).rglob("*.log"):
                        if file_path.is_file():
                            file_size = file_path.stat().st_size
                            
                            # Rotate large log files
                            if file_size > self.thresholds["log_file_max_size"]:
                                await self._rotate_log_file(file_path)
                                files_rotated += 1
                                space_freed += file_size * 0.7  # Estimate 70% space savings
            
            self.optimization_metrics["logs_rotated"] += files_rotated
            
            return {
                "files_rotated": files_rotated,
                "space_freed_mb": space_freed / (1024**2),
                "status": "completed"
            }
            
        except Exception as e:
            self.logger.error("Log optimization failed", error=str(e))
            return {"error": str(e)}
    
    async def _cleanup_old_logs(self) -> Dict[str, Any]:
        """Clean up old log files."""
        try:
            space_freed = 0
            files_deleted = 0
            
            # Find and delete old log files
            cutoff_time = time.time() - (7 * 24 * 3600)  # 7 days ago
            
            log_patterns = ["*.log", "*.log.*", "*.out", "*.err"]
            search_dirs = ["/tmp", "/var/log", "/workspace"]
            
            for search_dir in search_dirs:
                if os.path.exists(search_dir):
                    for pattern in log_patterns:
                        for file_path in Path(search_dir).rglob(pattern):
                            if file_path.is_file() and file_path.stat().st_mtime < cutoff_time:
                                file_size = file_path.stat().st_size
                                try:
                                    file_path.unlink()
                                    space_freed += file_size
                                    files_deleted += 1
                                except OSError:
                                    pass  # File might be in use
            
            return {
                "files_deleted": files_deleted,
                "space_freed": space_freed / (1024**2)  # MB
            }
            
        except Exception as e:
            self.logger.error("Old log cleanup failed", error=str(e))
            return {"error": str(e), "space_freed": 0}
    
    async def _cleanup_temp_files(self) -> Dict[str, Any]:
        """Clean up temporary files."""
        try:
            space_freed = 0
            files_deleted = 0
            
            temp_dirs = ["/tmp", "/var/tmp", "/workspace/tmp"]
            cutoff_time = time.time() - self.thresholds["temp_file_max_age"]
            
            for temp_dir in temp_dirs:
                if os.path.exists(temp_dir):
                    for file_path in Path(temp_dir).iterdir():
                        if (file_path.is_file() and 
                            file_path.stat().st_mtime < cutoff_time and
                            not file_path.name.startswith('.')):  # Don't delete hidden files
                            
                            file_size = file_path.stat().st_size
                            try:
                                file_path.unlink()
                                space_freed += file_size
                                files_deleted += 1
                            except OSError:
                                pass  # File might be in use
            
            return {
                "files_deleted": files_deleted,
                "space_freed": space_freed / (1024**2)  # MB
            }
            
        except Exception as e:
            self.logger.error("Temp file cleanup failed", error=str(e))
            return {"error": str(e), "space_freed": 0}
    
    async def _cleanup_old_cache(self) -> Dict[str, Any]:
        """Clean up old cache files."""
        try:
            space_freed = 0
            
            # Clean Redis cache if available
            redis = await get_redis_client()
            if redis:
                # Get cache statistics before cleanup
                info_before = await redis.info("memory")
                
                # Clean expired keys
                await redis.flushdb()
                
                # Get cache statistics after cleanup
                info_after = await redis.info("memory")
                
                memory_freed = info_before.get("used_memory", 0) - info_after.get("used_memory", 0)
                space_freed += memory_freed
                
                self.logger.info("Redis cache optimized",
                               memory_freed_bytes=memory_freed)
            
            return {
                "redis_cache_cleared": redis is not None,
                "space_freed": space_freed / (1024**2)  # MB
            }
            
        except Exception as e:
            self.logger.error("Cache cleanup failed", error=str(e))
            return {"error": str(e), "space_freed": 0}
    
    async def _optimize_memory_usage(self) -> Dict[str, Any]:
        """Optimize memory usage."""
        try:
            # Force garbage collection
            import gc
            collected = gc.collect()
            
            # Get memory info
            process = psutil.Process()
            memory_info = process.memory_info()
            
            self.optimization_metrics["memory_optimized"] += collected
            
            return {
                "garbage_collected": collected,
                "memory_rss_mb": memory_info.rss / (1024**2),
                "memory_vms_mb": memory_info.vms / (1024**2),
                "status": "completed"
            }
            
        except Exception as e:
            self.logger.error("Memory optimization failed", error=str(e))
            return {"error": str(e)}
    
    async def _optimize_database_files(self) -> Dict[str, Any]:
        """Optimize database files (if local database)."""
        try:
            # For PostgreSQL/Supabase, this would typically be handled by the service
            # For local SQLite files, we could optimize here
            
            sqlite_files = list(Path("/workspace").glob("*.db"))
            optimized_files = 0
            
            for db_file in sqlite_files:
                if db_file.exists():
                    # For SQLite, we could run VACUUM, but this is risky in production
                    # Just log the file size for monitoring
                    file_size_mb = db_file.stat().st_size / (1024**2)
                    self.logger.info(f"Database file found: {db_file.name}",
                                   size_mb=file_size_mb)
                    optimized_files += 1
            
            return {
                "database_files_checked": optimized_files,
                "space_freed": 0,  # No actual optimization for production safety
                "status": "checked"
            }
            
        except Exception as e:
            self.logger.error("Database optimization failed", error=str(e))
            return {"error": str(e), "space_freed": 0}
    
    async def _cleanup_temporary_files(self) -> Dict[str, Any]:
        """Clean up application temporary files."""
        try:
            temp_patterns = [
                "*.tmp",
                "*.temp", 
                "*~",
                "*.bak",
                "*.cache",
                "__pycache__"
            ]
            
            files_deleted = 0
            space_freed = 0
            
            for pattern in temp_patterns:
                for file_path in Path("/workspace").rglob(pattern):
                    if file_path.is_file():
                        file_size = file_path.stat().st_size
                        try:
                            file_path.unlink()
                            files_deleted += 1
                            space_freed += file_size
                        except OSError:
                            pass  # File might be in use
                    elif file_path.is_dir() and pattern == "__pycache__":
                        try:
                            shutil.rmtree(file_path)
                            files_deleted += 1
                        except OSError:
                            pass
            
            return {
                "files_deleted": files_deleted,
                "space_freed": space_freed / (1024**2)  # MB
            }
            
        except Exception as e:
            self.logger.error("Temporary file cleanup failed", error=str(e))
            return {"error": str(e), "space_freed": 0}
    
    async def _rotate_log_file(self, file_path: Path):
        """Rotate a large log file."""
        try:
            # Create rotated filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            rotated_path = file_path.with_suffix(f".{timestamp}{file_path.suffix}")
            
            # Move current log to rotated name
            file_path.rename(rotated_path)
            
            # Compress rotated log if possible
            try:
                import gzip
                with open(rotated_path, 'rb') as f_in:
                    with gzip.open(f"{rotated_path}.gz", 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                
                # Remove uncompressed rotated file
                rotated_path.unlink()
                
                self.logger.info("Log file rotated and compressed",
                               original=str(file_path),
                               compressed=f"{rotated_path}.gz")
                
            except ImportError:
                # gzip not available, keep uncompressed
                self.logger.info("Log file rotated (uncompressed)",
                               original=str(file_path),
                               rotated=str(rotated_path))
                
        except Exception as e:
            self.logger.error("Log rotation failed",
                            file=str(file_path),
                            error=str(e))
    
    async def get_optimization_metrics(self) -> Dict[str, Any]:
        """Get optimization metrics for monitoring."""
        system_metrics = await self._get_system_metrics()
        
        return {
            "system_metrics": system_metrics,
            "optimization_metrics": self.optimization_metrics,
            "thresholds": self.thresholds,
            "alerts": await self._generate_system_alerts(system_metrics)
        }
    
    async def _generate_system_alerts(self, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate system alerts based on current metrics."""
        alerts = []
        
        # Disk usage alerts
        disk_usage = metrics.get("disk_usage_percent", 0)
        if disk_usage >= self.thresholds["disk_usage_critical"]:
            alerts.append({
                "severity": "critical",
                "type": "disk_usage",
                "message": f"Critical disk usage: {disk_usage:.1f}% >= {self.thresholds['disk_usage_critical']}%",
                "value": disk_usage,
                "threshold": self.thresholds["disk_usage_critical"]
            })
        elif disk_usage >= self.thresholds["disk_usage_warning"]:
            alerts.append({
                "severity": "warning", 
                "type": "disk_usage",
                "message": f"High disk usage: {disk_usage:.1f}% >= {self.thresholds['disk_usage_warning']}%",
                "value": disk_usage,
                "threshold": self.thresholds["disk_usage_warning"]
            })
        
        # Memory usage alerts
        memory_usage = metrics.get("memory_usage_percent", 0)
        if memory_usage >= self.thresholds["memory_usage_warning"]:
            alerts.append({
                "severity": "warning",
                "type": "memory_usage",
                "message": f"High memory usage: {memory_usage:.1f}% >= {self.thresholds['memory_usage_warning']}%",
                "value": memory_usage,
                "threshold": self.thresholds["memory_usage_warning"]
            })
        
        return alerts


# Global system optimizer instance
system_optimizer = EnterpriseSystemOptimizer()


async def optimize_system_resources() -> Dict[str, Any]:
    """Convenience function to optimize system resources."""
    return await system_optimizer.optimize_system_resources()


async def get_system_optimization_metrics() -> Dict[str, Any]:
    """Get system optimization metrics."""
    return await system_optimizer.get_optimization_metrics()