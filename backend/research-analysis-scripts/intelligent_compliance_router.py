"""
Intelligent Compliance Router
Routes data records to appropriate processing architecture based on compliance urgency and risk assessment

This module implements sophisticated routing logic that determines whether records should be:
1. Processed immediately via stream processing (Storm)
2. Batched for later processing via batch processing (Spark)

Routing decisions are based on:
- Compliance violation severity
- Regulatory deadlines
- Data sensitivity levels
- Risk assessment scores
- Business impact analysis
"""

import sys
import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum
from dataclasses import dataclass

# Add src to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
src_dir = os.path.join(backend_dir, 'src')
sys.path.insert(0, backend_dir)
sys.path.insert(0, src_dir)

class ProcessingMode(Enum):
    IMMEDIATE_STREAM = "immediate_stream"
    BATCH_DEFERRED = "batch_deferred"
    PRIORITY_STREAM = "priority_stream"

class ComplianceUrgency(Enum):
    CRITICAL = "critical"      # Must process within minutes
    HIGH = "high"             # Must process within hours
    MEDIUM = "medium"         # Must process within days
    LOW = "low"              # Can process in batch cycles

class RiskLevel(Enum):
    EXTREME = "extreme"       # Immediate financial/legal impact
    HIGH = "high"            # Significant business impact
    MEDIUM = "medium"        # Moderate business impact
    LOW = "low"             # Minimal business impact

@dataclass
class RoutingDecision:
    processing_mode: ProcessingMode
    urgency_level: ComplianceUrgency
    risk_level: RiskLevel
    reasoning: str
    estimated_processing_time: float
    regulatory_deadline: Optional[datetime]
    business_impact_score: float

class IntelligentComplianceRouter:
    """
    Intelligent routing system that makes processing architecture decisions
    based on compliance requirements, risk assessment, and business impact
    """
    
    def __init__(self):
        self.routing_rules = self._initialize_routing_rules()
        self.risk_assessment_engine = RiskAssessmentEngine()
        self.compliance_urgency_analyzer = ComplianceUrgencyAnalyzer()
        
    def _initialize_routing_rules(self) -> Dict[str, Any]:
        """Initialize comprehensive routing rules for different compliance scenarios"""
        return {
            "hipaa_rules": {
                "phi_exposure": {
                    "urgency": ComplianceUrgency.CRITICAL,
                    "processing_mode": ProcessingMode.IMMEDIATE_STREAM,
                    "max_processing_delay": 300,  # 5 minutes
                    "reasoning": "PHI exposure requires immediate containment"
                },
                "audit_trail_gap": {
                    "urgency": ComplianceUrgency.HIGH,
                    "processing_mode": ProcessingMode.PRIORITY_STREAM,
                    "max_processing_delay": 3600,  # 1 hour
                    "reasoning": "Audit trail gaps compromise compliance integrity"
                },
                "routine_screening": {
                    "urgency": ComplianceUrgency.MEDIUM,
                    "processing_mode": ProcessingMode.BATCH_DEFERRED,
                    "max_processing_delay": 86400,  # 24 hours
                    "reasoning": "Routine screening can be processed in batches"
                }
            },
            "gdpr_rules": {
                "data_breach": {
                    "urgency": ComplianceUrgency.CRITICAL,
                    "processing_mode": ProcessingMode.IMMEDIATE_STREAM,
                    "max_processing_delay": 2160,  # 72 hours for notification
                    "reasoning": "GDPR breach notification deadline"
                },
                "consent_withdrawal": {
                    "urgency": ComplianceUrgency.HIGH,
                    "processing_mode": ProcessingMode.IMMEDIATE_STREAM,
                    "max_processing_delay": 3600,  # 1 hour
                    "reasoning": "Data processing must stop immediately"
                },
                "data_retention_violation": {
                    "urgency": ComplianceUrgency.MEDIUM,
                    "processing_mode": ProcessingMode.BATCH_DEFERRED,
                    "max_processing_delay": 604800,  # 7 days
                    "reasoning": "Retention violations can be addressed in batch"
                }
            },
            "pci_rules": {
                "card_data_exposure": {
                    "urgency": ComplianceUrgency.CRITICAL,
                    "processing_mode": ProcessingMode.IMMEDIATE_STREAM,
                    "max_processing_delay": 60,  # 1 minute
                    "reasoning": "Card data exposure requires immediate action"
                },
                "transaction_anomaly": {
                    "urgency": ComplianceUrgency.HIGH,
                    "processing_mode": ProcessingMode.PRIORITY_STREAM,
                    "max_processing_delay": 900,  # 15 minutes
                    "reasoning": "Potential fraud requires quick investigation"
                },
                "compliance_audit": {
                    "urgency": ComplianceUrgency.LOW,
                    "processing_mode": ProcessingMode.BATCH_DEFERRED,
                    "max_processing_delay": 2592000,  # 30 days
                    "reasoning": "Audit preparation can be done in batches"
                }
            },
            "temporal_rules": {
                "recent_transaction": {
                    "time_threshold": 3600,  # 1 hour
                    "processing_mode": ProcessingMode.IMMEDIATE_STREAM,
                    "reasoning": "Recent transactions need immediate processing"
                },
                "historical_data": {
                    "time_threshold": 86400,  # 24 hours
                    "processing_mode": ProcessingMode.BATCH_DEFERRED,
                    "reasoning": "Historical data can be processed in batches"
                }
            },
            "volume_rules": {
                "high_volume_threshold": 10000,
                "low_volume_threshold": 100,
                "burst_processing_mode": ProcessingMode.BATCH_DEFERRED,
                "normal_processing_mode": ProcessingMode.IMMEDIATE_STREAM
            }
        }
    
    def route_record(self, record: Dict[str, Any]) -> RoutingDecision:
        """
        Main routing function that determines processing architecture
        based on record characteristics and compliance requirements
        """
        # Step 1: Assess compliance urgency
        urgency_assessment = self.compliance_urgency_analyzer.analyze_urgency(record)
        
        # Step 2: Assess risk level
        risk_assessment = self.risk_assessment_engine.assess_risk(record)
        
        # Step 3: Apply temporal analysis
        temporal_analysis = self._analyze_temporal_factors(record)
        
        # Step 4: Apply volume analysis
        volume_analysis = self._analyze_volume_factors(record)
        
        # Step 5: Make routing decision
        routing_decision = self._make_routing_decision(
            record, urgency_assessment, risk_assessment, 
            temporal_analysis, volume_analysis
        )
        
        return routing_decision
    
    def _analyze_temporal_factors(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze temporal factors that influence routing decisions"""
        current_time = datetime.now()
        
        # Extract relevant timestamps
        created_at = record.get('created_at')
        transaction_date = record.get('transaction_date')
        treatment_date = record.get('treatment_date')
        
        # Determine data age
        data_age = None
        if created_at:
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            data_age = (current_time - created_at).total_seconds()
        
        # Apply temporal rules
        temporal_rules = self.routing_rules["temporal_rules"]
        
        if data_age and data_age < temporal_rules["recent_transaction"]["time_threshold"]:
            return {
                "classification": "recent",
                "recommended_mode": temporal_rules["recent_transaction"]["processing_mode"],
                "reasoning": temporal_rules["recent_transaction"]["reasoning"],
                "data_age": data_age
            }
        else:
            return {
                "classification": "historical",
                "recommended_mode": temporal_rules["historical_data"]["processing_mode"],
                "reasoning": temporal_rules["historical_data"]["reasoning"],
                "data_age": data_age
            }
    
    def _analyze_volume_factors(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze volume factors that might influence routing"""
        # This would typically connect to a real-time metrics system
        # For now, simulate based on record characteristics
        
        volume_rules = self.routing_rules["volume_rules"]
        
        # Simulate current processing volume
        simulated_current_volume = 1000  # This would be real-time metrics
        
        if simulated_current_volume > volume_rules["high_volume_threshold"]:
            return {
                "volume_level": "high",
                "recommended_mode": volume_rules["burst_processing_mode"],
                "reasoning": "High volume detected, routing to batch processing"
            }
        else:
            return {
                "volume_level": "normal",
                "recommended_mode": volume_rules["normal_processing_mode"],
                "reasoning": "Normal volume, can use stream processing"
            }
    
    def _make_routing_decision(self, record: Dict[str, Any], 
                             urgency_assessment: Dict[str, Any],
                             risk_assessment: Dict[str, Any],
                             temporal_analysis: Dict[str, Any],
                             volume_analysis: Dict[str, Any]) -> RoutingDecision:
        """
        Make final routing decision based on all assessment factors
        """
        # Priority hierarchy: Urgency > Risk > Temporal > Volume
        
        # Critical urgency always goes to immediate stream
        if urgency_assessment["urgency"] == ComplianceUrgency.CRITICAL:
            return RoutingDecision(
                processing_mode=ProcessingMode.IMMEDIATE_STREAM,
                urgency_level=urgency_assessment["urgency"],
                risk_level=risk_assessment["risk_level"],
                reasoning=f"Critical urgency: {urgency_assessment['reasoning']}",
                estimated_processing_time=urgency_assessment["max_processing_delay"],
                regulatory_deadline=urgency_assessment.get("deadline"),
                business_impact_score=risk_assessment["business_impact_score"]
            )
        
        # High risk with high urgency goes to priority stream
        if (risk_assessment["risk_level"] in [RiskLevel.EXTREME, RiskLevel.HIGH] and 
            urgency_assessment["urgency"] == ComplianceUrgency.HIGH):
            return RoutingDecision(
                processing_mode=ProcessingMode.PRIORITY_STREAM,
                urgency_level=urgency_assessment["urgency"],
                risk_level=risk_assessment["risk_level"],
                reasoning=f"High risk + high urgency: {risk_assessment['reasoning']}",
                estimated_processing_time=urgency_assessment["max_processing_delay"],
                regulatory_deadline=urgency_assessment.get("deadline"),
                business_impact_score=risk_assessment["business_impact_score"]
            )
        
        # Medium/Low urgency can be batched unless temporal factors override
        if urgency_assessment["urgency"] in [ComplianceUrgency.MEDIUM, ComplianceUrgency.LOW]:
            # Check if temporal factors require immediate processing
            if temporal_analysis["classification"] == "recent":
                return RoutingDecision(
                    processing_mode=ProcessingMode.IMMEDIATE_STREAM,
                    urgency_level=urgency_assessment["urgency"],
                    risk_level=risk_assessment["risk_level"],
                    reasoning=f"Recent data overrides batch preference: {temporal_analysis['reasoning']}",
                    estimated_processing_time=3600,  # 1 hour for recent data
                    regulatory_deadline=urgency_assessment.get("deadline"),
                    business_impact_score=risk_assessment["business_impact_score"]
                )
            else:
                return RoutingDecision(
                    processing_mode=ProcessingMode.BATCH_DEFERRED,
                    urgency_level=urgency_assessment["urgency"],
                    risk_level=risk_assessment["risk_level"],
                    reasoning=f"Low urgency + historical data: suitable for batch processing",
                    estimated_processing_time=urgency_assessment["max_processing_delay"],
                    regulatory_deadline=urgency_assessment.get("deadline"),
                    business_impact_score=risk_assessment["business_impact_score"]
                )
        
        # Default to immediate stream for safety
        return RoutingDecision(
            processing_mode=ProcessingMode.IMMEDIATE_STREAM,
            urgency_level=urgency_assessment["urgency"],
            risk_level=risk_assessment["risk_level"],
            reasoning="Default to immediate processing for safety",
            estimated_processing_time=3600,
            regulatory_deadline=urgency_assessment.get("deadline"),
            business_impact_score=risk_assessment["business_impact_score"]
        )

class ComplianceUrgencyAnalyzer:
    """Analyzes compliance urgency based on violation types and regulatory requirements"""
    
    def analyze_urgency(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze compliance urgency for a given record"""
        
        # Detect violation types
        violation_type = record.get('violation_type')
        data_type = record.get('data_type', 'unknown')
        has_violation = record.get('has_violation', False)
        
        if not has_violation:
            return {
                "urgency": ComplianceUrgency.LOW,
                "reasoning": "No compliance violation detected",
                "max_processing_delay": 86400,  # 24 hours
                "deadline": None
            }
        
        # HIPAA urgency analysis
        if data_type == 'healthcare':
            return self._analyze_hipaa_urgency(record, violation_type)
        
        # GDPR urgency analysis
        elif data_type == 'financial':
            return self._analyze_gdpr_urgency(record, violation_type)
        
        # Default analysis
        return {
            "urgency": ComplianceUrgency.MEDIUM,
            "reasoning": "Unknown violation type, medium urgency",
            "max_processing_delay": 3600,  # 1 hour
            "deadline": None
        }
    
    def _analyze_hipaa_urgency(self, record: Dict[str, Any], violation_type: str) -> Dict[str, Any]:
        """Analyze HIPAA-specific urgency factors"""
        
        # Check for PHI exposure
        if record.get('ssn') or record.get('phone') or record.get('email'):
            return {
                "urgency": ComplianceUrgency.CRITICAL,
                "reasoning": "PHI exposure detected - immediate containment required",
                "max_processing_delay": 300,  # 5 minutes
                "deadline": datetime.now() + timedelta(minutes=5)
            }
        
        # Check for medical record access violations
        if record.get('medical_record_number'):
            return {
                "urgency": ComplianceUrgency.HIGH,
                "reasoning": "Medical record access violation",
                "max_processing_delay": 3600,  # 1 hour
                "deadline": datetime.now() + timedelta(hours=1)
            }
        
        return {
            "urgency": ComplianceUrgency.MEDIUM,
            "reasoning": "General HIPAA violation",
            "max_processing_delay": 86400,  # 24 hours
            "deadline": datetime.now() + timedelta(days=1)
        }
    
    def _analyze_gdpr_urgency(self, record: Dict[str, Any], violation_type: str) -> Dict[str, Any]:
        """Analyze GDPR-specific urgency factors"""
        
        # Check for data breach indicators
        if violation_type == 'GDPR_VIOLATION':
            consent_given = record.get('consent_given', True)
            data_retention_days = record.get('data_retention_days', 0)
            
            if not consent_given:
                return {
                    "urgency": ComplianceUrgency.CRITICAL,
                    "reasoning": "Processing without consent - immediate stop required",
                    "max_processing_delay": 60,  # 1 minute
                    "deadline": datetime.now() + timedelta(minutes=1)
                }
            
            if data_retention_days > 2557:  # > 7 years
                return {
                    "urgency": ComplianceUrgency.HIGH,
                    "reasoning": "Data retention violation",
                    "max_processing_delay": 604800,  # 7 days
                    "deadline": datetime.now() + timedelta(days=7)
                }
        
        return {
            "urgency": ComplianceUrgency.MEDIUM,
            "reasoning": "General GDPR violation",
            "max_processing_delay": 86400,  # 24 hours
            "deadline": datetime.now() + timedelta(days=1)
        }

class RiskAssessmentEngine:
    """Assesses business and regulatory risk levels for compliance violations"""
    
    def assess_risk(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Assess risk level for a given record"""
        
        risk_factors = self._calculate_risk_factors(record)
        risk_level = self._determine_risk_level(risk_factors)
        business_impact_score = self._calculate_business_impact(record, risk_factors)
        
        return {
            "risk_level": risk_level,
            "risk_factors": risk_factors,
            "business_impact_score": business_impact_score,
            "reasoning": self._generate_risk_reasoning(risk_level, risk_factors)
        }
    
    def _calculate_risk_factors(self, record: Dict[str, Any]) -> Dict[str, float]:
        """Calculate various risk factors"""
        factors = {
            "data_sensitivity": 0.0,
            "violation_severity": 0.0,
            "regulatory_exposure": 0.0,
            "business_impact": 0.0
        }
        
        # Data sensitivity scoring
        if record.get('ssn'):
            factors["data_sensitivity"] += 0.4
        if record.get('medical_record_number'):
            factors["data_sensitivity"] += 0.3
        if record.get('account_number'):
            factors["data_sensitivity"] += 0.3
        
        # Violation severity scoring
        if record.get('has_violation'):
            violation_type = record.get('violation_type', '')
            if 'PHI_EXPOSURE' in violation_type:
                factors["violation_severity"] = 0.9
            elif 'GDPR_VIOLATION' in violation_type:
                factors["violation_severity"] = 0.7
            else:
                factors["violation_severity"] = 0.5
        
        # Regulatory exposure scoring
        data_type = record.get('data_type', '')
        if data_type == 'healthcare':
            factors["regulatory_exposure"] = 0.8  # HIPAA penalties
        elif data_type == 'financial':
            factors["regulatory_exposure"] = 0.7  # GDPR penalties
        
        # Business impact scoring (simplified)
        transaction_amount = record.get('transaction_amount', 0)
        if transaction_amount > 10000:
            factors["business_impact"] = 0.8
        elif transaction_amount > 1000:
            factors["business_impact"] = 0.5
        else:
            factors["business_impact"] = 0.2
        
        return factors
    
    def _determine_risk_level(self, risk_factors: Dict[str, float]) -> RiskLevel:
        """Determine overall risk level based on factors"""
        
        # Weighted risk score
        weights = {
            "data_sensitivity": 0.3,
            "violation_severity": 0.4,
            "regulatory_exposure": 0.2,
            "business_impact": 0.1
        }
        
        risk_score = sum(risk_factors[factor] * weights[factor] 
                        for factor in risk_factors)
        
        if risk_score >= 0.8:
            return RiskLevel.EXTREME
        elif risk_score >= 0.6:
            return RiskLevel.HIGH
        elif risk_score >= 0.4:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    def _calculate_business_impact(self, record: Dict[str, Any], 
                                 risk_factors: Dict[str, float]) -> float:
        """Calculate business impact score"""
        
        # Base impact from risk factors
        base_impact = sum(risk_factors.values()) / len(risk_factors)
        
        # Adjust based on record characteristics
        if record.get('data_type') == 'healthcare':
            base_impact *= 1.2  # Healthcare violations have higher impact
        
        if record.get('transaction_amount', 0) > 10000:
            base_impact *= 1.1  # High-value transactions increase impact
        
        return min(base_impact, 1.0)  # Cap at 1.0
    
    def _generate_risk_reasoning(self, risk_level: RiskLevel, 
                               risk_factors: Dict[str, float]) -> str:
        """Generate human-readable risk reasoning"""
        
        high_factors = [factor for factor, score in risk_factors.items() 
                       if score > 0.6]
        
        if high_factors:
            return f"{risk_level.value} risk due to: {', '.join(high_factors)}"
        else:
            return f"{risk_level.value} risk - general assessment"

# Usage example and testing
if __name__ == "__main__":
    # Initialize the intelligent router
    router = IntelligentComplianceRouter()
    
    # Test with different record types
    test_records = [
        {
            "id": "test_1",
            "data_type": "healthcare",
            "has_violation": True,
            "violation_type": "PHI_EXPOSURE",
            "ssn": "123-45-6789",
            "created_at": datetime.now().isoformat(),
            "patient_name": "John Doe"
        },
        {
            "id": "test_2", 
            "data_type": "financial",
            "has_violation": True,
            "violation_type": "GDPR_VIOLATION",
            "consent_given": False,
            "transaction_amount": 5000,
            "created_at": (datetime.now() - timedelta(hours=2)).isoformat()
        },
        {
            "id": "test_3",
            "data_type": "financial",
            "has_violation": False,
            "transaction_amount": 100,
            "created_at": (datetime.now() - timedelta(days=1)).isoformat()
        }
    ]
    
    print("🧠 Intelligent Compliance Router Test Results")
    print("=" * 60)
    
    for record in test_records:
        decision = router.route_record(record)
        print(f"\n📋 Record ID: {record['id']}")
        print(f"🎯 Processing Mode: {decision.processing_mode.value}")
        print(f"⚡ Urgency Level: {decision.urgency_level.value}")
        print(f"⚠️  Risk Level: {decision.risk_level.value}")
        print(f"💡 Reasoning: {decision.reasoning}")
        print(f"⏱️  Est. Processing Time: {decision.estimated_processing_time}s")
        print(f"📊 Business Impact: {decision.business_impact_score:.2f}")
        if decision.regulatory_deadline:
            print(f"📅 Deadline: {decision.regulatory_deadline}")
        print("-" * 40) 