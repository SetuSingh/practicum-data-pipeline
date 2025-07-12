"""
Data Schemas Module
Defines schemas for different data types and provides automatic schema detection

This module centralizes schema definitions, making it easy to:
- Add new data formats and types
- Automatically detect schema based on file content or metadata
- Maintain consistent field definitions across processors
- Support schema evolution and versioning
"""
from pyspark.sql.types import *
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from enum import Enum
import pandas as pd
import json

class DataType(Enum):
    """Enumeration of supported data types"""
    HEALTHCARE = "healthcare"
    FINANCIAL = "financial"
    GENERIC = "generic"
    CUSTOMER = "customer"
    TRANSACTION = "transaction"

class SchemaFormat(Enum):
    """Enumeration of schema formats"""
    SPARK = "spark"
    PANDAS = "pandas"
    JSON = "json"

@dataclass
class FieldDefinition:
    """Definition of a data field with metadata"""
    name: str
    data_type: Union[str, type]
    nullable: bool = True
    description: str = ""
    is_sensitive: bool = False
    compliance_rules: List[str] = None
    
    def __post_init__(self):
        if self.compliance_rules is None:
            self.compliance_rules = []

class SchemaDefinition:
    """Base schema definition with field mappings and metadata"""
    
    def __init__(self, name: str, data_type: DataType, fields: List[FieldDefinition]):
        self.name = name
        self.data_type = data_type
        self.fields = fields
        self.field_map = {field.name: field for field in fields}
    
    def get_spark_schema(self) -> StructType:
        """Convert to Spark StructType schema"""
        spark_fields = []
        
        for field in self.fields:
            # Map Python types to Spark types
            if field.data_type == str:
                spark_type = StringType()
            elif field.data_type == int:
                spark_type = IntegerType()
            elif field.data_type == float:
                spark_type = DoubleType()
            elif field.data_type == bool:
                spark_type = BooleanType()
            elif field.data_type == "datetime":
                spark_type = TimestampType()
            elif field.data_type == "date":
                spark_type = DateType()
            else:
                spark_type = StringType()  # Default fallback
            
            spark_fields.append(StructField(field.name, spark_type, field.nullable))
        
        return StructType(spark_fields)
    
    def get_pandas_dtypes(self) -> Dict[str, str]:
        """Convert to Pandas dtype dictionary"""
        dtype_map = {}
        
        for field in self.fields:
            if field.data_type == str:
                dtype_map[field.name] = 'object'
            elif field.data_type == int:
                dtype_map[field.name] = 'int64'
            elif field.data_type == float:
                dtype_map[field.name] = 'float64'
            elif field.data_type == bool:
                dtype_map[field.name] = 'bool'
            elif field.data_type in ["datetime", "date"]:
                dtype_map[field.name] = 'datetime64[ns]'
            else:
                dtype_map[field.name] = 'object'
        
        return dtype_map
    
    def get_json_schema(self) -> Dict[str, Any]:
        """Convert to JSON schema format"""
        properties = {}
        required_fields = []
        
        for field in self.fields:
            # Map to JSON schema types
            if field.data_type == str:
                json_type = "string"
            elif field.data_type == int:
                json_type = "integer"
            elif field.data_type == float:
                json_type = "number"
            elif field.data_type == bool:
                json_type = "boolean"
            else:
                json_type = "string"
            
            properties[field.name] = {
                "type": json_type,
                "description": field.description
            }
            
            if not field.nullable:
                required_fields.append(field.name)
        
        return {
            "type": "object",
            "properties": properties,
            "required": required_fields
        }
    
    def get_sensitive_fields(self) -> List[str]:
        """Get list of sensitive field names for compliance checking"""
        return [field.name for field in self.fields if field.is_sensitive]

# Define healthcare data schema
HEALTHCARE_SCHEMA = SchemaDefinition(
    name="healthcare_v1",
    data_type=DataType.HEALTHCARE,
    fields=[
        FieldDefinition("id", str, False, "Unique patient identifier"),
        FieldDefinition("patient_name", str, True, "Patient full name", True, ["HIPAA_PHI"]),
        FieldDefinition("ssn", str, True, "Social Security Number", True, ["HIPAA_PHI"]),
        FieldDefinition("phone", str, True, "Phone number", True, ["HIPAA_PHI"]),
        FieldDefinition("email", str, True, "Email address", True, ["HIPAA_PHI"]),
        FieldDefinition("diagnosis", str, True, "Medical diagnosis", True, ["HIPAA_PHI"]),
        FieldDefinition("treatment_date", "datetime", True, "Date of treatment"),
        FieldDefinition("has_violation", bool, True, "Violation flag for testing"),
        FieldDefinition("violation_type", str, True, "Type of violation"),
        FieldDefinition("timestamp", "datetime", True, "Record creation timestamp"),
        FieldDefinition("medical_record_number", str, True, "Medical record number", True, ["HIPAA_PHI"]),
        FieldDefinition("doctor_name", str, True, "Attending physician", True, ["HIPAA_PHI"]),
        FieldDefinition("insurance_id", str, True, "Insurance identifier", True, ["HIPAA_PHI"])
    ]
)

# Define financial data schema
FINANCIAL_SCHEMA = SchemaDefinition(
    name="financial_v1",
    data_type=DataType.FINANCIAL,
    fields=[
        FieldDefinition("id", str, False, "Unique transaction identifier"),
        FieldDefinition("customer_name", str, True, "Customer full name", True, ["GDPR_PII"]),
        FieldDefinition("account_number", str, True, "Account number", True, ["GDPR_PII"]),
        FieldDefinition("transaction_amount", float, True, "Transaction amount"),
        FieldDefinition("transaction_date", "datetime", True, "Transaction date"),
        FieldDefinition("location", str, True, "Transaction location"),
        FieldDefinition("consent_given", bool, True, "GDPR consent status", False, ["GDPR_CONSENT"]),
        FieldDefinition("has_violation", bool, True, "Violation flag for testing"),
        FieldDefinition("violation_type", str, True, "Type of violation"),
        FieldDefinition("timestamp", "datetime", True, "Record creation timestamp"),
        FieldDefinition("customer_id", str, True, "Customer identifier", True, ["GDPR_PII"]),
        FieldDefinition("credit_score", int, True, "Credit score", True, ["GDPR_PII"]),
        FieldDefinition("data_retention_days", int, True, "Data retention period")
    ]
)

# Define generic customer schema
CUSTOMER_SCHEMA = SchemaDefinition(
    name="customer_v1",
    data_type=DataType.CUSTOMER,
    fields=[
        FieldDefinition("id", str, False, "Unique customer identifier"),
        FieldDefinition("name", str, True, "Customer name", True, ["PII"]),
        FieldDefinition("email", str, True, "Email address", True, ["PII"]),
        FieldDefinition("phone", str, True, "Phone number", True, ["PII"]),
        FieldDefinition("address", str, True, "Home address", True, ["PII"]),
        FieldDefinition("date_of_birth", "date", True, "Date of birth", True, ["PII"]),
        FieldDefinition("created_at", "datetime", True, "Account creation date"),
        FieldDefinition("updated_at", "datetime", True, "Last update timestamp")
    ]
)

# Define e-commerce data schema (EXAMPLE)
ECOMMERCE_SCHEMA = SchemaDefinition(
    name="ecommerce_v1", 
    data_type=DataType.CUSTOMER,
    fields=[
        FieldDefinition("order_id", str, False, "Unique order identifier"),
        FieldDefinition("customer_email", str, True, "Customer email", True, ["PII", "GDPR_PII"]),
        FieldDefinition("customer_name", str, True, "Customer name", True, ["PII"]),
        FieldDefinition("credit_card", str, True, "Credit card number", True, ["PCI_DSS"]),
        FieldDefinition("billing_address", str, True, "Billing address", True, ["PII"]),
        FieldDefinition("product_name", str, True, "Product purchased"),
        FieldDefinition("order_amount", float, True, "Order total amount"),
        FieldDefinition("order_date", "datetime", True, "Order date"),
        FieldDefinition("shipping_address", str, True, "Shipping address", True, ["PII"]),
        FieldDefinition("consent_marketing", bool, True, "Marketing consent", False, ["GDPR_CONSENT"]),
        FieldDefinition("timestamp", "datetime", True, "Record timestamp")
    ]
)

# Define IoT sensor data schema (EXAMPLE)
IOT_SCHEMA = SchemaDefinition(
    name="iot_sensors_v1",
    data_type=DataType.GENERIC,
    fields=[
        FieldDefinition("device_id", str, False, "Unique device identifier"),
        FieldDefinition("sensor_type", str, True, "Type of sensor"),
        FieldDefinition("location_lat", float, True, "Latitude", True, ["LOCATION_PII"]),
        FieldDefinition("location_lng", float, True, "Longitude", True, ["LOCATION_PII"]),
        FieldDefinition("temperature", float, True, "Temperature reading"),
        FieldDefinition("humidity", float, True, "Humidity reading"),
        FieldDefinition("user_id", str, True, "Associated user", True, ["PII"]),
        FieldDefinition("reading_timestamp", "datetime", True, "Sensor reading time"),
        FieldDefinition("data_retention_days", int, True, "Data retention period")
    ]
)

class SchemaRegistry:
    """Registry for managing and detecting schemas"""
    
    def __init__(self):
        self.schemas: Dict[str, SchemaDefinition] = {
            'healthcare': HEALTHCARE_SCHEMA,
            'financial': FINANCIAL_SCHEMA,
            'ecommerce': ECOMMERCE_SCHEMA,
            'iot': IOT_SCHEMA,
            'customer': CUSTOMER_SCHEMA
        }
        
        # Field signature patterns for auto-detection
        self.detection_patterns = {
            'healthcare': {
                'required_fields': ['patient_name', 'diagnosis', 'treatment_date'],
                'optional_fields': ['ssn', 'medical_record_number', 'doctor_name'],
                'score_threshold': 0.6
            },
            'financial': {
                'required_fields': ['transaction_amount', 'transaction_date', 'account_number'],
                'optional_fields': ['customer_name', 'consent_given', 'credit_score'],
                'score_threshold': 0.6
            },
            'customer': {
                'required_fields': ['name', 'email'],
                'optional_fields': ['phone', 'address', 'date_of_birth'],
                'score_threshold': 0.5
            }
        }
    
    def register_schema(self, schema: SchemaDefinition):
        """Register a new schema"""
        self.schemas[schema.data_type.value] = schema
    
    def get_schema(self, schema_name: str) -> Optional[SchemaDefinition]:
        """Get schema by name"""
        return self.schemas.get(schema_name)
    
    def detect_schema(self, data_sample: Union[Dict[str, Any], List[Dict[str, Any]], pd.DataFrame]) -> Optional[str]:
        """
        Auto-detect schema based on data sample
        
        Args:
            data_sample: Sample data to analyze
            
        Returns:
            Schema name if detected, None otherwise
        """
        # Extract field names from sample data
        if isinstance(data_sample, pd.DataFrame):
            field_names = set(data_sample.columns.tolist())
        elif isinstance(data_sample, list) and data_sample:
            field_names = set(data_sample[0].keys())
        elif isinstance(data_sample, dict):
            field_names = set(data_sample.keys())
        else:
            return None
        
        best_match = None
        best_score = 0
        
        # Score each schema based on field overlap
        for schema_name, pattern in self.detection_patterns.items():
            score = self._calculate_schema_score(field_names, pattern)
            
            if score > pattern['score_threshold'] and score > best_score:
                best_score = score
                best_match = schema_name
        
        return best_match
    
    def _calculate_schema_score(self, field_names: set, pattern: Dict[str, Any]) -> float:
        """Calculate how well field names match a schema pattern"""
        required_fields = set(pattern['required_fields'])
        optional_fields = set(pattern['optional_fields'])
        
        # Required fields must be present
        required_matches = len(required_fields.intersection(field_names))
        required_score = required_matches / len(required_fields) if required_fields else 1.0
        
        # Optional fields add to the score
        optional_matches = len(optional_fields.intersection(field_names))
        optional_score = optional_matches / len(optional_fields) if optional_fields else 0.0
        
        # Weighted combination
        total_score = (required_score * 0.8) + (optional_score * 0.2)
        
        return total_score
    
    def get_schema_for_file(self, file_path: str, sample_data: Optional[Union[Dict, List, pd.DataFrame]] = None) -> Optional[SchemaDefinition]:
        """
        Get appropriate schema for a file based on path and/or sample data
        
        Args:
            file_path: Path to the data file
            sample_data: Optional sample of the data for detection
            
        Returns:
            SchemaDefinition if found, None otherwise
        """
        # First try filename-based detection
        file_path_lower = file_path.lower()
        
        if any(keyword in file_path_lower for keyword in ['healthcare', 'medical', 'patient', 'hipaa']):
            return self.get_schema('healthcare')
        elif any(keyword in file_path_lower for keyword in ['financial', 'transaction', 'payment', 'gdpr']):
            return self.get_schema('financial')
        elif any(keyword in file_path_lower for keyword in ['customer', 'client', 'user']):
            return self.get_schema('customer')
        
        # If filename doesn't help, try data-based detection
        if sample_data is not None:
            detected_schema_name = self.detect_schema(sample_data)
            if detected_schema_name:
                return self.get_schema(detected_schema_name)
        
        # Fallback to generic schema or None
        return None
    
    def list_schemas(self) -> List[str]:
        """List all available schema names"""
        return list(self.schemas.keys())

# Global schema registry instance
schema_registry = SchemaRegistry()

def get_schema_for_data(data_sample: Union[Dict, List, pd.DataFrame], file_path: str = "") -> Optional[SchemaDefinition]:
    """
    Convenience function to get schema for data
    
    Args:
        data_sample: Sample data for detection
        file_path: Optional file path for filename-based detection
        
    Returns:
        SchemaDefinition if detected, None otherwise
    """
    return schema_registry.get_schema_for_file(file_path, data_sample)

def get_spark_schema(schema_name: str) -> Optional[StructType]:
    """Get Spark schema by name"""
    schema = schema_registry.get_schema(schema_name)
    return schema.get_spark_schema() if schema else None

def get_pandas_dtypes(schema_name: str) -> Optional[Dict[str, str]]:
    """Get Pandas dtypes by schema name"""
    schema = schema_registry.get_schema(schema_name)
    return schema.get_pandas_dtypes() if schema else None 