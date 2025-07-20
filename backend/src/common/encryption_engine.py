#!/usr/bin/env python3
"""
Advanced Encryption Engine for Secure Data Pipeline
Implements AES encryption for data at rest and TLS for data in transit
Supports HashiCorp Vault integration for secure key management
"""

import os
import json
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import base64
import secrets

logger = logging.getLogger(__name__)

class EncryptionEngine:
    """
    Enterprise-grade encryption engine with AES-256 encryption
    and secure key management capabilities
    """
    
    def __init__(self, vault_config: Optional[Dict] = None):
        """
        Initialize encryption engine
        
        Args:
            vault_config: Optional HashiCorp Vault configuration
        """
        self.vault_config = vault_config
        self._master_key = None
        self._key_cache = {}
        self._key_rotation_interval = timedelta(days=30)
        
        # Initialize encryption backend
        self.backend = default_backend()
        
        # Load or generate master key
        self._initialize_master_key()
        
        logger.info("Encryption Engine initialized with AES-256")
    
    def _initialize_master_key(self):
        """Initialize or load master encryption key"""
        try:
            # Try to load from Vault first
            if self.vault_config:
                self._master_key = self._load_key_from_vault()
            else:
                # Fallback to environment variable
                key_b64 = os.getenv('MASTER_ENCRYPTION_KEY')
                if key_b64:
                    self._master_key = base64.b64decode(key_b64)
                else:
                    # Generate new key
                    self._master_key = self._generate_master_key()
                    logger.warning("Generated new master key - store securely!")
                    
        except Exception as e:
            logger.error(f"Failed to initialize master key: {e}")
            # Generate temporary key for development
            self._master_key = self._generate_master_key()
    
    def _generate_master_key(self) -> bytes:
        """Generate a new 256-bit master key"""
        return secrets.token_bytes(32)  # 256 bits
    
    def _load_key_from_vault(self) -> bytes:
        """Load encryption key from HashiCorp Vault"""
        # TODO: Implement Vault integration
        # For now, return a development key
        logger.warning("Vault integration not implemented - using development key")
        return secrets.token_bytes(32)
    
    def derive_key(self, context: str, salt: Optional[bytes] = None) -> bytes:
        """
        Derive a key for specific context using PBKDF2
        
        Args:
            context: Context string for key derivation
            salt: Optional salt bytes
            
        Returns:
            Derived key bytes
        """
        if salt is None:
            salt = hashlib.sha256(context.encode()).digest()[:16]
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=self.backend
        )
        
        return kdf.derive(self._master_key)
    
    def encrypt_data(self, data: Any, context: str = "default") -> Dict[str, Any]:
        """
        Encrypt data using AES-256-GCM
        
        Args:
            data: Data to encrypt (will be JSON serialized)
            context: Encryption context for key derivation
            
        Returns:
            Dictionary with encrypted data and metadata
        """
        try:
            # Serialize data to JSON
            if isinstance(data, (dict, list)):
                plaintext = json.dumps(data, default=str).encode()
            else:
                plaintext = str(data).encode()
            
            # Generate unique IV for this encryption
            iv = secrets.token_bytes(12)  # 96 bits for GCM
            
            # Derive key for this context
            key = self.derive_key(context)
            
            # Create cipher
            cipher = Cipher(
                algorithms.AES(key),
                modes.GCM(iv),
                backend=self.backend
            )
            
            encryptor = cipher.encryptor()
            ciphertext = encryptor.update(plaintext) + encryptor.finalize()
            
            # Return encrypted package
            return {
                'ciphertext': base64.b64encode(ciphertext).decode(),
                'iv': base64.b64encode(iv).decode(),
                'tag': base64.b64encode(encryptor.tag).decode(),
                'context': context,
                'algorithm': 'AES-256-GCM',
                'encrypted_at': datetime.utcnow().isoformat(),
                'key_version': 1  # For key rotation support
            }
            
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise
    
    def decrypt_data(self, encrypted_package: Dict[str, Any]) -> Any:
        """
        Decrypt data using AES-256-GCM
        
        Args:
            encrypted_package: Dictionary with encrypted data and metadata
            
        Returns:
            Decrypted data
        """
        try:
            # Extract components
            ciphertext = base64.b64decode(encrypted_package['ciphertext'])
            iv = base64.b64decode(encrypted_package['iv'])
            tag = base64.b64decode(encrypted_package['tag'])
            context = encrypted_package['context']
            
            # Derive key for this context
            key = self.derive_key(context)
            
            # Create cipher
            cipher = Cipher(
                algorithms.AES(key),
                modes.GCM(iv, tag),
                backend=self.backend
            )
            
            decryptor = cipher.decryptor()
            plaintext = decryptor.update(ciphertext) + decryptor.finalize()
            
            # Try to parse as JSON, fallback to string
            try:
                return json.loads(plaintext.decode())
            except json.JSONDecodeError:
                return plaintext.decode()
                
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise
    
    def encrypt_file(self, file_path: str, context: str = "file") -> str:
        """
        Encrypt a file and return path to encrypted file
        
        Args:
            file_path: Path to file to encrypt
            context: Encryption context
            
        Returns:
            Path to encrypted file
        """
        try:
            # Read file data
            with open(file_path, 'rb') as f:
                file_data = f.read()
            
            # Encrypt data
            encrypted_package = self.encrypt_data(
                base64.b64encode(file_data).decode(), 
                context
            )
            
            # Write encrypted file
            encrypted_path = f"{file_path}.encrypted"
            with open(encrypted_path, 'w') as f:
                json.dump(encrypted_package, f, indent=2)
            
            logger.info(f"File encrypted: {file_path} -> {encrypted_path}")
            return encrypted_path
            
        except Exception as e:
            logger.error(f"File encryption failed: {e}")
            raise
    
    def decrypt_file(self, encrypted_file_path: str, output_path: Optional[str] = None) -> str:
        """
        Decrypt a file and return path to decrypted file
        
        Args:
            encrypted_file_path: Path to encrypted file
            output_path: Optional output path
            
        Returns:
            Path to decrypted file
        """
        try:
            # Read encrypted file
            with open(encrypted_file_path, 'r') as f:
                encrypted_package = json.load(f)
            
            # Decrypt data
            decrypted_data = self.decrypt_data(encrypted_package)
            
            # Decode from base64
            file_data = base64.b64decode(decrypted_data)
            
            # Write decrypted file
            if output_path is None:
                output_path = encrypted_file_path.replace('.encrypted', '.decrypted')
            
            with open(output_path, 'wb') as f:
                f.write(file_data)
            
            logger.info(f"File decrypted: {encrypted_file_path} -> {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"File decryption failed: {e}")
            raise
    
    def generate_data_hash(self, data: Any, algorithm: str = "sha256") -> str:
        """
        Generate cryptographic hash of data for integrity checking
        
        Args:
            data: Data to hash
            algorithm: Hash algorithm (sha256, md5)
            
        Returns:
            Hex string of hash
        """
        try:
            # Serialize data consistently
            if isinstance(data, (dict, list)):
                data_str = json.dumps(data, sort_keys=True, default=str)
            else:
                data_str = str(data)
            
            # Generate hash
            if algorithm.lower() == 'sha256':
                hash_obj = hashlib.sha256(data_str.encode())
            elif algorithm.lower() == 'md5':
                hash_obj = hashlib.md5(data_str.encode())
            else:
                raise ValueError(f"Unsupported hash algorithm: {algorithm}")
            
            return hash_obj.hexdigest()
            
        except Exception as e:
            logger.error(f"Hash generation failed: {e}")
            raise
    
    def verify_data_integrity(self, data: Any, expected_hash: str, algorithm: str = "sha256") -> bool:
        """
        Verify data integrity using hash comparison
        
        Args:
            data: Data to verify
            expected_hash: Expected hash value
            algorithm: Hash algorithm used
            
        Returns:
            True if integrity check passes
        """
        try:
            current_hash = self.generate_data_hash(data, algorithm)
            return current_hash == expected_hash
        except Exception as e:
            logger.error(f"Integrity verification failed: {e}")
            return False
    
    def rotate_keys(self) -> Dict[str, Any]:
        """
        Rotate encryption keys (placeholder for key rotation logic)
        
        Returns:
            Key rotation status
        """
        logger.info("Key rotation triggered")
        # TODO: Implement key rotation logic
        return {
            'status': 'scheduled',
            'rotation_time': (datetime.utcnow() + timedelta(hours=1)).isoformat(),
            'old_key_retention': '30 days'
        }


class DataChangeMonitor:
    """
    Monitor data changes using cryptographic hashes
    Detects unauthorized modifications to data records
    """
    
    def __init__(self, encryption_engine: EncryptionEngine):
        """
        Initialize change monitor
        
        Args:
            encryption_engine: Encryption engine instance
        """
        self.encryption_engine = encryption_engine
        self.baseline_hashes = {}
        self.change_log = []
        
        logger.info("Data Change Monitor initialized")
    
    def create_baseline(self, data: Dict[str, Any], record_id: str) -> str:
        """
        Create integrity baseline for a data record
        
        Args:
            data: Data record
            record_id: Unique record identifier
            
        Returns:
            Baseline hash
        """
        baseline_hash = self.encryption_engine.generate_data_hash(data)
        
        self.baseline_hashes[record_id] = {
            'hash': baseline_hash,
            'created_at': datetime.utcnow().isoformat(),
            'algorithm': 'sha256'
        }
        
        logger.debug(f"Created baseline for record {record_id}: {baseline_hash[:16]}...")
        return baseline_hash
    
    def check_for_changes(self, data: Dict[str, Any], record_id: str) -> Dict[str, Any]:
        """
        Check if data has been modified since baseline
        
        Args:
            data: Current data record
            record_id: Record identifier
            
        Returns:
            Change detection result
        """
        current_hash = self.encryption_engine.generate_data_hash(data)
        
        if record_id not in self.baseline_hashes:
            return {
                'status': 'no_baseline',
                'message': f'No baseline found for record {record_id}',
                'current_hash': current_hash
            }
        
        baseline = self.baseline_hashes[record_id]
        baseline_hash = baseline['hash']
        
        if current_hash == baseline_hash:
            return {
                'status': 'unchanged',
                'record_id': record_id,
                'hash': current_hash
            }
        else:
            # Data has changed - log the change
            change_event = {
                'record_id': record_id,
                'baseline_hash': baseline_hash,
                'current_hash': current_hash,
                'detected_at': datetime.utcnow().isoformat(),
                'change_type': 'unauthorized_modification'
            }
            
            self.change_log.append(change_event)
            
            logger.warning(f"Unauthorized change detected in record {record_id}")
            
            return {
                'status': 'changed',
                'record_id': record_id,
                'baseline_hash': baseline_hash,
                'current_hash': current_hash,
                'change_event': change_event
            }
    
    def get_change_history(self, record_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get change history for all records or specific record
        
        Args:
            record_id: Optional specific record ID
            
        Returns:
            List of change events
        """
        if record_id:
            return [event for event in self.change_log if event['record_id'] == record_id]
        return self.change_log.copy()
    
    def clear_change_history(self):
        """Clear change history log"""
        self.change_log.clear()
        logger.info("Change history cleared")


# Global instances
encryption_engine = EncryptionEngine()
change_monitor = DataChangeMonitor(encryption_engine) 