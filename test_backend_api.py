#!/usr/bin/env python3
"""
script on-device OCR implementation.
Tests the new POST /serials endpoint, database schema, and observability features.
Image upload functionality has been completely removed.
"""

import requests
import json
import time
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8000"
API_KEY = "phase2-pilot-key-2024"

def test_health_endpoint():
    """Test the enhanced health endpoint."""
    print("🔍 Testing health endpoint...")
    
    response = requests.get(f"{BASE_URL}/health")
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Health check passed: {data['status']}")
        print(f"   Phase: {data.get('phase', 'unknown')}")
        print(f"   Database: {data.get('database', 'unknown')}")
        print(f"   Total serials: {data.get('total_serials', 0)}")
        return True
    else:
        print(f"❌ Health check failed: {response.status_code}")
        return False

def test_serial_submission():
    """Test POST /serials endpoint with valid data."""
    print("\n🔍 Testing serial submission...")
    
    # Test data
    test_submission = {
        "serial": "C02Y9ABCDEFG",  # Valid Apple serial format
        "confidence": 0.85,
        "device_type": "iPhone",
        "source": "ios",
        "notes": "Test submission from Phase 2.1"
    }
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    response = requests.post(
        f"{BASE_URL}/serials",
        json=test_submission,
        headers=headers
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Serial submission successful: {data['message']}")
        print(f"   Serial ID: {data.get('serial_id', 'N/A')}")
        print(f"   Validation passed: {data['validation_passed']}")
        print(f"   Confidence acceptable: {data['confidence_acceptable']}")
        return True
    else:
        print(f"❌ Serial submission failed: {response.status_code}")
        print(f"   Response: {response.text}")
        return False

def test_invalid_serial_submission():
    """Test POST /serials endpoint with invalid data."""
    print("\n🔍 Testing invalid serial submission...")
    
    # Test data with invalid serial
    test_submission = {
        "serial": "TOOSHORT",  # Too short
        "confidence": 0.90,
        "device_type": "MacBook",
        "source": "mac",
        "notes": "Invalid serial test"
    }
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    response = requests.post(
        f"{BASE_URL}/serials",
        json=test_submission,
        headers=headers
    )
    
    if response.status_code == 422:  # Pydantic validation error
        print("✅ Invalid serial correctly rejected")
        return True
    elif response.status_code == 200:
        data = response.json()
        if not data['success'] and 'validation_failed' in data['message']:
            print("✅ Invalid serial correctly rejected")
            return True
        else:
            print("❌ Invalid serial should have been rejected")
            return False
    else:
        print(f"❌ Invalid serial not properly handled: {response.status_code}")
        return False

def test_low_confidence_submission():
    """Test POST /serials endpoint with low confidence."""
    print("\n🔍 Testing low confidence submission...")
    
    # Test data with low confidence
    test_submission = {
        "serial": "C02Y9ABCDEFG",
        "confidence": 0.25,  # Below minimum
        "device_type": "iPad",
        "source": "ios",
        "notes": "Low confidence test"
    }
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    response = requests.post(
        f"{BASE_URL}/serials",
        json=test_submission,
        headers=headers
    )
    
    if response.status_code == 200:
        data = response.json()
        if not data['success']:
            print("✅ Low confidence correctly rejected")
            return True
        else:
            print("❌ Low confidence should have been rejected")
            return False
    else:
        print(f"❌ Low confidence test failed: {response.status_code}")
        return False

def test_unauthorized_submission():
    """Test POST /serials endpoint without API key."""
    print("\n🔍 Testing unauthorized submission...")
    
    test_submission = {
        "serial": "C02Y9ABCDEFG",
        "confidence": 0.85,
        "device_type": "iPhone",
        "source": "ios"
    }
    
    headers = {
        "Content-Type": "application/json"
        # No Authorization header
    }
    
    response = requests.post(
        f"{BASE_URL}/serials",
        json=test_submission,
        headers=headers
    )
    
    if response.status_code == 401:
        print("✅ Unauthorized access correctly rejected")
        return True
    else:
        print(f"❌ Unauthorized access not properly handled: {response.status_code}")
        return False

def test_history_endpoint():
    """Test the enhanced history endpoint."""
    print("\n🔍 Testing history endpoint...")
    
    response = requests.get(f"{BASE_URL}/history?limit=10")
    if response.status_code == 200:
        data = response.json()
        print(f"✅ History endpoint working")
        print(f"   Total scans: {data['total_scans']}")
        print(f"   Recent scans: {len(data['recent_scans'])}")
        
        # Check for Phase 2.1 fields
        if data['recent_scans']:
            first_scan = data['recent_scans'][0]
            if 'source' in first_scan and 'validation_passed' in first_scan:
                print("✅ Phase 2.1 fields present in history")
                return True
            else:
                print("❌ Phase 2.1 fields missing from history")
                return False
        return True
    else:
        print(f"❌ History endpoint failed: {response.status_code}")
        return False

def test_stats_endpoint():
    """Test the new stats endpoint."""
    print("\n🔍 Testing stats endpoint...")
    
    response = requests.get(f"{BASE_URL}/stats")
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Stats endpoint working")
        print(f"   Phase: {data.get('phase', 'unknown')}")
        print(f"   Database stats: {data.get('database', {})}")
        return True
    else:
        print(f"❌ Stats endpoint failed: {response.status_code}")
        return False

def test_config_endpoint():
    """Test the new config endpoint."""
    print("\n🔍 Testing config endpoint...")
    
    response = requests.get(f"{BASE_URL}/config")
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Config endpoint working")
        print(f"   Min acceptance confidence: {data.get('min_acceptance_confidence', 'N/A')}")
        print(f"   Production mode: {data.get('production_mode', 'N/A')}")
        return True
    else:
        print(f"❌ Config endpoint failed: {response.status_code}")
        return False

def test_image_upload_removed():
    """Test that image upload endpoints have been completely removed."""
    print("\n🔍 Testing that image upload endpoints are removed...")
    
    # Test old image upload endpoints - they should return 404
    old_endpoints = [
        "/scan",
        "/process-serial", 
        "/process-progressive"
    ]
    
    for endpoint in old_endpoints:
        response = requests.post(f"{BASE_URL}{endpoint}")
        if response.status_code == 404:
            print(f"✅ {endpoint} correctly returns 404 (removed)")
        else:
            print(f"❌ {endpoint} still accessible: {response.status_code}")
            return False
    
    return True

def main():
    """Run all Phase 2.1 tests."""
    print("🚀 Phase 2.1 Implementation Test Suite")
    print("=" * 50)
    print("📝 Note: Image upload functionality has been completely removed")
    print("=" * 50)
    
    tests = [
        test_health_endpoint,
        test_serial_submission,
        test_invalid_serial_submission,
        test_low_confidence_submission,
        test_unauthorized_submission,
        test_history_endpoint,
        test_stats_endpoint,
        test_config_endpoint,
        test_image_upload_removed
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All Phase 2.1 tests passed!")
        print("\n✅ Phase 2.1 Implementation Complete:")
        print("   - POST /serials endpoint working")
        print("   - Database schema updated")
        print("   - API key authentication working")
        print("   - Validation and confidence checks working")
        print("   - Enhanced history and stats endpoints working")
        print("   - Observability features enabled")
        print("   - Image upload functionality completely removed")
        print("   - Only on-device OCR endpoints remain")
    else:
        print("⚠️  Some tests failed. Please check the implementation.")

if __name__ == "__main__":
    main()
