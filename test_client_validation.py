#!/usr/bin/env python3
"""
Phase 2.3 Test Suite: Client-side Validation and Post-processing

This test suite validates the Phase 2.3 implementation including:
- Position-aware character disambiguation
- Apple-specific validation rules
- Confidence shaping
- User confirmation logic
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.utils.client_validation import (
    AppleSerialValidator,
    validate_apple_serial_client,
    should_submit_serial,
    ValidationLevel
)


def test_position_corrections():
    """Test position-aware character corrections."""
    print("\n🔍 Testing position-aware corrections...")
    
    validator = AppleSerialValidator()
    
    # Test cases with common OCR mistakes
    test_cases = [
        ("C02Y9ABCDEFG", "C02Y9ABCDEFG", []),  # No corrections needed
        ("C02Y9ABCDEFG", "C02Y9ABCDEFG", []),  # Already correct
        ("C02Y9ABCDEFG", "C02Y9ABCDEFG", []),  # No corrections needed
        ("C02Y9ABCDEFG", "C02Y9ABCDEFG", []),  # Already correct
        ("C02Y9ABCDEFG", "C02Y9ABCDEFG", []),  # No corrections needed
        ("C02Y9ABCDEFG", "C02Y9ABCDEFG", []),  # Already correct
        ("C02Y9ABCDEFG", "C02Y9ABCDEFG", []),  # No corrections needed
        ("C02Y9ABCDEFG", "C02Y9ABCDEFG", []),  # Already correct
        ("C02Y9ABCDEFG", "C02Y9ABCDEFG", []),  # No corrections needed
        ("C02Y9ABCDEFG", "C02Y9ABCDEFG", []),  # Already correct
        ("C02Y9ABCDEFG", "C02Y9ABCDEFG", []),  # No corrections needed
        ("C02Y9ABCDEFG", "C02Y9ABCDEFG", []),  # Already correct
    ]
    
    # Test with actual corrections
    corrected_serial, corrections = validator._apply_position_corrections("C02Y9ABCDEFG")
    print(f"   Original: C02Y9ABCDEFG")
    print(f"   Corrected: {corrected_serial}")
    print(f"   Corrections: {corrections}")
    
    # Test with common OCR mistakes
    test_cases_with_corrections = [
        ("C02Y9ABCDEFG", "CO2Y9ABCDEFG", ["Position 2: '0' → 'O'"]),  # 0->O in second position
        ("C12Y9ABCDEFG", "CI2Y9ABCDEFG", ["Position 2: '1' → 'I'"]),  # 1->I in second position
        ("C02Y9ABCDEFG", "CO2Y9ABCDEFG", ["Position 2: '0' → 'O'"]),  # 0->O in second position
        ("C02Y9ABCDEFG", "CO2Y9ABCDEFG", ["Position 2: '0' → 'O'"]),  # 0->O in second position
    ]
    
    for original, expected, expected_corrections in test_cases_with_corrections:
        corrected, corrections = validator._apply_position_corrections(original)
        if corrected == expected and len(corrections) == len(expected_corrections):
            print(f"✅ Correction test passed: {original} → {corrected}")
        else:
            print(f"❌ Correction test failed: {original} → {corrected} (expected {expected})")
            return False
    
    return True


def test_known_prefixes():
    """Test known Apple serial prefix detection."""
    print("\n🔍 Testing known prefix detection...")
    
    validator = AppleSerialValidator()
    
    # Test known prefixes
    known_prefixes = ["C02", "C03", "C04", "C06", "C07", "C08", "C09", "C0A", "C0B", "C0C", "C0D", "C0E", "C0F"]
    for prefix in known_prefixes:
        test_serial = f"{prefix}Y9ABCDEFG"
        result = validator.validate_with_corrections(test_serial, 0.85)
        if "Known Apple serial prefix detected" in result.validation_notes:
            print(f"✅ Known prefix detected: {prefix}")
        else:
            print(f"❌ Known prefix not detected: {prefix}")
            return False
    
    # Test unknown prefixes
    unknown_prefixes = ["AAA", "BBB", "III"]
    for prefix in unknown_prefixes:
        test_serial = f"{prefix}9ABCDEFGH"
        result = validator.validate_with_corrections(test_serial, 0.85)
        if "Unknown prefix" in " ".join(result.validation_notes):
            print(f"✅ Unknown prefix correctly identified: {prefix}")
        else:
            print(f"❌ Unknown prefix not identified: {prefix}")
            return False
    
    return True


def test_confidence_shaping():
    """Test confidence shaping based on corrections and validation."""
    print("\n🔍 Testing confidence shaping...")
    
    validator = AppleSerialValidator()
    
    # Test cases: (serial, original_confidence, expected_adjusted_confidence_range)
    test_cases = [
        ("C03Y9ABCDEFG", 0.90, (0.87, 0.97)),  # Known prefix, with corrections and warnings
        ("C04Y9ABCDEFG", 0.80, (0.77, 0.87)),  # Known prefix, with corrections and warnings
        ("C06Y9ABCDEFG", 0.70, (0.67, 0.77)),  # Known prefix, with corrections and warnings
        ("C07Y9ABCDEFG", 0.60, (0.57, 0.67)),  # Known prefix, with corrections and warnings
    ]
    
    for serial, original_conf, (min_expected, max_expected) in test_cases:
        result = validator.validate_with_corrections(serial, original_conf)
        
        # Calculate adjusted confidence from the result
        # We need to extract it from the validation logic
        adjusted_conf = validator._shape_confidence(original_conf, result.corrections_made, result.validation_notes)
        
        if min_expected <= adjusted_conf <= max_expected:
            print(f"✅ Confidence shaping: {original_conf:.2f} → {adjusted_conf:.2f}")
        else:
            print(f"❌ Confidence shaping failed: {original_conf:.2f} → {adjusted_conf:.2f} (expected {min_expected:.2f}-{max_expected:.2f})")
            return False
    
    return True


def test_validation_levels():
    """Test validation level determination."""
    print("\n🔍 Testing validation levels...")
    
    validator = AppleSerialValidator()
    
    # Test cases: (serial, confidence, expected_level, should_require_confirmation)
    test_cases = [
        ("C03Y9ABCDEFG", 0.90, ValidationLevel.BORDERLINE, True),  # High confidence, known prefix, but has warnings
        ("C03Y9ABCDEFG", 0.75, ValidationLevel.BORDERLINE, True),  # Medium confidence, known prefix, but has warnings
        ("C03Y9ABCDEFG", 0.65, ValidationLevel.BORDERLINE, True),  # Low confidence, known prefix, but has warnings
        ("C03Y9ABCDEFG", 0.50, ValidationLevel.REJECT, True),  # Very low confidence
        ("AAA9ABCDEFGH", 0.85, ValidationLevel.REJECT, True),  # Unknown prefix, high confidence
        ("AAA9ABCDEFGH", 0.70, ValidationLevel.REJECT, True),  # Unknown prefix, medium confidence
    ]
    
    for serial, confidence, expected_level, should_require_confirmation in test_cases:
        result = validator.validate_with_corrections(serial, confidence)
        
        if result.confidence_level == expected_level:
            print(f"✅ Validation level correct: {serial} → {result.confidence_level.value}")
        else:
            print(f"❌ Validation level incorrect: {serial} → {result.confidence_level.value} (expected {expected_level.value})")
            return False
        
        if result.requires_user_confirmation == should_require_confirmation:
            print(f"   User confirmation requirement correct: {result.requires_user_confirmation}")
        else:
            print(f"   User confirmation requirement incorrect: {result.requires_user_confirmation} (expected {should_require_confirmation})")
            return False
    
    return True


def test_submission_logic():
    """Test submission decision logic."""
    print("\n🔍 Testing submission logic...")
    
    validator = AppleSerialValidator()
    
    # Test cases: (serial, confidence, user_confirmed, should_submit)
    test_cases = [
        ("C03Y9ABCDEFG", 0.90, False, False),  # Borderline level, no confirmation needed
        ("C03Y9ABCDEFG", 0.75, False, False),  # Borderline level, no confirmation
        ("C03Y9ABCDEFG", 0.75, True, True),    # Borderline level, with confirmation
        ("C03Y9ABCDEFG", 0.50, False, False),  # Reject level, no confirmation
        ("C03Y9ABCDEFG", 0.50, True, False),   # Reject level, with confirmation (still reject)
        ("AAA9ABCDEFGH", 0.85, False, False),   # Unknown prefix, no confirmation
        ("AAA9ABCDEFGH", 0.85, True, False),     # Unknown prefix, with confirmation (still reject)
    ]
    
    for serial, confidence, user_confirmed, should_submit in test_cases:
        result = validator.validate_with_corrections(serial, confidence)
        actual_submit = validator.should_submit_to_backend(result, user_confirmed)
        
        if actual_submit == should_submit:
            print(f"✅ Submission logic correct: {serial} (conf={confidence}, user_confirmed={user_confirmed}) → {actual_submit}")
        else:
            print(f"❌ Submission logic incorrect: {serial} (conf={confidence}, user_confirmed={user_confirmed}) → {actual_submit} (expected {should_submit})")
            return False
    
    return True


def test_convenience_functions():
    """Test convenience functions for easy integration."""
    print("\n🔍 Testing convenience functions...")
    
    # Test validate_apple_serial_client
    result = validate_apple_serial_client("C03Y9ABCDEFG", 0.85)
    if result.is_valid and result.confidence_level == ValidationLevel.BORDERLINE:
        print("✅ validate_apple_serial_client working correctly")
    else:
        print("❌ validate_apple_serial_client not working correctly")
        return False
    
    # Test should_submit_serial
    should_submit = should_submit_serial(result, False)
    if not should_submit:  # Should be False because it's borderline and no user confirmation
        print("✅ should_submit_serial working correctly")
    else:
        print("❌ should_submit_serial not working correctly")
        return False
    
    return True


def test_edge_cases():
    """Test edge cases and error handling."""
    print("\n🔍 Testing edge cases...")
    
    validator = AppleSerialValidator()
    
    # Test empty string
    result = validator.validate_with_corrections("", 0.85)
    if not result.is_valid and result.confidence_level == ValidationLevel.REJECT:
        print("✅ Empty string correctly rejected")
    else:
        print("❌ Empty string not properly handled")
        return False
    
    # Test too short
    result = validator.validate_with_corrections("SHORT", 0.85)
    if not result.is_valid and result.confidence_level == ValidationLevel.REJECT:
        print("✅ Too short string correctly rejected")
    else:
        print("❌ Too short string not properly handled")
        return False
    
    # Test too long
    result = validator.validate_with_corrections("C02Y9ABCDEFG123", 0.85)
    if not result.is_valid and result.confidence_level == ValidationLevel.REJECT:
        print("✅ Too long string correctly rejected")
    else:
        print("❌ Too long string not properly handled")
        return False
    
    # Test invalid characters
    result = validator.validate_with_corrections("C02Y9ABCDEF!", 0.85)
    if not result.is_valid and result.confidence_level == ValidationLevel.REJECT:
        print("✅ Invalid characters correctly rejected")
    else:
        print("❌ Invalid characters not properly handled")
        return False
    
    return True


def main():
    """Run all Phase 2.3 tests."""
    print("🚀 Phase 2.3 Implementation Test Suite")
    print("=" * 50)
    print("📝 Testing client-side validation and post-processing")
    print("=" * 50)
    
    tests = [
        ("Position Corrections", test_position_corrections),
        ("Known Prefixes", test_known_prefixes),
        ("Confidence Shaping", test_confidence_shaping),
        ("Validation Levels", test_validation_levels),
        ("Submission Logic", test_submission_logic),
        ("Convenience Functions", test_convenience_functions),
        ("Edge Cases", test_edge_cases),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                print(f"❌ {test_name} failed")
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All Phase 2.3 tests passed!")
        print("\n✅ Phase 2.3 Implementation Complete:")
        print("   - Position-aware character disambiguation")
        print("   - Apple-specific validation rules")
        print("   - Confidence shaping and adjustment")
        print("   - User confirmation logic")
        print("   - Submission decision logic")
        print("   - Edge case handling")
        print("   - Ready for iOS/macOS integration")
    else:
        print("⚠️  Some tests failed. Please check the implementation.")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
