#!/usr/bin/env python3
"""
Performance Analysis Script
Measures total processing speed from iOS app submission to Excel export generation.
"""

import time
import requests
import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Tuple

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

def measure_api_performance(base_url: str = "http://localhost:8000") -> Dict:
    """Measure API endpoint performance."""
    results = {}
    
    # Test health endpoint
    start_time = time.time()
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        health_time = time.time() - start_time
        results["health_check"] = {
            "time_ms": health_time * 1000,
            "status": response.status_code,
            "success": response.status_code == 200
        }
    except Exception as e:
        results["health_check"] = {
            "time_ms": 0,
            "status": "error",
            "success": False,
            "error": str(e)
        }
    
    return results

def measure_scan_performance(base_url: str = "http://localhost:8000", test_image_path: str = None) -> Dict:
    """Measure scan endpoint performance."""
    results = {}
    
    if not test_image_path or not os.path.exists(test_image_path):
        print(f"Test image not found: {test_image_path}")
        return results
    
    # Test scan submission
    start_time = time.time()
    try:
        with open(test_image_path, 'rb') as f:
            files = {'file': f}
            response = requests.post(f"{base_url}/scan", files=files, timeout=60)
            submission_time = time.time() - start_time
            
            if response.status_code == 200:
                job_data = response.json()
                job_id = job_data.get("job_id")
                
                results["scan_submission"] = {
                    "time_ms": submission_time * 1000,
                    "status": response.status_code,
                    "success": True,
                    "job_id": job_id
                }
                
                # Monitor job progress
                if job_id:
                    job_results = monitor_job_progress(base_url, job_id)
                    results["job_processing"] = job_results
            else:
                results["scan_submission"] = {
                    "time_ms": submission_time * 1000,
                    "status": response.status_code,
                    "success": False,
                    "error": response.text
                }
                
    except Exception as e:
        results["scan_submission"] = {
            "time_ms": 0,
            "status": "error",
            "success": False,
            "error": str(e)
        }
    
    return results

def monitor_job_progress(base_url: str, job_id: str, max_wait: int = 120) -> Dict:
    """Monitor job progress until completion."""
    start_time = time.time()
    progress_updates = []
    
    while time.time() - start_time < max_wait:
        try:
            response = requests.get(f"{base_url}/result/{job_id}", timeout=10)
            if response.status_code == 200:
                job_data = response.json()
                status = job_data.get("status")
                progress = job_data.get("progress", 0)
                message = job_data.get("message", "")
                
                current_time = time.time() - start_time
                progress_updates.append({
                    "time_s": current_time,
                    "progress": progress,
                    "status": status,
                    "message": message
                })
                
                if status in ["completed", "failed"]:
                    # Get final results
                    if status == "completed":
                        results = job_data.get("results", {})
                        processing_time = results.get("processing_time", 0)
                        total_detected = results.get("total_detected", 0)
                        top_confidence = results.get("top_result", {}).get("confidence", 0)
                        
                        return {
                            "total_time_ms": current_time * 1000,
                            "processing_time_ms": processing_time * 1000,
                            "status": status,
                            "progress_updates": progress_updates,
                            "total_detected": total_detected,
                            "top_confidence": top_confidence,
                            "success": True
                        }
                    else:
                        return {
                            "total_time_ms": current_time * 1000,
                            "status": status,
                            "progress_updates": progress_updates,
                            "success": False,
                            "error": job_data.get("error", "Unknown error")
                        }
            
            time.sleep(1)  # Wait 1 second before next check
            
        except Exception as e:
            return {
                "total_time_ms": (time.time() - start_time) * 1000,
                "status": "error",
                "progress_updates": progress_updates,
                "success": False,
                "error": str(e)
            }
    
    return {
        "total_time_ms": max_wait * 1000,
        "status": "timeout",
        "progress_updates": progress_updates,
        "success": False,
        "error": "Job monitoring timeout"
    }

def measure_export_performance(base_url: str = "http://localhost:8000") -> Dict:
    """Measure Excel export performance."""
    results = {}
    
    start_time = time.time()
    try:
        response = requests.get(f"{base_url}/export", timeout=30)
        export_time = time.time() - start_time
        
        if response.status_code == 200:
            # Check if response is Excel file
            content_type = response.headers.get('content-type', '')
            if 'spreadsheet' in content_type or 'excel' in content_type:
                file_size = len(response.content)
                results["excel_export"] = {
                    "time_ms": export_time * 1000,
                    "status": response.status_code,
                    "success": True,
                    "file_size_bytes": file_size,
                    "content_type": content_type
                }
            else:
                results["excel_export"] = {
                    "time_ms": export_time * 1000,
                    "status": response.status_code,
                    "success": False,
                    "error": "Response is not an Excel file"
                }
        else:
            results["excel_export"] = {
                "time_ms": export_time * 1000,
                "status": response.status_code,
                "success": False,
                "error": response.text
            }
            
    except Exception as e:
        results["excel_export"] = {
            "time_ms": 0,
            "status": "error",
            "success": False,
            "error": str(e)
        }
    
    return results

def measure_database_performance() -> Dict:
    """Measure database operations performance."""
    results = {}
    
    try:
        from app.db import fetch_serials
        from app.services.export import generate_excel
        
        # Measure database fetch
        start_time = time.time()
        serials = fetch_serials()
        fetch_time = time.time() - start_time
        
        results["database_fetch"] = {
            "time_ms": fetch_time * 1000,
            "success": True,
            "records_count": len(serials)
        }
        
        # Measure Excel generation
        start_time = time.time()
        temp_path = f"storage/exports/performance_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        excel_path = generate_excel(temp_path)
        excel_time = time.time() - start_time
        
        if os.path.exists(excel_path):
            file_size = os.path.getsize(excel_path)
            results["excel_generation"] = {
                "time_ms": excel_time * 1000,
                "success": True,
                "file_size_bytes": file_size,
                "file_path": excel_path
            }
            
            # Clean up test file
            try:
                os.remove(excel_path)
            except:
                pass
        else:
            results["excel_generation"] = {
                "time_ms": excel_time * 1000,
                "success": False,
                "error": "Excel file not created"
            }
            
    except Exception as e:
        results["database_operations"] = {
            "time_ms": 0,
            "success": False,
            "error": str(e)
        }
    
    return results

def run_comprehensive_performance_test(base_url: str = "http://localhost:8000", test_image_path: str = None) -> Dict:
    """Run comprehensive performance test."""
    print("🚀 Starting Comprehensive Performance Analysis...")
    print(f"📡 Testing API at: {base_url}")
    
    results = {
        "timestamp": datetime.now().isoformat(),
        "base_url": base_url,
        "test_image": test_image_path
    }
    
    # 1. API Health Check
    print("\n1️⃣ Testing API Health...")
    health_results = measure_api_performance(base_url)
    results.update(health_results)
    
    if not health_results.get("health_check", {}).get("success", False):
        print("❌ API health check failed. Stopping test.")
        return results
    
    # 2. Scan Performance (if test image provided)
    if test_image_path:
        print("\n2️⃣ Testing Scan Performance...")
        scan_results = measure_scan_performance(base_url, test_image_path)
        results.update(scan_results)
    
    # 3. Export Performance
    print("\n3️⃣ Testing Excel Export Performance...")
    export_results = measure_export_performance(base_url)
    results.update(export_results)
    
    # 4. Database Performance
    print("\n4️⃣ Testing Database Performance...")
    db_results = measure_database_performance()
    results.update(db_results)
    
    # Calculate total processing time
    total_time = 0
    if scan_results.get("scan_submission", {}).get("success"):
        total_time += scan_results["scan_submission"]["time_ms"]
        if "job_processing" in scan_results and scan_results["job_processing"].get("success"):
            total_time += scan_results["job_processing"]["total_time_ms"]
    
    if export_results.get("excel_export", {}).get("success"):
        total_time += export_results["excel_export"]["time_ms"]
    
    results["total_processing_time_ms"] = total_time
    
    return results

def print_performance_summary(results: Dict):
    """Print a formatted performance summary."""
    print("\n" + "="*60)
    print("📊 PERFORMANCE ANALYSIS SUMMARY")
    print("="*60)
    
    # API Health
    health = results.get("health_check", {})
    if health.get("success"):
        print(f"✅ API Health Check: {health['time_ms']:.2f}ms")
    else:
        print(f"❌ API Health Check: FAILED - {health.get('error', 'Unknown error')}")
    
    # Scan Performance
    scan = results.get("scan_submission", {})
    if scan.get("success"):
        print(f"✅ Scan Submission: {scan['time_ms']:.2f}ms")
        
        job = results.get("job_processing", {})
        if job.get("success"):
            print(f"✅ Job Processing: {job['total_time_ms']:.2f}ms")
            print(f"   📈 Progress Updates: {len(job.get('progress_updates', []))}")
            print(f"   🎯 Detected: {job.get('total_detected', 0)} serials")
            print(f"   📊 Top Confidence: {job.get('top_confidence', 0):.3f}")
        else:
            print(f"❌ Job Processing: FAILED - {job.get('error', 'Unknown error')}")
    else:
        print(f"❌ Scan Submission: FAILED - {scan.get('error', 'Unknown error')}")
    
    # Export Performance
    export = results.get("excel_export", {})
    if export.get("success"):
        print(f"✅ Excel Export: {export['time_ms']:.2f}ms")
        print(f"   📄 File Size: {export.get('file_size_bytes', 0)} bytes")
    else:
        print(f"❌ Excel Export: FAILED - {export.get('error', 'Unknown error')}")
    
    # Database Performance
    db_fetch = results.get("database_fetch", {})
    if db_fetch.get("success"):
        print(f"✅ Database Fetch: {db_fetch['time_ms']:.2f}ms")
        print(f"   📊 Records: {db_fetch.get('records_count', 0)}")
    
    excel_gen = results.get("excel_generation", {})
    if excel_gen.get("success"):
        print(f"✅ Excel Generation: {excel_gen['time_ms']:.2f}ms")
        print(f"   📄 File Size: {excel_gen.get('file_size_bytes', 0)} bytes")
    
    # Total Processing Time
    total_time = results.get("total_processing_time_ms", 0)
    print(f"\n⏱️  TOTAL PROCESSING TIME: {total_time:.2f}ms ({total_time/1000:.2f}s)")
    
    # Performance Assessment
    if total_time < 5000:
        assessment = "🟢 EXCELLENT"
    elif total_time < 10000:
        assessment = "🟡 GOOD"
    elif total_time < 30000:
        assessment = "🟠 ACCEPTABLE"
    else:
        assessment = "🔴 SLOW"
    
    print(f"📈 PERFORMANCE ASSESSMENT: {assessment}")

def main():
    """Main function to run performance analysis."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Performance Analysis for Apple OCR Backend")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL for API")
    parser.add_argument("--image", help="Path to test image file")
    parser.add_argument("--output", help="Output JSON file for results")
    
    args = parser.parse_args()
    
    # Run performance test
    results = run_comprehensive_performance_test(args.url, args.image)
    
    # Print summary
    print_performance_summary(results)
    
    # Save results if output file specified
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\n💾 Results saved to: {args.output}")
    
    return results

if __name__ == "__main__":
    main()
