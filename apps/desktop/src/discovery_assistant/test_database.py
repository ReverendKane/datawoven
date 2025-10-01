#!/usr/bin/env python3
"""
Simple test script to verify SQLAlchemy database setup is working correctly.
Run this from your project root directory.
"""

import sys
from pathlib import Path

# Add the project root to Python path so we can import discovery_assistant
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from discovery_assistant.storage import (
    initialize_database,
    test_database_connection,
    DatabaseSession,
    Respondent,
    Process,
    PainPoint,
    get_database_path
)


def test_basic_operations():
    """Test basic database operations"""
    print("Testing SQLAlchemy database setup...")

    # Test database initialization
    print("1. Testing database initialization...")
    success = initialize_database()
    if success:
        print("   ✓ Database initialized successfully")
        print(f"   Database location: {get_database_path()}")
    else:
        print("   ✗ Database initialization failed")
        return False

    # Test connection
    print("2. Testing database connection...")
    if test_database_connection():
        print("   ✓ Database connection test passed")
    else:
        print("   ✗ Database connection test failed")
        return False

    # Test creating records
    print("3. Testing record creation...")
    try:
        with DatabaseSession() as session:
            # Create a test respondent
            respondent = Respondent(
                full_name="Test User",
                work_email="test@example.com",
                department="Testing",
                role_title="QA Engineer"
            )
            session.add(respondent)

            # Create a test process
            process = Process(
                title="Test Process",
                priority_rank=1,
                notes="This is a test process"
            )
            session.add(process)

            # Create a test pain point
            pain_point = PainPoint(
                pain_name="Test Pain Point",
                priority_rank=1,
                impact=0.8,
                frequency="Daily",
                notes="This is a test pain point"
            )
            session.add(pain_point)

        print("   ✓ Records created successfully")
    except Exception as e:
        print(f"   ✗ Record creation failed: {e}")
        return False

    # Test reading records
    print("4. Testing record retrieval...")
    try:
        with DatabaseSession() as session:
            respondents = session.query(Respondent).all()
            processes = session.query(Process).all()
            pain_points = session.query(PainPoint).all()

            print(f"   Found {len(respondents)} respondent(s)")
            print(f"   Found {len(processes)} process(es)")
            print(f"   Found {len(pain_points)} pain point(s)")

            if respondents:
                resp = respondents[0]
                print(f"   Sample respondent: {resp.full_name} ({resp.work_email})")

        print("   ✓ Records retrieved successfully")
    except Exception as e:
        print(f"   ✗ Record retrieval failed: {e}")
        return False

    print("\n🎉 All tests passed! SQLAlchemy database setup is working correctly.")
    return True


if __name__ == "__main__":
    success = test_basic_operations()
    sys.exit(0 if success else 1)
