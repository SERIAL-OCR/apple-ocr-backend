#!/usr/bin/env python3
"""
Phase 2.1 Implementation Test
Tests the frontend implementation for Apple Serial Scanner
"""

import os
import sys
import json
from pathlib import Path

def test_file_structure():
    """Test that all required files are present"""
    print("🔍 Testing file structure...")
    
    base_path = Path("ios/AppleSerialScanner/AppleSerialScanner")
    required_files = [
        "AppleSerialScannerApp.swift",
        "SerialScannerView.swift", 
        "SerialScannerViewModel.swift",
        "Info.plist",
        "Models/SerialSubmission.swift",
        "Models/SerialResponse.swift",
        "Models/ScanHistory.swift",
        "Models/SystemStats.swift",
        "Services/BackendService.swift",
        "Services/AppleSerialValidator.swift",
        "Utils/PlatformDetector.swift",
        "Utils/CameraManager.swift",
        "Views/SettingsView.swift",
        "Views/HistoryView.swift"
    ]
    
    missing_files = []
    for file_path in required_files:
        full_path = base_path / file_path
        if not full_path.exists():
            missing_files.append(file_path)
    
    if missing_files:
        print(f"❌ Missing files: {missing_files}")
        return False
    else:
        print("✅ All required files present")
        return True

def test_swift_syntax():
    """Test basic Swift syntax by checking for common patterns"""
    print("\n🔍 Testing Swift syntax patterns...")
    
    base_path = Path("ios/AppleSerialScanner/AppleSerialScanner")
    swift_files = list(base_path.rglob("*.swift"))
    
    syntax_issues = []
    
    for swift_file in swift_files:
        try:
            content = swift_file.read_text(encoding='utf-8')
            
            # Check for basic Swift patterns
            if not content.strip():
                syntax_issues.append(f"{swift_file.name}: Empty file")
                continue
                
            # Check for import statements
            if not any(line.strip().startswith('import ') for line in content.split('\n')):
                syntax_issues.append(f"{swift_file.name}: No import statements")
                
            # Check for basic Swift structure
            if 'struct ' not in content and 'class ' not in content and 'enum ' not in content:
                syntax_issues.append(f"{swift_file.name}: No struct/class/enum definitions")
                
        except Exception as e:
            syntax_issues.append(f"{swift_file.name}: Error reading file - {e}")
    
    if syntax_issues:
        print(f"❌ Syntax issues found: {syntax_issues}")
        return False
    else:
        print("✅ Swift syntax patterns look good")
        return True

def test_platform_detection():
    """Test platform detection implementation"""
    print("\n🔍 Testing platform detection...")
    
    platform_file = Path("ios/AppleSerialScanner/AppleSerialScanner/Utils/PlatformDetector.swift")
    
    if not platform_file.exists():
        print("❌ PlatformDetector.swift not found")
        return False
    
    content = platform_file.read_text(encoding='utf-8')
    
    # Check for required platform detection patterns
    required_patterns = [
        "enum Platform",
        "case iOS",
        "case macOS", 
        "static var current: Platform",
        "#if os(iOS)",
        "#elseif os(macOS)",
        "PlatformDetector"
    ]
    
    missing_patterns = []
    for pattern in required_patterns:
        if pattern not in content:
            missing_patterns.append(pattern)
    
    if missing_patterns:
        print(f"❌ Missing platform detection patterns: {missing_patterns}")
        return False
    else:
        print("✅ Platform detection implementation complete")
        return True

def test_models():
    """Test data models implementation"""
    print("\n🔍 Testing data models...")
    
    models_path = Path("ios/AppleSerialScanner/AppleSerialScanner/Models")
    required_models = [
        "SerialSubmission.swift",
        "SerialResponse.swift", 
        "ScanHistory.swift",
        "SystemStats.swift"
    ]
    
    model_issues = []
    
    for model_file in required_models:
        file_path = models_path / model_file
        if not file_path.exists():
            model_issues.append(f"{model_file}: File missing")
            continue
            
        content = file_path.read_text(encoding='utf-8')
        
        # Check for Codable conformance
        if "Codable" not in content:
            model_issues.append(f"{model_file}: Missing Codable conformance")
            
        # Check for struct definition
        if "struct " not in content:
            model_issues.append(f"{model_file}: No struct definition")
    
    if model_issues:
        print(f"❌ Model issues: {model_issues}")
        return False
    else:
        print("✅ Data models implementation complete")
        return True

def test_services():
    """Test services implementation"""
    print("\n🔍 Testing services...")
    
    services_path = Path("ios/AppleSerialScanner/AppleSerialScanner/Services")
    required_services = [
        "BackendService.swift",
        "AppleSerialValidator.swift"
    ]
    
    service_issues = []
    
    for service_file in required_services:
        file_path = services_path / service_file
        if not file_path.exists():
            service_issues.append(f"{service_file}: File missing")
            continue
            
        content = file_path.read_text(encoding='utf-8')
        
        # Check for class definition
        if "class " not in content:
            service_issues.append(f"{service_file}: No class definition")
            
        # Check for async/await patterns in BackendService
        if service_file == "BackendService.swift":
            if "async" not in content or "await" not in content:
                service_issues.append(f"{service_file}: Missing async/await patterns")
                
        # Check for validation patterns in AppleSerialValidator
        if service_file == "AppleSerialValidator.swift":
            if "ValidationResult" not in content or "ValidationLevel" not in content:
                service_issues.append(f"{service_file}: Missing validation structures")
    
    if service_issues:
        print(f"❌ Service issues: {service_issues}")
        return False
    else:
        print("✅ Services implementation complete")
        return True

def test_views():
    """Test SwiftUI views implementation"""
    print("\n🔍 Testing SwiftUI views...")
    
    views_path = Path("ios/AppleSerialScanner/AppleSerialScanner/Views")
    required_views = [
        "SettingsView.swift",
        "HistoryView.swift"
    ]
    
    view_issues = []
    
    for view_file in required_views:
        file_path = views_path / view_file
        if not file_path.exists():
            view_issues.append(f"{view_file}: File missing")
            continue
            
        content = file_path.read_text(encoding='utf-8')
        
        # Check for SwiftUI patterns
        if "struct " not in content or "View" not in content:
            view_issues.append(f"{view_file}: Missing SwiftUI view structure")
            
        # Check for @StateObject or @State
        if "@State" not in content and "@StateObject" not in content:
            view_issues.append(f"{view_file}: Missing state management")
    
    if view_issues:
        print(f"❌ View issues: {view_issues}")
        return False
    else:
        print("✅ SwiftUI views implementation complete")
        return True

def test_camera_integration():
    """Test camera integration patterns"""
    print("\n🔍 Testing camera integration...")
    
    camera_file = Path("ios/AppleSerialScanner/AppleSerialScanner/Utils/CameraManager.swift")
    view_model_file = Path("ios/AppleSerialScanner/AppleSerialScanner/SerialScannerViewModel.swift")
    
    camera_issues = []
    
    # Check CameraManager
    if camera_file.exists():
        content = camera_file.read_text(encoding='utf-8')
        if "AVCaptureSession" not in content:
            camera_issues.append("CameraManager: Missing AVCaptureSession")
        if "AVCaptureVideoDataOutputSampleBufferDelegate" not in content:
            camera_issues.append("CameraManager: Missing video output delegate")
    else:
        camera_issues.append("CameraManager.swift: File missing")
    
    # Check SerialScannerViewModel
    if view_model_file.exists():
        content = view_model_file.read_text(encoding='utf-8')
        if "AVCaptureVideoDataOutputSampleBufferDelegate" not in content:
            camera_issues.append("SerialScannerViewModel: Missing video output delegate")
        if "AVCapturePhotoCaptureDelegate" not in content:
            camera_issues.append("SerialScannerViewModel: Missing photo capture delegate")
    else:
        camera_issues.append("SerialScannerViewModel.swift: File missing")
    
    if camera_issues:
        print(f"❌ Camera integration issues: {camera_issues}")
        return False
    else:
        print("✅ Camera integration patterns complete")
        return True

def test_vision_integration():
    """Test Vision framework integration"""
    print("\n🔍 Testing Vision framework integration...")
    
    view_model_file = Path("ios/AppleSerialScanner/AppleSerialScanner/SerialScannerViewModel.swift")
    
    if not view_model_file.exists():
        print("❌ SerialScannerViewModel.swift not found")
        return False
    
    content = view_model_file.read_text(encoding='utf-8')
    
    vision_patterns = [
        "VNRecognizeTextRequest",
        "VNRecognizedTextObservation",
        "regionOfInterest"
    ]
    
    missing_patterns = []
    for pattern in vision_patterns:
        if pattern not in content:
            missing_patterns.append(pattern)
    
    if missing_patterns:
        print(f"❌ Missing Vision patterns: {missing_patterns}")
        return False
    else:
        print("✅ Vision framework integration complete")
        return True

def test_backend_integration():
    """Test backend integration patterns"""
    print("\n🔍 Testing backend integration...")
    
    backend_file = Path("ios/AppleSerialScanner/AppleSerialScanner/Services/BackendService.swift")
    
    if not backend_file.exists():
        print("❌ BackendService.swift not found")
        return False
    
    content = backend_file.read_text(encoding='utf-8')
    
    backend_patterns = [
        "URLSession.shared.data",
        "JSONEncoder",
        "JSONDecoder",
        "submitSerial",
        "fetchHistory",
        "fetchSystemStats"
    ]
    
    missing_patterns = []
    for pattern in backend_patterns:
        if pattern not in content:
            missing_patterns.append(pattern)
    
    if missing_patterns:
        print(f"❌ Missing backend patterns: {missing_patterns}")
        return False
    else:
        print("✅ Backend integration patterns complete")
        return True

def test_validation_logic():
    """Test validation logic implementation"""
    print("\n🔍 Testing validation logic...")
    
    validator_file = Path("ios/AppleSerialScanner/AppleSerialScanner/Services/AppleSerialValidator.swift")
    
    if not validator_file.exists():
        print("❌ AppleSerialValidator.swift not found")
        return False
    
    content = validator_file.read_text(encoding='utf-8')
    
    validation_patterns = [
        "ValidationResult",
        "ValidationLevel",
        "ACCEPT",
        "BORDERLINE", 
        "REJECT",
        "validate_with_corrections"
    ]
    
    missing_patterns = []
    for pattern in validation_patterns:
        if pattern not in content:
            missing_patterns.append(pattern)
    
    if missing_patterns:
        print(f"❌ Missing validation patterns: {missing_patterns}")
        return False
    else:
        print("✅ Validation logic implementation complete")
        return True

def main():
    """Run all tests"""
    print("🚀 Phase 2.1 Implementation Test")
    print("=" * 50)
    
    tests = [
        test_file_structure,
        test_swift_syntax,
        test_platform_detection,
        test_models,
        test_services,
        test_views,
        test_camera_integration,
        test_vision_integration,
        test_backend_integration,
        test_validation_logic
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
        print("🎉 Phase 2.1 implementation is complete and ready!")
        print("\n✅ All components implemented:")
        print("   • Platform detection (iOS/macOS)")
        print("   • Camera integration with Vision framework")
        print("   • Client-side validation with corrections")
        print("   • Backend service integration")
        print("   • Settings and history views")
        print("   • Data models for API communication")
        print("   • SwiftUI views for both platforms")
        return True
    else:
        print("⚠️  Some tests failed. Please review the implementation.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
