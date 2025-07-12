#!/usr/bin/env python3
"""
Database Setup Script for Data Integrity Monitoring System
Initializes PostgreSQL database and runs schema migration
"""

import sys
import os

# Add src to Python path
sys.path.append('src')

from database.postgres_connector import PostgreSQLConnector, create_database_if_not_exists, run_schema_migration

def main():
    print("🚀 Setting up Data Integrity Monitoring Database")
    print("=" * 60)
    
    # Database configuration
    DB_CONFIG = {
        'host': 'localhost',
        'port': 5433,  # Using custom port to avoid conflicts
        'database': 'compliance_db',
        'username': 'admin',
        'password': 'password'
    }
    
    try:
        # Step 1: Create database if it doesn't exist
        print("1️⃣ Creating database if needed...")
        create_database_if_not_exists(**DB_CONFIG)
        print("✅ Database ready")
        
        # Step 2: Connect to database
        print("\n2️⃣ Connecting to database...")
        connector = PostgreSQLConnector(**DB_CONFIG)
        print("✅ Connected successfully")
        
        # Step 3: Run schema migration
        print("\n3️⃣ Running schema migration...")
        run_schema_migration(connector, 'sql/schema.up.sql')
        print("✅ Schema migration completed")
        
        # Step 4: Verify connection
        print("\n4️⃣ Verifying database setup...")
        # Simple verification query
        tables = connector.execute_query("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name;
        """)
        print(f"   Created {len(tables)} tables")
        
        print("\n" + "=" * 60)
        print("🎉 Database setup completed successfully!")
        print("=" * 60)
        
        print("\n📊 Database Connection Info:")
        print(f"   Host: {DB_CONFIG['host']}")
        print(f"   Port: {DB_CONFIG['port']}")
        print(f"   Database: {DB_CONFIG['database']}")
        print(f"   Username: {DB_CONFIG['username']}")
        
        print(f"\n📋 Tables Created: {len(tables)}")
        for table in tables[:10]:  # Show first 10 tables
            print(f"   • {table['table_name']}")
        if len(tables) > 10:
            print(f"   ... and {len(tables) - 10} more")
        
        print("\n🚀 Ready to start the application!")
        print("   Run: ./start_dashboard.sh")
        
    except Exception as e:
        print(f"❌ Setup failed: {e}")
        print(f"   Error details: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()