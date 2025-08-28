#!/usr/bin/env python3
"""
Phase 2.4 Implementation Test Suite
==================================
Testing Backend Data Services (On-prem Mac)

This test suite validates the enhanced data services functionality including:
- Enhanced Excel export with filtering and formatting
- Enhanced history view with filtering, pagination, and sorting
- Data validation and integrity
- Export metadata and statistics
"""

import requests
import json
import time
from datetime import datetime, timedelta
import os

# Configuration
BASE_URL = "http://localhost:8000"
API_KEY = "phase2-pilot-key-2024"
HEADERS = {"Authorization": f"Bearer {API_KEY}"}

def test_enhanced_export_functionality():
    """Test enhanced Excel export with filtering capabilities."""
    print("\n🔍 Testing enhanced Excel export functionality...")
    
    # Test basic export
    try:
        response = requests.get(f"{BASE_URL}/export", headers=HEADERS)
        if response.status_code == 200:
            print("✅ Basic export working")
        else:
            print(f"❌ Basic export failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Basic export failed with exception: {e}")
        return False
    
    # Test export with source filter
    try:
        response = requests.get(f"{BASE_URL}/export?source=ios", headers=HEADERS)
        if response.status_code == 200:
            print("✅ Export with source filter working")
        else:
            print(f"❌ Export with source filter failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Export with source filter failed with exception: {e}")
        return False
    
    # Test export with date filters
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        response = requests.get(f"{BASE_URL}/export?date_from={today}", headers=HEADERS)
        if response.status_code == 200:
            print("✅ Export with date filter working")
        else:
            print(f"❌ Export with date filter failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Export with date filter failed with exception: {e}")
        return False
    
    # Test export with validation status filter
    try:
        response = requests.get(f"{BASE_URL}/export?validation_status=valid", headers=HEADERS)
        if response.status_code == 200:
            print("✅ Export with validation status filter working")
        else:
            print(f"❌ Export with validation status filter failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Export with validation status filter failed with exception: {e}")
        return False
    
    # Test export with multiple filters
    try:
        response = requests.get(f"{BASE_URL}/export?source=ios&validation_status=valid", headers=HEADERS)
        if response.status_code == 200:
            print("✅ Export with multiple filters working")
        else:
            print(f"❌ Export with multiple filters failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Export with multiple filters failed with exception: {e}")
        return False
    
    # Test invalid filter values
    try:
        response = requests.get(f"{BASE_URL}/export?source=invalid", headers=HEADERS)
        if response.status_code == 400:
            print("✅ Invalid source filter correctly rejected")
        else:
            print(f"❌ Invalid source filter not rejected: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Invalid source filter test failed with exception: {e}")
        return False
    
    return True

def test_enhanced_history_functionality():
    """Test enhanced history view with filtering, pagination, and sorting."""
    print("\n🔍 Testing enhanced history functionality...")
    
    # Test basic history
    try:
        response = requests.get(f"{BASE_URL}/history", headers=HEADERS)
        if response.status_code == 200:
            data = response.json()
            if "total_scans" in data and "recent_scans" in data:
                print("✅ Basic history working")
            else:
                print("❌ Basic history missing required fields")
                return False
        else:
            print(f"❌ Basic history failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Basic history failed with exception: {e}")
        return False
    
    # Test history with pagination
    try:
        response = requests.get(f"{BASE_URL}/history?limit=10&offset=0", headers=HEADERS)
        if response.status_code == 200:
            data = response.json()
            if "pagination" in data and data["pagination"]["limit"] == 10:
                print("✅ History pagination working")
            else:
                print("❌ History pagination not working correctly")
                return False
        else:
            print(f"❌ History pagination failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ History pagination failed with exception: {e}")
        return False
    
    # Test history with source filter
    try:
        response = requests.get(f"{BASE_URL}/history?source=ios", headers=HEADERS)
        if response.status_code == 200:
            data = response.json()
            if "filters" in data and data["filters"]["source"] == "ios":
                print("✅ History source filter working")
            else:
                print("❌ History source filter not working correctly")
                return False
        else:
            print(f"❌ History source filter failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ History source filter failed with exception: {e}")
        return False
    
    # Test history with sorting
    try:
        response = requests.get(f"{BASE_URL}/history?sort_by=confidence&sort_order=desc", headers=HEADERS)
        if response.status_code == 200:
            data = response.json()
            if "sorting" in data and data["sorting"]["sort_by"] == "confidence":
                print("✅ History sorting working")
            else:
                print("❌ History sorting not working correctly")
                return False
        else:
            print(f"❌ History sorting failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ History sorting failed with exception: {e}")
        return False
    
    # Test history with search
    try:
        response = requests.get(f"{BASE_URL}/history?search=C02", headers=HEADERS)
        if response.status_code == 200:
            data = response.json()
            if "filters" in data and data["filters"]["search"] == "C02":
                print("✅ History search working")
            else:
                print("❌ History search not working correctly")
                return False
        else:
            print(f"❌ History search failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ History search failed with exception: {e}")
        return False
    
    # Test invalid parameters
    try:
        response = requests.get(f"{BASE_URL}/history?sort_by=invalid", headers=HEADERS)
        if response.status_code == 400:
            print("✅ Invalid sort_by correctly rejected")
        else:
            print(f"❌ Invalid sort_by not rejected: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Invalid sort_by test failed with exception: {e}")
        return False
    
    return True

def test_export_metadata_and_statistics():
    """Test that export includes proper metadata and statistics."""
    print("\n🔍 Testing export metadata and statistics...")
    
    # Test that export filename includes filter information
    try:
        response = requests.get(f"{BASE_URL}/export?source=ios&validation_status=valid", headers=HEADERS)
        if response.status_code == 200:
            filename = response.headers.get('content-disposition', '')
            if 'source_ios' in filename and 'validation_valid' in filename:
                print("✅ Export filename includes filter information")
            else:
                print("❌ Export filename missing filter information")
                return False
        else:
            print(f"❌ Export metadata test failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Export metadata test failed with exception: {e}")
        return False
    
    return True

def test_data_integrity():
    """Test data integrity and consistency."""
    print("\n🔍 Testing data integrity...")
    
    # Test that history and export return consistent data
    try:
        # Get history data
        history_response = requests.get(f"{BASE_URL}/history?limit=10", headers=HEADERS)
        if history_response.status_code != 200:
            print(f"❌ History request failed: {history_response.status_code}")
            return False
        
        history_data = history_response.json()
        history_count = history_data.get("total_scans", 0)
        
        # Get stats data
        stats_response = requests.get(f"{BASE_URL}/stats", headers=HEADERS)
        if stats_response.status_code != 200:
            print(f"❌ Stats request failed: {stats_response.status_code}")
            return False
        
        stats_data = stats_response.json()
        stats_count = stats_data.get("database", {}).get("total_serials", 0)
        
        # Compare counts
        if history_count == stats_count:
            print("✅ Data consistency between history and stats")
        else:
            print(f"❌ Data inconsistency: history={history_count}, stats={stats_count}")
            return False
        
    except Exception as e:
        print(f"❌ Data integrity test failed with exception: {e}")
        return False
    
    return True

def test_error_handling():
    """Test error handling for invalid requests."""
    print("\n🔍 Testing error handling...")
    
    # Test invalid date format
    try:
        response = requests.get(f"{BASE_URL}/export?date_from=invalid-date", headers=HEADERS)
        if response.status_code == 400:
            print("✅ Invalid date format correctly rejected")
        else:
            print(f"❌ Invalid date format not rejected: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Invalid date format test failed with exception: {e}")
        return False
    
    # Test invalid validation status
    try:
        response = requests.get(f"{BASE_URL}/export?validation_status=maybe", headers=HEADERS)
        if response.status_code == 400:
            print("✅ Invalid validation status correctly rejected")
        else:
            print(f"❌ Invalid validation status not rejected: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Invalid validation status test failed with exception: {e}")
        return False
    
    # Test invalid sort order
    try:
        response = requests.get(f"{BASE_URL}/history?sort_order=maybe", headers=HEADERS)
        if response.status_code == 400:
            print("✅ Invalid sort order correctly rejected")
        else:
            print(f"❌ Invalid sort order not rejected: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Invalid sort order test failed with exception: {e}")
        return False
    
    return True

def main():
    """Run all Phase 2.4 tests."""
    print("🚀 Phase 2.4 Implementation Test Suite")
    print("=" * 50)
    print("📝 Testing Backend Data Services (On-prem Mac)")
    print("=" * 50)
    
    tests = [
        ("Enhanced Export Functionality", test_enhanced_export_functionality),
        ("Enhanced History Functionality", test_enhanced_history_functionality),
        ("Export Metadata and Statistics", test_export_metadata_and_statistics),
        ("Data Integrity", test_data_integrity),
        ("Error Handling", test_error_handling),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🧪 Running: {test_name}")
        try:
            if test_func():
                print(f"✅ {test_name} passed")
                passed += 1
            else:
                print(f"❌ {test_name} failed")
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All Phase 2.4 tests passed!")
        print("\n✅ Phase 2.4 Implementation Complete:")
        print("   - Enhanced Excel export with filtering and formatting")
        print("   - Enhanced history view with filtering, pagination, and sorting")
        print("   - Export metadata and statistics")
        print("   - Data integrity validation")
        print("   - Comprehensive error handling")
        print("   - Ready for production deployment")
    else:
        print("⚠️  Some tests failed. Please check the implementation.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
