"""
Test script to verify PostHog integration and trigger test events.

This script:
1. Initializes PostHog client
2. Sends test events
3. Captures a test exception
4. Identifies a test user
"""

import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hrms_core.settings')

import django
django.setup()

from hrms_core.posthog_config import (
    get_posthog_client,
    capture_event,
    capture_exception,
    identify_user,
)
from loguru import logger

def main():
    print("=" * 60)
    print("PostHog Integration Test")
    print("=" * 60)
    print()
    
    # 1. Check if PostHog is initialized
    print("1. Checking PostHog client initialization...")
    client = get_posthog_client()
    if client:
        print("   ✅ PostHog client initialized successfully")
    else:
        print("   ❌ PostHog client not initialized (check API key)")
        return
    print()
    
    # 2. Send a simple test event
    print("2. Sending test event: 'test_app_started'...")
    capture_event(
        event_name="test_app_started",
        distinct_id="test_user_123",
        properties={
            "environment": "development",
            "test_run": True,
            "timestamp": str(django.utils.timezone.now()),
        }
    )
    print("   ✅ Event sent")
    print()
    
    # 3. Identify a test user
    print("3. Identifying test user...")
    identify_user(
        distinct_id="test_user_123",
        properties={
            "email": "test@hrms.com",
            "name": "Test User",
            "role": "admin",
            "company": "Test Company",
        }
    )
    print("   ✅ User identified")
    print()
    
    # 4. Send a feature usage event
    print("4. Sending feature usage event...")
    capture_event(
        event_name="feature_used",
        distinct_id="test_user_123",
        properties={
            "feature_name": "posthog_integration_test",
            "success": True,
            "duration_ms": 150,
        }
    )
    print("   ✅ Feature event sent")
    print()
    
    # 5. Capture a test exception
    print("5. Capturing test exception...")
    try:
        # Intentionally raise an exception
        raise ValueError("This is a test exception to verify PostHog exception tracking")
    except Exception as e:
        logger.exception("Test exception raised")
        capture_exception(
            e,
            distinct_id="test_user_123",
            properties={
                "test": True,
                "context": "posthog_integration_test",
            }
        )
        print("   ✅ Exception captured")
    print()
    
    # 6. Send a completion event
    print("6. Sending test completion event...")
    capture_event(
        event_name="test_completed",
        distinct_id="test_user_123",
        properties={
            "tests_run": 5,
            "all_passed": True,
        }
    )
    print("   ✅ Completion event sent")
    print()
    
    print("=" * 60)
    print("✅ All tests completed successfully!")
    print()
    print("📊 Check your PostHog dashboard at:")
    print("   https://us.i.posthog.com/")
    print()
    print("💡 Events should appear within a few seconds.")
    print("   Look for events from user: test_user_123")
    print("=" * 60)

if __name__ == "__main__":
    main()
