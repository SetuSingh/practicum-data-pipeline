#!/usr/bin/env python3
"""
HashiCorp Vault Client for Secure Data Pipeline
Manages encryption keys and secrets securely
"""

import hvac
import os
import base64
import logging
from typing import Dict, Optional, Any
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)

class VaultClient:
    """
    HashiCorp Vault client for secure key management
    """
    
    def __init__(self, 
                 vault_url: str = "http://localhost:8200",
                 vault_token: str = None,
                 role_id: str = None,
                 secret_id: str = None):
        """
        Initialize Vault client
        
        Args:
            vault_url: Vault server URL
            vault_token: Vault authentication token (for dev)
            role_id: AppRole role ID (for production)
            secret_id: AppRole secret ID (for production)
        """
        self.vault_url = vault_url
        self.client = hvac.Client(url=vault_url)
        self._token_expiry = None
        
        # Try authentication methods in order of preference
        if vault_token:
            self._authenticate_with_token(vault_token)
        elif role_id and secret_id:
            self._authenticate_with_approle(role_id, secret_id)
        else:
            # Try environment variables
            vault_token = os.getenv('VAULT_TOKEN', 'root-token-2024')  # Default for dev
            role_id = os.getenv('VAULT_ROLE_ID')
            secret_id = os.getenv('VAULT_SECRET_ID')
            
            if role_id and secret_id:
                self._authenticate_with_approle(role_id, secret_id)
            else:
                self._authenticate_with_token(vault_token)
    
    def _authenticate_with_token(self, token: str):
        """Authenticate using Vault token"""
        try:
            self.client.token = token
            if self.client.is_authenticated():
                logger.info("Successfully authenticated to Vault with token")
                # Set expiry far in the future for dev tokens
                self._token_expiry = datetime.now() + timedelta(hours=24)
            else:
                raise Exception("Failed to authenticate with Vault token")
        except Exception as e:
            logger.error(f"Vault token authentication failed: {e}")
            raise
    
    def _authenticate_with_approle(self, role_id: str, secret_id: str):
        """Authenticate using AppRole"""
        try:
            auth_response = self.client.auth.approle.login(
                role_id=role_id,
                secret_id=secret_id
            )
            
            # Set token expiry based on response
            lease_duration = auth_response.get('lease_duration', 3600)
            self._token_expiry = datetime.now() + timedelta(seconds=lease_duration - 300)  # 5 min buffer
            
            logger.info("Successfully authenticated to Vault with AppRole")
            
        except Exception as e:
            logger.error(f"Vault AppRole authentication failed: {e}")
            raise
    
    def _ensure_authenticated(self):
        """Ensure we have a valid authentication token"""
        if not self.client.is_authenticated():
            raise Exception("Not authenticated to Vault")
        
        # Check if token is about to expire
        if self._token_expiry and datetime.now() >= self._token_expiry:
            logger.warning("Vault token is expired or about to expire")
            # In production, you would re-authenticate here
    
    def get_encryption_key(self, key_name: str) -> str:
        """
        Get encryption key from Vault
        
        Args:
            key_name: Name of the encryption key (aes-key, database-key, tokenization-key)
            
        Returns:
            Base64 encoded encryption key
        """
        self._ensure_authenticated()
        
        try:
            response = self.client.secrets.kv.v2.read_secret_version(
                path=f'encryption/{key_name}'
            )
            
            key_data = response['data']['data']
            return key_data['key']
            
        except Exception as e:
            logger.error(f"Failed to retrieve encryption key '{key_name}': {e}")
            # Fallback to default key for development
            logger.warning("Using fallback encryption key for development")
            return base64.b64encode(b'default-key-for-development-32b').decode()
    
    def get_api_key(self, service: str) -> str:
        """
        Get API key for a service
        
        Args:
            service: Service name (prometheus, grafana)
            
        Returns:
            API key string
        """
        self._ensure_authenticated()
        
        try:
            response = self.client.secrets.kv.v2.read_secret_version(
                path=f'api-keys/{service}'
            )
            
            key_data = response['data']['data']
            return key_data['key']
            
        except Exception as e:
            logger.error(f"Failed to retrieve API key for '{service}': {e}")
            # Fallback to default keys
            fallback_keys = {
                'prometheus': 'prometheus_key_2024',
                'grafana': 'grafana_key_2024'
            }
            return fallback_keys.get(service, 'default_key')
    
    def get_database_credentials(self) -> Dict[str, str]:
        """
        Get database credentials from Vault
        
        Returns:
            Dictionary containing database connection parameters
        """
        self._ensure_authenticated()
        
        try:
            response = self.client.secrets.kv.v2.read_secret_version(
                path='database/postgres'
            )
            
            return response['data']['data']
            
        except Exception as e:
            logger.error(f"Failed to retrieve database credentials: {e}")
            # Fallback to default credentials for development
            return {
                'username': 'admin',
                'password': 'password',
                'host': 'localhost',
                'port': '5433',
                'database': 'compliance_db'
            }
    
    def rotate_key(self, key_type: str, key_name: str) -> str:
        """
        Rotate an encryption key
        
        Args:
            key_type: Type of key (encryption, api-keys)
            key_name: Name of the key
            
        Returns:
            New key value
        """
        self._ensure_authenticated()
        
        try:
            # Generate new key
            if key_type == 'encryption':
                import secrets
                new_key = base64.b64encode(secrets.token_bytes(32)).decode()
            else:
                import uuid
                new_key = f"{key_name}_{uuid.uuid4().hex[:8]}"
            
            # Store new key in Vault
            self.client.secrets.kv.v2.create_or_update_secret(
                path=f'{key_type}/{key_name}',
                secret={
                    'key': new_key,
                    'created_at': datetime.utcnow().isoformat(),
                    'rotated_at': datetime.utcnow().isoformat(),
                    'purpose': f'Rotated {key_type} key'
                }
            )
            
            logger.info(f"Successfully rotated key: {key_type}/{key_name}")
            return new_key
            
        except Exception as e:
            logger.error(f"Failed to rotate key '{key_type}/{key_name}': {e}")
            raise
    
    def list_keys(self, key_type: str = None) -> Dict[str, Any]:
        """
        List all keys in Vault
        
        Args:
            key_type: Optional key type filter
            
        Returns:
            Dictionary of keys and metadata
        """
        self._ensure_authenticated()
        
        try:
            paths = ['encryption', 'api-keys', 'database']
            if key_type:
                paths = [key_type]
            
            keys = {}
            for path in paths:
                try:
                    response = self.client.secrets.kv.v2.list_secrets(path=path)
                    keys[path] = response['data']['keys']
                except Exception as e:
                    logger.warning(f"Could not list keys for path '{path}': {e}")
                    keys[path] = []
            
            return keys
            
        except Exception as e:
            logger.error(f"Failed to list keys: {e}")
            return {}
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check Vault health and authentication status
        
        Returns:
            Health status dictionary
        """
        try:
            # Check if Vault is reachable
            health = self.client.sys.read_health_status()
            
            # Check authentication
            is_authenticated = self.client.is_authenticated()
            
            # Check token expiry
            token_valid = True
            if self._token_expiry:
                token_valid = datetime.now() < self._token_expiry
            
            return {
                'vault_reachable': True,
                'vault_sealed': health.get('sealed', True),
                'authenticated': is_authenticated,
                'token_valid': token_valid,
                'token_expiry': self._token_expiry.isoformat() if self._token_expiry else None,
                'vault_version': health.get('version', 'unknown')
            }
            
        except Exception as e:
            logger.error(f"Vault health check failed: {e}")
            return {
                'vault_reachable': False,
                'error': str(e),
                'authenticated': False,
                'token_valid': False
            }

# Global Vault client instance
_vault_client = None

def get_vault_client() -> VaultClient:
    """
    Get singleton Vault client instance
    
    Returns:
        VaultClient instance
    """
    global _vault_client
    
    if _vault_client is None:
        try:
            _vault_client = VaultClient()
        except Exception as e:
            logger.error(f"Failed to initialize Vault client: {e}")
            # Create a mock client for development
            _vault_client = MockVaultClient()
    
    return _vault_client

class MockVaultClient:
    """
    Mock Vault client for development when Vault is not available
    """
    
    def get_encryption_key(self, key_name: str) -> str:
        """Return default encryption key for development"""
        return base64.b64encode(f'dev-key-{key_name}-32bytes-long!'.encode()[:32]).decode()
    
    def get_api_key(self, service: str) -> str:
        """Return default API key for development"""
        return f'{service}_key_2024'
    
    def get_database_credentials(self) -> Dict[str, str]:
        """Return default database credentials for development"""
        return {
            'username': 'admin',
            'password': 'password',
            'host': 'localhost',
            'port': '5433',
            'database': 'compliance_db'
        }
    
    def health_check(self) -> Dict[str, Any]:
        """Return mock health status"""
        return {
            'vault_reachable': False,
            'mock_mode': True,
            'authenticated': True,
            'token_valid': True
        }
    
    def rotate_key(self, key_type: str, key_name: str) -> str:
        """Mock key rotation"""
        import uuid
        return f'mock-{key_name}-{uuid.uuid4().hex[:8]}'
    
    def list_keys(self, key_type: str = None) -> Dict[str, Any]:
        """Return mock key list"""
        return {
            'encryption': ['aes-key', 'database-key', 'tokenization-key'],
            'api-keys': ['prometheus', 'grafana'],
            'database': ['postgres']
        } 