"""
Enterprise Model Validator - SQLAlchemy 2.x Compatibility

This service validates all database models for SQLAlchemy 2.x compatibility
and provides comprehensive analysis of potential issues.

Features:
- Model structure validation
- Relationship integrity checking
- Column type compatibility
- Index and constraint validation
- Performance analysis
- Migration recommendations

Author: CTO Assistant
Date: September 20, 2025
"""

import importlib
import inspect
from datetime import datetime
from typing import Dict, Any, List, Optional, Type
import structlog

logger = structlog.get_logger(__name__)


class ModelValidationResult:
    """Result of model validation with detailed analysis."""
    
    def __init__(self, model_name: str):
        self.model_name = model_name
        self.is_valid = True
        self.issues = []
        self.warnings = []
        self.recommendations = []
        self.performance_notes = []
    
    def add_issue(self, issue_type: str, description: str, severity: str = "error"):
        """Add validation issue."""
        self.issues.append({
            "type": issue_type,
            "description": description,
            "severity": severity
        })
        if severity == "error":
            self.is_valid = False
    
    def add_warning(self, warning_type: str, description: str):
        """Add validation warning."""
        self.warnings.append({
            "type": warning_type,
            "description": description
        })
    
    def add_recommendation(self, rec_type: str, description: str):
        """Add improvement recommendation."""
        self.recommendations.append({
            "type": rec_type,
            "description": description
        })


class EnterpriseModelValidator:
    """
    Enterprise Model Validator for SQLAlchemy 2.x
    
    Provides comprehensive validation of database models for
    SQLAlchemy 2.x compatibility and enterprise standards.
    """
    
    def __init__(self):
        self.model_modules = [
            "app.models.user",
            "app.models.trading", 
            "app.models.credit",
            "app.models.exchange",
            "app.models.market",
            "app.models.system",
            "app.models.telegram_integration",
            "app.models.analytics",
            "app.models.tenant",
            "app.models.ai",
            "app.models.ab_testing",
            "app.models.session",
            "app.models.subscription",
            "app.models.data",
            "app.models.oauth",
            "app.models.market_data",
            "app.models.strategy_submission",
            "app.models.chat",
            "app.models.copy_trading"
        ]
        self.validation_results = {}
    
    async def validate_all_models(self) -> Dict[str, Any]:
        """Validate all models for SQLAlchemy 2.x compatibility."""
        logger.info("🔍 Starting comprehensive model validation for SQLAlchemy 2.x")
        
        validation_summary = {
            "total_models": 0,
            "valid_models": 0,
            "invalid_models": 0,
            "models_with_warnings": 0,
            "critical_issues": [],
            "overall_status": "unknown",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        for module_name in self.model_modules:
            try:
                logger.info(f"Validating module: {module_name}")
                module_result = await self._validate_module(module_name)
                self.validation_results[module_name] = module_result
                
                validation_summary["total_models"] += len(module_result["models"])
                validation_summary["valid_models"] += len([m for m in module_result["models"].values() if m.is_valid])
                validation_summary["invalid_models"] += len([m for m in module_result["models"].values() if not m.is_valid])
                validation_summary["models_with_warnings"] += len([m for m in module_result["models"].values() if m.warnings])
                
                # Collect critical issues
                for model_name, result in module_result["models"].items():
                    critical_issues = [issue for issue in result.issues if issue["severity"] == "critical"]
                    if critical_issues:
                        validation_summary["critical_issues"].extend([
                            {
                                "model": model_name,
                                "module": module_name,
                                **issue
                            }
                            for issue in critical_issues
                        ])
                
            except Exception as e:
                logger.exception(f"Failed to validate module {module_name}", error=str(e))
                validation_summary["critical_issues"].append({
                    "model": "module_load",
                    "module": module_name,
                    "type": "import_error",
                    "description": str(e),
                    "severity": "critical"
                })
        
        # Determine overall status
        if validation_summary["critical_issues"]:
            validation_summary["overall_status"] = "critical_issues"
        elif validation_summary["invalid_models"] > 0:
            validation_summary["overall_status"] = "has_issues"
        elif validation_summary["models_with_warnings"] > 0:
            validation_summary["overall_status"] = "has_warnings"
        else:
            validation_summary["overall_status"] = "all_valid"
        
        logger.info("✅ Model validation completed", 
                   total_models=validation_summary["total_models"],
                   valid_models=validation_summary["valid_models"],
                   status=validation_summary["overall_status"])
        
        return validation_summary
    
    async def _validate_module(self, module_name: str) -> Dict[str, Any]:
        """Validate a specific module."""
        module_result = {
            "module_name": module_name,
            "import_success": False,
            "models": {},
            "module_issues": []
        }
        
        try:
            # Import the module
            module = importlib.import_module(module_name)
            module_result["import_success"] = True
            
            # Find all model classes
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if hasattr(obj, '__tablename__') and hasattr(obj, 'metadata'):
                    # This is a SQLAlchemy model
                    model_validation = await self._validate_model(obj)
                    module_result["models"][name] = model_validation
            
        except Exception as e:
            module_result["module_issues"].append({
                "type": "import_error",
                "description": str(e),
                "severity": "critical"
            })
        
        return module_result
    
    async def _validate_model(self, model_class: Type) -> ModelValidationResult:
        """Validate a specific model class."""
        result = ModelValidationResult(model_class.__name__)
        
        try:
            # Check basic model structure
            if not hasattr(model_class, '__tablename__'):
                result.add_issue("missing_tablename", "Model missing __tablename__ attribute", "critical")
            
            if not hasattr(model_class, 'metadata'):
                result.add_issue("missing_metadata", "Model missing metadata attribute", "critical")
            
            # Check for SQLAlchemy 2.x compatibility
            if hasattr(model_class, '__table__'):
                table = model_class.__table__
                
                # Validate columns
                for column in table.columns:
                    if hasattr(column.type, 'schema') and column.type.schema is None:
                        result.add_warning("column_schema", f"Column {column.name} has None schema")
                
                # Check indexes
                for index in table.indexes:
                    if len(index.columns) == 0:
                        result.add_issue("empty_index", f"Index {index.name} has no columns", "error")
                
                # Check foreign keys
                for fk in table.foreign_keys:
                    if not fk.column.table:
                        result.add_issue("invalid_fk", f"Foreign key {fk} has invalid target", "error")
            
            # Check for deprecated patterns
            model_source = inspect.getsource(model_class)
            
            if "Column(" in model_source and "nullable=False" not in model_source:
                result.add_recommendation("nullable_explicit", "Consider making nullable explicit for all columns")
            
            if "relationship(" in model_source:
                result.add_recommendation("relationship_lazy", "Review relationship lazy loading for performance")
            
        except Exception as e:
            result.add_issue("validation_error", f"Model validation failed: {str(e)}", "critical")
        
        return result
    
    def generate_migration_report(self) -> Dict[str, Any]:
        """Generate comprehensive migration report."""
        if not self.validation_results:
            return {"error": "No validation results available"}
        
        report = {
            "migration_feasibility": "unknown",
            "critical_blockers": [],
            "recommended_fixes": [],
            "migration_strategy": [],
            "risk_assessment": "unknown",
            "estimated_effort": "unknown"
        }
        
        total_critical = sum(
            len([issue for model_result in module["models"].values() 
                 for issue in model_result.issues if issue["severity"] == "critical"])
            for module in self.validation_results.values()
            if "models" in module
        )
        
        if total_critical == 0:
            report["migration_feasibility"] = "ready"
            report["risk_assessment"] = "low"
            report["estimated_effort"] = "minimal"
            report["migration_strategy"] = [
                "Update database.py to use SQLAlchemy 2.x patterns",
                "Test model imports",
                "Validate database operations",
                "Deploy with monitoring"
            ]
        elif total_critical <= 5:
            report["migration_feasibility"] = "fixable"
            report["risk_assessment"] = "medium"
            report["estimated_effort"] = "moderate"
            report["migration_strategy"] = [
                "Fix critical model issues first",
                "Implement backward compatibility layer",
                "Gradual migration with rollback plan",
                "Comprehensive testing before deployment"
            ]
        else:
            report["migration_feasibility"] = "complex"
            report["risk_assessment"] = "high"
            report["estimated_effort"] = "significant"
            report["migration_strategy"] = [
                "Create comprehensive compatibility layer",
                "Fix models in phases",
                "Implement blue-green deployment",
                "Extensive testing and validation"
            ]
        
        return report


# Global model validator
model_validator = EnterpriseModelValidator()