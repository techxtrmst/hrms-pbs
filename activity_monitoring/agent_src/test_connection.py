"""
Test script to diagnose activity tracker connection issues.
Run this to check if the tracker can reach your HRMS server.
"""

import json
import os
import sys

import requests

# Read config
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(BASE_DIR, "config.json")

if not os.path.exists(config_path):
    print("❌ ERROR: config.json not found!")
    print(f"   Expected location: {config_path}")
    print("\n   Please run the setup_tracker.bat file first.")
    sys.exit(1)

with open(config_path) as f:
    cfg = json.load(f)
    SERVER_URL = cfg.get("server_url")
    API_TOKEN = cfg.get("api_token")

print("=" * 60)
print("HRMS Activity Tracker - Connection Test")
print("=" * 60)
print(f"\n📍 Server URL: {SERVER_URL}")
print(f"🔑 Token: {API_TOKEN[:20]}..." if API_TOKEN else "❌ No token found")
print()

# Test 1: Basic connectivity
print("Test 1: Checking internet connectivity...")
try:
    resp = requests.get("https://www.google.com", timeout=5)
    print("✅ Internet connection OK")
except Exception as e:
    print(f"❌ No internet connection: {e}")
    sys.exit(1)

# Test 2: Server reachability
print("\nTest 2: Checking if HRMS server is reachable...")
try:
    # Extract base URL
    base_url = SERVER_URL.split("/activity-tracking")[0]
    resp = requests.get(base_url, timeout=10)
    print(f"✅ Server is reachable (Status: {resp.status_code})")
except requests.exceptions.SSLError as e:
    print(f"❌ SSL Certificate Error: {e}")
    print("   Your server might have an invalid SSL certificate.")
except requests.exceptions.ConnectionError as e:
    print(f"❌ Cannot reach server: {e}")
    print("   Check if the server URL is correct.")
    sys.exit(1)
except Exception as e:
    print(f"⚠️  Warning: {e}")

# Test 3: API endpoint test
print("\nTest 3: Testing activity sync API endpoint...")
test_payload = {
    "app_activities": [],
    "browser_activities": [],
    "system_events": [],
    "is_idle": False,
    "idle_seconds": 0,
}
headers = {"Authorization": f"Token {API_TOKEN}", "Content-Type": "application/json"}

try:
    resp = requests.post(SERVER_URL, json=test_payload, headers=headers, timeout=15)

    if resp.status_code == 201:
        print("✅ API endpoint working! Sync successful!")
        print(f"   Response: {resp.json()}")
    elif resp.status_code == 401:
        print("❌ Authentication failed!")
        print(f"   Response: {resp.text}")
        print("\n   Possible issues:")
        print("   1. Token is invalid or expired")
        print("   2. Device is marked as inactive in admin panel")
        print("   3. Token doesn't match any device")
    elif resp.status_code == 400:
        print("⚠️  Bad request (but endpoint is reachable)")
        print(f"   Response: {resp.text}")
    else:
        print(f"⚠️  Unexpected response: {resp.status_code}")
        print(f"   Response: {resp.text}")

except requests.exceptions.SSLError as e:
    print(f"❌ SSL Error: {e}")
    print("\n   Your server has an SSL certificate problem.")
    print("   Options:")
    print("   1. Fix the SSL certificate on the server")
    print("   2. Use HTTP instead of HTTPS (not recommended)")
except requests.exceptions.ConnectionError as e:
    print(f"❌ Connection Error: {e}")
    print("\n   Cannot connect to the API endpoint.")
    print("   Possible issues:")
    print("   1. Server is down")
    print("   2. Firewall blocking the connection")
    print("   3. Wrong URL in config.json")
except requests.exceptions.Timeout:
    print("❌ Request timed out")
    print("   Server is too slow to respond or not responding.")
except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "=" * 60)
print("Test complete!")
print("=" * 60)
print("\nIf all tests passed, the tracker should work.")
print("If tests failed, share this output with your IT admin.")
print("\nPress Enter to exit...")
input()
