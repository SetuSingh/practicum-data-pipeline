"""
Compliance Rules Module
Defines GDPR and HIPAA compliance rules and violation detection patterns

This module centralizes compliance rule definitions, making it easy to:
- Add new regulations (e.g., CCPA, PCI-DSS)
- Modify existing rules without touching processing logic
- Maintain consistent compliance checking across all processors
- Support rule versioning and updates
"""
import re
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

class ViolationType(Enum):
    """Enumeration of different types of compliance violations"""
    PHI_EXPOSURE = "phi_exposure"           # HIPAA: Protected Health Information exposure
    MISSING_CONSENT = "missing_consent"     # GDPR: Missing explicit consent
    DATA_RETENTION = "data_retention"       # GDPR: Data kept too long
    UNAUTHORIZED_ACCESS = "unauthorized_access"  # Both: Improper access
    INSUFFICIENT_ANONYMIZATION = "insufficient_anonymization"  # Both: Poor anonymization

@dataclass
class ViolationResult:
    """Result of a compliance check"""
    violation_type: ViolationType
    field_name: str
    description: str
    severity: str  # "low", "medium", "high", "critical"
    regulation: str  # "HIPAA", "GDPR", "BOTH"

class ComplianceRule(ABC):
    """Abstract base class for compliance rules"""
    
    @abstractmethod
    def check(self, record: Dict[str, Any]) -> List[ViolationResult]:
        """Check a record for compliance violations"""
        pass
    
    @abstractmethod
    def get_rule_name(self) -> str:
        """Get the name of this rule"""
        pass

class HIPAAPhiExposureRule(ComplianceRule):
    """HIPAA rule for detecting exposed Protected Health Information (PHI)"""
    
    def __init__(self):
        # Define PHI patterns that should be masked/encrypted
        self.phi_patterns = {
            'ssn': {
                'pattern': r'\d{3}-\d{2}-\d{4}',
                'description': 'Social Security Number in XXX-XX-XXXX format',
                'severity': 'critical'
            },
            'phone': {
                'pattern': r'\(\d{3}\)\s?\d{3}-\d{4}',
                'description': 'Phone number in (XXX) XXX-XXXX format',
                'severity': 'high'
            },
            'email': {
                'pattern': r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
                'description': 'Email address in standard format',
                'severity': 'high'
            },
            'medical_record_number': {
                'pattern': r'MRN\d{6,}',
                'description': 'Medical Record Number',
                'severity': 'critical'
            }
        }
    
    def check(self, record: Dict[str, Any]) -> List[ViolationResult]:
        """Check for exposed PHI in healthcare records"""
        violations = []
        
        for field_name, pattern_info in self.phi_patterns.items():
            if field_name in record:
                field_value = str(record[field_name])
                
                # Check if field contains unmasked PHI
                if re.search(pattern_info['pattern'], field_value):
                    # Verify it's not already masked (contains ***)
                    if '***' not in field_value:
                        violations.append(ViolationResult(
                            violation_type=ViolationType.PHI_EXPOSURE,
                            field_name=field_name,
                            description=f"Exposed {pattern_info['description']}",
                            severity=pattern_info['severity'],
                            regulation="HIPAA"
                        ))
        
        return violations
    
    def get_rule_name(self) -> str:
        return "HIPAA_PHI_Exposure"

class GDPRConsentRule(ComplianceRule):
    """GDPR rule for checking explicit consent requirements"""
    
    def check(self, record: Dict[str, Any]) -> List[ViolationResult]:
        """Check for GDPR consent violations"""
        violations = []
        
        # Check for missing consent in financial/personal data processing
        if 'consent_given' in record:
            if not record['consent_given']:
                violations.append(ViolationResult(
                    violation_type=ViolationType.MISSING_CONSENT,
                    field_name='consent_given',
                    description="Processing personal data without explicit consent",
                    severity='critical',
                    regulation="GDPR"
                ))
        
        # Check for consent withdrawal not honored
        if 'consent_withdrawn' in record and record.get('consent_withdrawn', False):
            # If consent is withdrawn but data is still being processed
            if record.get('processing_status') == 'active':
                violations.append(ViolationResult(
                    violation_type=ViolationType.UNAUTHORIZED_ACCESS,
                    field_name='processing_status',
                    description="Processing data after consent withdrawal",
                    severity='critical',
                    regulation="GDPR"
                ))
        
        return violations
    
    def get_rule_name(self) -> str:
        return "GDPR_Consent"

class GDPRDataRetentionRule(ComplianceRule):
    """GDPR rule for data retention limits"""
    
    def __init__(self, retention_days: int = 365):
        self.retention_days = retention_days
    
    def check(self, record: Dict[str, Any]) -> List[ViolationResult]:
        """Check for data retention violations"""
        violations = []
        
        # This is a simplified check - in practice, you'd check against
        # actual dates and business requirements
        if 'data_retention_days' in record:
            retention_days = record.get('data_retention_days', 0)
            if retention_days > self.retention_days:
                violations.append(ViolationResult(
                    violation_type=ViolationType.DATA_RETENTION,
                    field_name='data_retention_days',
                    description=f"Data retained for {retention_days} days, exceeds limit of {self.retention_days}",
                    severity='medium',
                    regulation="GDPR"
                ))
        
        return violations
    
    def get_rule_name(self) -> str:
        return "GDPR_Data_Retention"

class PCIDSSRule(ComplianceRule):
    """PCI-DSS rule for detecting exposed credit card information"""
    
    def check(self, record: Dict[str, Any]) -> List[ViolationResult]:
        """Check for PCI-DSS violations in e-commerce data"""
        violations = []
        
        # Check for unmasked credit card numbers
        if 'credit_card' in record:
            card_value = str(record['credit_card'])
            # Look for unmasked credit card pattern (16 digits)
            if re.match(r'\d{4}-?\d{4}-?\d{4}-?\d{4}', card_value):
                if '*' not in card_value:  # Not masked
                    violations.append(ViolationResult(
                        violation_type=ViolationType.PHI_EXPOSURE,
                        field_name='credit_card',
                        description="Exposed credit card number violates PCI-DSS",
                        severity='critical',
                        regulation="PCI-DSS"
                    ))
        
        return violations
    
    def get_rule_name(self) -> str:
        return "PCI_DSS_CardData"

class LocationPrivacyRule(ComplianceRule):
    """Location privacy rule for IoT/GPS data"""
    
    def check(self, record: Dict[str, Any]) -> List[ViolationResult]:
        """Check for location privacy violations"""
        violations = []
        
        # Check if precise location is exposed without consent
        if 'location_lat' in record and 'location_lng' in record:
            lat = record.get('location_lat')
            lng = record.get('location_lng')
            
            # If we have precise coordinates (not generalized)
            if lat and lng and isinstance(lat, (int, float)) and isinstance(lng, (int, float)):
                # Check if coordinates are too precise (more than 2 decimal places)
                if len(str(lat).split('.')[-1]) > 2 or len(str(lng).split('.')[-1]) > 2:
                    violations.append(ViolationResult(
                        violation_type=ViolationType.UNAUTHORIZED_ACCESS,
                        field_name='location_lat,location_lng',
                        description="Precise location data without proper anonymization",
                        severity='high',
                        regulation="GDPR"
                    ))
        
        return violations
    
    def get_rule_name(self) -> str:
        return "Location_Privacy"

class ComplianceRuleEngine:
    """Main engine that orchestrates compliance checking using all rules"""
    
    def __init__(self):
        # Initialize with default rule set
        self.rules: List[ComplianceRule] = [
            HIPAAPhiExposureRule(),
            GDPRConsentRule(),
            GDPRDataRetentionRule(),
            PCIDSSRule(),
            LocationPrivacyRule()
        ]
        
        # Rule sets for different data types
        self.rule_sets = {
            'healthcare': [HIPAAPhiExposureRule(), GDPRConsentRule()],
            'financial': [GDPRConsentRule(), GDPRDataRetentionRule()],
            'ecommerce': [PCIDSSRule(), GDPRConsentRule(), GDPRDataRetentionRule()],
            'iot': [LocationPrivacyRule(), GDPRConsentRule(), GDPRDataRetentionRule()],
            'customer': [GDPRConsentRule(), GDPRDataRetentionRule()],
            'all': self.rules
        }
    
    def add_rule(self, rule: ComplianceRule):
        """Add a custom compliance rule"""
        self.rules.append(rule)
    
    def check_compliance(self, record: Dict[str, Any], data_type: str = 'all') -> List[ViolationResult]:
        """
        Check a record against appropriate compliance rules
        
        Args:
            record: Data record to check
            data_type: Type of data ('healthcare', 'financial', 'all')
            
        Returns:
            List of violation results
        """
        applicable_rules = self.rule_sets.get(data_type, self.rules)
        all_violations = []
        
        for rule in applicable_rules:
            violations = rule.check(record)
            all_violations.extend(violations)
        
        return all_violations
    
    def get_violation_summary(self, violations: List[ViolationResult]) -> Dict[str, Any]:
        """Generate a summary of violations for reporting"""
        if not violations:
            return {'total': 0, 'by_severity': {}, 'by_regulation': {}, 'by_type': {}}
        
        summary = {
            'total': len(violations),
            'by_severity': {},
            'by_regulation': {},
            'by_type': {}
        }
        
        for violation in violations:
            # Count by severity
            severity = violation.severity
            summary['by_severity'][severity] = summary['by_severity'].get(severity, 0) + 1
            
            # Count by regulation
            regulation = violation.regulation
            summary['by_regulation'][regulation] = summary['by_regulation'].get(regulation, 0) + 1
            
            # Count by type
            v_type = violation.violation_type.value
            summary['by_type'][v_type] = summary['by_type'].get(v_type, 0) + 1
        
        return summary

# Global instance for easy access
compliance_engine = ComplianceRuleEngine()

def quick_compliance_check(record: Dict[str, Any], data_type: str = 'all') -> bool:
    """
    Quick compliance check that returns True if violations found
    
    This is optimized for routing decisions in hybrid processing
    """
    violations = compliance_engine.check_compliance(record, data_type)
    return len(violations) > 0

def detailed_compliance_check(record: Dict[str, Any], data_type: str = 'all') -> Dict[str, Any]:
    """
    Detailed compliance check that returns full violation analysis
    
    This is used for comprehensive compliance reporting
    """
    violations = compliance_engine.check_compliance(record, data_type)
    summary = compliance_engine.get_violation_summary(violations)
    
    return {
        'violations': [
            {
                'type': v.violation_type.value,
                'field': v.field_name,
                'description': v.description,
                'severity': v.severity,
                'regulation': v.regulation
            } for v in violations
        ],
        'summary': summary,
        'compliant': len(violations) == 0
    } 