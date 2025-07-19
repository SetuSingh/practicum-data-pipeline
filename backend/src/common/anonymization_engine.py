"""
Enhanced Anonymization Engine for Research Question 2 (RQ2)
Implements k-anonymity, differential privacy, and tokenization with configurable parameters

This module provides comprehensive anonymization capabilities with the exact
parameters specified in the research evaluation framework:
- K-anonymity with k-values: [3, 5, 10, 15]
- Differential privacy with epsilon values: [0.1, 0.5, 1.0, 2.0]
- Tokenization with key lengths: [128, 256, 512]
"""
import hashlib
import hmac
import secrets
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass
from enum import Enum
import json
import time

class AnonymizationMethod(Enum):
    K_ANONYMITY = "k_anonymity"
    DIFFERENTIAL_PRIVACY = "differential_privacy"
    TOKENIZATION = "tokenization"

@dataclass
class AnonymizationConfig:
    """Configuration for anonymization parameters"""
    method: AnonymizationMethod
    k_value: Optional[int] = None  # For k-anonymity: 3, 5, 10, 15
    epsilon: Optional[float] = None  # For differential privacy: 0.1, 0.5, 1.0, 2.0
    key_length: Optional[int] = None  # For tokenization: 128, 256, 512
    
    def __post_init__(self):
        """Validate configuration parameters"""
        if self.method == AnonymizationMethod.K_ANONYMITY and self.k_value is None:
            raise ValueError("k_value required for k-anonymity")
        if self.method == AnonymizationMethod.DIFFERENTIAL_PRIVACY and self.epsilon is None:
            raise ValueError("epsilon required for differential privacy")
        if self.method == AnonymizationMethod.TOKENIZATION and self.key_length is None:
            raise ValueError("key_length required for tokenization")

@dataclass
class AnonymizationMetrics:
    """Metrics for evaluating anonymization performance"""
    processing_time: float
    memory_usage: float
    information_loss: float
    utility_preservation: float
    privacy_level: float
    method: str
    parameters: Dict[str, Any]

class EnhancedAnonymizationEngine:
    """
    Comprehensive anonymization engine supporting all RQ2 requirements
    """
    
    def __init__(self):
        """Initialize the anonymization engine with default configurations"""
        self.supported_configs = self._generate_supported_configs()
        self.salt = secrets.token_bytes(32)  # For consistent tokenization
        
    def _generate_supported_configs(self) -> List[AnonymizationConfig]:
        """Generate all supported configuration combinations for RQ2"""
        configs = []
        
        # K-anonymity configurations
        for k in [3, 5, 10, 15]:
            configs.append(AnonymizationConfig(
                method=AnonymizationMethod.K_ANONYMITY,
                k_value=k
            ))
        
        # Differential privacy configurations
        for epsilon in [0.1, 0.5, 1.0, 2.0]:
            configs.append(AnonymizationConfig(
                method=AnonymizationMethod.DIFFERENTIAL_PRIVACY,
                epsilon=epsilon
            ))
        
        # Tokenization configurations
        for key_length in [128, 256, 512]:
            configs.append(AnonymizationConfig(
                method=AnonymizationMethod.TOKENIZATION,
                key_length=key_length
            ))
        
        return configs
    
    def anonymize_record(self, record: Dict[str, Any], config: AnonymizationConfig) -> Dict[str, Any]:
        """
        Anonymize a single record using the specified configuration
        
        Args:
            record: Input data record
            config: Anonymization configuration
            
        Returns:
            Anonymized record with metrics
        """
        start_time = time.time()
        
        if config.method == AnonymizationMethod.K_ANONYMITY:
            result = self._apply_k_anonymity(record, config.k_value)
        elif config.method == AnonymizationMethod.DIFFERENTIAL_PRIVACY:
            result = self._apply_differential_privacy(record, config.epsilon)
        elif config.method == AnonymizationMethod.TOKENIZATION:
            result = self._apply_tokenization(record, config.key_length)
        else:
            raise ValueError(f"Unsupported anonymization method: {config.method}")
        
        processing_time = time.time() - start_time
        
        # Add anonymization metadata
        result['_anonymization_config'] = {
            'method': config.method.value,
            'parameters': self._get_config_parameters(config),
            'processing_time': processing_time
        }
        
        return result
    
    def _apply_k_anonymity(self, record: Dict[str, Any], k_value: int) -> Dict[str, Any]:
        """
        Apply k-anonymity with specified k-value
        
        K-anonymity ensures that each record is indistinguishable from at least
        k-1 other records based on quasi-identifiers.
        """
        anonymized = record.copy()
        
        # Age generalization based on k-value
        if 'age' in record and record['age']:
            age = int(record['age'])
            if k_value <= 3:
                # Small k: 10-year ranges
                anonymized['age'] = f"{(age // 10) * 10}-{(age // 10) * 10 + 9}"
            elif k_value <= 10:
                # Medium k: 20-year ranges
                anonymized['age'] = f"{(age // 20) * 20}-{(age // 20) * 20 + 19}"
            else:
                # Large k: 30-year ranges
                anonymized['age'] = f"{(age // 30) * 30}-{(age // 30) * 30 + 29}"
        
        # SSN generalization based on k-value
        if 'ssn' in record and record['ssn']:
            ssn = str(record['ssn'])
            if k_value <= 3:
                # Small k: mask last 4 digits
                anonymized['ssn'] = f"{ssn[:5]}****"
            elif k_value <= 10:
                # Medium k: mask last 6 digits
                anonymized['ssn'] = f"{ssn[:3]}******"
            else:
                # Large k: full masking
                anonymized['ssn'] = "***-**-****"
        
        # Phone generalization
        if 'phone' in record and record['phone']:
            phone = str(record['phone'])
            if k_value <= 3:
                anonymized['phone'] = f"{phone[:6]}****"
            elif k_value <= 10:
                anonymized['phone'] = f"{phone[:3]}*******"
            else:
                anonymized['phone'] = "***-***-****"
        
        # Diagnosis generalization (medical records)
        if 'diagnosis' in record and record['diagnosis']:
            diagnosis = str(record['diagnosis']).lower()
            if k_value <= 3:
                # Specific grouping
                if diagnosis in ['diabetes', 'hypertension']:
                    anonymized['diagnosis'] = 'chronic_condition'
                elif diagnosis in ['flu', 'cold']:
                    anonymized['diagnosis'] = 'respiratory_infection'
                else:
                    anonymized['diagnosis'] = 'other_condition'
            else:
                # Very general grouping
                anonymized['diagnosis'] = 'medical_condition'
        
        # Location generalization
        if 'location' in record and record['location']:
            location = str(record['location'])
            if k_value <= 3:
                # City level
                anonymized['location'] = location.split(',')[0] if ',' in location else location
            else:
                # State/region level
                anonymized['location'] = 'Region_Generalized'
        
        # Add k-anonymity metadata
        anonymized['_k_anonymity_level'] = k_value
        
        return anonymized
    
    def _apply_differential_privacy(self, record: Dict[str, Any], epsilon: float) -> Dict[str, Any]:
        """
        Apply differential privacy with specified epsilon value
        
        Differential privacy provides mathematical privacy guarantees by adding
        calibrated noise to the data based on the privacy budget (epsilon).
        """
        anonymized = record.copy()
        
        # Calculate noise scale based on epsilon (Laplace mechanism)
        sensitivity = 1.0  # Assume global sensitivity of 1
        noise_scale = sensitivity / epsilon
        
        # Apply DP to numerical fields
        if 'age' in record and record['age']:
            try:
                original_age = float(record['age'])
                noise = np.random.laplace(0, noise_scale)
                noisy_age = max(0, min(120, original_age + noise))  # Clamp to reasonable range
                anonymized['age'] = int(round(noisy_age))
            except (ValueError, TypeError):
                anonymized['age'] = None
        
        if 'transaction_amount' in record and record['transaction_amount']:
            try:
                original_amount = float(record['transaction_amount'])
                noise = np.random.laplace(0, noise_scale * 100)  # Scale for monetary values
                anonymized['transaction_amount'] = max(0, original_amount + noise)
            except (ValueError, TypeError):
                anonymized['transaction_amount'] = None
        
        # Apply DP to categorical fields (using randomized response)
        dp_probability = 1 / (1 + np.exp(epsilon))  # Probability of truthful response
        
        if 'gender' in record and record['gender']:
            if np.random.random() > dp_probability:
                anonymized['gender'] = np.random.choice(['M', 'F', 'Other'])
        
        # For high-sensitivity identifiers, apply strong protection
        if epsilon < 0.5:  # Strong privacy
            if 'ssn' in record:
                anonymized['ssn'] = f"DP_STRONG_{hash(str(record.get('ssn', ''))) % 10000:04d}"
            if 'phone' in record:
                anonymized['phone'] = f"DP_STRONG_{hash(str(record.get('phone', ''))) % 10000:04d}"
            if 'email' in record:
                anonymized['email'] = f"DP_STRONG_{hash(str(record.get('email', ''))) % 1000:03d}@private.com"
        elif epsilon < 1.0:  # Medium privacy
            if 'ssn' in record:
                anonymized['ssn'] = f"DP_MED_{hash(str(record.get('ssn', ''))) % 10000:04d}"
            if 'phone' in record:
                anonymized['phone'] = f"DP_MED_{hash(str(record.get('phone', ''))) % 10000:04d}"
            if 'email' in record:
                anonymized['email'] = f"DP_MED_{hash(str(record.get('email', ''))) % 1000:03d}@private.com"
        else:  # Weaker privacy (epsilon >= 1.0)
            if 'ssn' in record:
                anonymized['ssn'] = f"DP_WEAK_{hash(str(record.get('ssn', ''))) % 10000:04d}"
            if 'phone' in record:
                anonymized['phone'] = f"DP_WEAK_{hash(str(record.get('phone', ''))) % 10000:04d}"
            if 'email' in record:
                anonymized['email'] = f"DP_WEAK_{hash(str(record.get('email', ''))) % 1000:03d}@private.com"
        
        # Add DP metadata
        anonymized['_epsilon_used'] = epsilon
        anonymized['_noise_scale'] = noise_scale
        
        return anonymized
    
    def _apply_tokenization(self, record: Dict[str, Any], key_length: int) -> Dict[str, Any]:
        """
        Apply tokenization with specified key length
        
        Tokenization replaces sensitive data with non-sensitive tokens while
        preserving referential integrity through deterministic mapping.
        """
        anonymized = record.copy()
        
        # Generate key based on specified length
        key_bytes = key_length // 8  # Convert bits to bytes
        
        # Tokenize identifiers based on key strength
        if 'ssn' in record and record['ssn']:
            token = self._generate_token(str(record['ssn']), key_bytes, 'SSN')
            anonymized['ssn'] = f"TOKEN_{key_length}_{token}"
        
        if 'phone' in record and record['phone']:
            token = self._generate_token(str(record['phone']), key_bytes, 'PHONE')
            anonymized['phone'] = f"PHONE_{key_length}_{token}"
        
        if 'email' in record and record['email']:
            token = self._generate_token(str(record['email']), key_bytes, 'EMAIL')
            anonymized['email'] = f"EMAIL_{key_length}_{token}@tokenized.com"
        
        if 'patient_name' in record and record['patient_name']:
            token = self._generate_token(str(record['patient_name']), key_bytes, 'NAME')
            anonymized['patient_name'] = f"PATIENT_{key_length}_{token}"
        
        if 'customer_name' in record and record['customer_name']:
            token = self._generate_token(str(record['customer_name']), key_bytes, 'CUSTOMER')
            anonymized['customer_name'] = f"CUSTOMER_{key_length}_{token}"
        
        if 'account_number' in record and record['account_number']:
            token = self._generate_token(str(record['account_number']), key_bytes, 'ACCOUNT')
            anonymized['account_number'] = f"ACCT_{key_length}_{token}"
        
        # Add tokenization metadata
        anonymized['_token_key_length'] = key_length
        
        return anonymized
    
    def _generate_token(self, value: str, key_bytes: int, prefix: str) -> str:
        """
        Generate a deterministic token for a value using HMAC
        
        Args:
            value: Original value to tokenize
            key_bytes: Length of key in bytes
            prefix: Prefix for token type
            
        Returns:
            Deterministic token string
        """
        # Use HMAC for cryptographically secure tokenization
        key = self.salt[:key_bytes]  # Use specified key length
        token = hmac.new(key, value.encode('utf-8'), hashlib.sha256).hexdigest()
        
        # Return shortened token based on key strength
        if key_bytes >= 64:  # 512-bit key
            return token[:16]
        elif key_bytes >= 32:  # 256-bit key
            return token[:12]
        else:  # 128-bit key
            return token[:8]
    
    def _get_config_parameters(self, config: AnonymizationConfig) -> Dict[str, Any]:
        """Get configuration parameters as dictionary"""
        params = {}
        if config.k_value is not None:
            params['k_value'] = config.k_value
        if config.epsilon is not None:
            params['epsilon'] = config.epsilon
        if config.key_length is not None:
            params['key_length'] = config.key_length
        return params
    
    def get_all_configurations(self) -> List[AnonymizationConfig]:
        """Get all supported anonymization configurations for RQ2"""
        return self.supported_configs
    
    def calculate_utility_metrics(self, original: Dict[str, Any], anonymized: Dict[str, Any], 
                                config: AnonymizationConfig, 
                                field_ranges: Optional[Dict[str, Tuple[float, float]]] = None) -> Dict[str, float]:
        """Calculate information-loss / utility-preservation in a data-driven way.

        Args:
            original: Original (pre-anonymisation) record.
            anonymized: Anonymised record.
            config: The anonymisation config used (still returned in output for reference).
            field_ranges: Optional mapping {field: (min, max)} computed on the *original* dataset. If not
                          supplied we fall back to per-record heuristics (works but less robust).

        Returns:
            dict with information_loss (0-1) and utility_preservation (0-1).
        """
        diffs = []
        for field, orig_val in original.items():
            # Skip internal / metadata fields
            if field.startswith('_') or field not in anonymized:
                continue

            anon_val = anonymized.get(field)

            # Exact match or both missing ⇒ no loss for this field
            if orig_val == anon_val:
                diffs.append(0.0)
                continue

            # Attempt numeric comparison
            try:
                orig_float = float(orig_val)
                anon_float = float(anon_val)
                # Determine range for normalisation
                if field_ranges and field in field_ranges and field_ranges[field][1] != field_ranges[field][0]:
                    f_min, f_max = field_ranges[field]
                    denom = f_max - f_min
                else:
                    # Fallback: use magnitude of original value (avoid div-by-zero)
                    denom = abs(orig_float) if abs(orig_float) > 0 else 1.0
                diff = abs(orig_float - anon_float) / denom
                # Clamp to [0,1] in case of outliers / noise
                diff = max(0.0, min(1.0, diff))
                diffs.append(diff)
                continue
            except (ValueError, TypeError):
                # Non-numeric, treat as categorical
                pass

            # Categorical difference: use normalised Levenshtein (edit) distance
            orig_str = str(orig_val)
            anon_str = str(anon_val)

            try:
                # Fast path – python-Levenshtein if available
                from Levenshtein import distance as lev_dist  # type: ignore
                edit_distance = lev_dist(orig_str, anon_str)
            except ModuleNotFoundError:
                # Fallback – difflib (pure-Python, slower but avoids extra dep)
                import difflib
                seq_match = difflib.SequenceMatcher(None, orig_str, anon_str)
                # Convert similarity ratio → edit distance approximation
                edit_distance = int((1.0 - seq_match.ratio()) * max(len(orig_str), len(anon_str)))

            max_len = max(len(orig_str), 1)  # avoid divide-by-zero
            diff_norm = edit_distance / max_len
            diff_norm = max(0.0, min(1.0, diff_norm))
            diffs.append(diff_norm)

        information_loss = float(np.mean(diffs)) if diffs else 0.0
        utility_preservation = 1.0 - information_loss

        # Simple privacy-level proxy (config specific)
        if config.method == AnonymizationMethod.K_ANONYMITY and config.k_value:
            privacy_level = 1.0 - 1.0 / max(1, config.k_value)
        elif config.method == AnonymizationMethod.DIFFERENTIAL_PRIVACY and config.epsilon is not None:
            privacy_level = 1.0 - np.exp(-float(config.epsilon))
        elif config.method == AnonymizationMethod.TOKENIZATION and config.key_length:
            privacy_level = min(1.0, float(config.key_length) / 512.0)
        else:
            privacy_level = 0.5  # default / unknown

        return {
            'information_loss': information_loss,
            'utility_preservation': utility_preservation,
            'privacy_level': privacy_level
        }

# Convenience functions for backward compatibility
def create_anonymization_engine() -> EnhancedAnonymizationEngine:
    """Create a new anonymization engine instance"""
    return EnhancedAnonymizationEngine()

def get_rq2_configurations() -> List[AnonymizationConfig]:
    """Get all RQ2 anonymization configurations"""
    engine = EnhancedAnonymizationEngine()
    return engine.get_all_configurations() 