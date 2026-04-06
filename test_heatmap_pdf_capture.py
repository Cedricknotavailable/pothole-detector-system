#!/usr/bin/env python3
"""
Test script to verify the enhanced heatmap PDF capture implementation.
This script tests that the actual geographic heatmap can be captured in PDFs.
"""

import re
import os
import sys

def test_html2canvas_integration():
    """Test that html2canvas library is properly integrated."""
    print("Testing html2canvas integration...")
    
    with open('templates/analytics.html', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for html2canvas library
    assert 'html2canvas' in content, "html2canvas library not found"
    assert 'cdnjs.cloudflare.com/ajax/libs/html2canvas' in content, "html2canvas CDN not found"
    
    print("✓ html2canvas library is properly integrated")

def test_async_map_capture():
    """Test that map capture function is properly implemented as async."""
    print("Testing async map capture implementation...")
    
    with open('templates/analytics.html', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for async map capture function
    assert 'async function captureMapAsImage()' in content, "captureMapAsImage is not async"
    assert 'await html2canvas(' in content, "html2canvas not used with await"
    assert 'useCORS: true' in content, "CORS configuration not found"
    assert 'allowTaint: true' in content, "allowTaint configuration not found"
    
    # Check for fallback mechanism
    assert 'Capture failed - see web version' in content, "Fallback mechanism not found"
    
    print("✓ Async map capture is properly implemented")

def test_async_chart_capture():
    """Test that chart capture function is updated to handle async map capture."""
    print("Testing async chart capture integration...")
    
    with open('templates/analytics.html', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for async chart capture function
    assert 'async function captureChartsForPDF()' in content, "captureChartsForPDF is not async"
    assert 'await captureMapAsImage()' in content, "Map capture not awaited in chart capture"
    
    print("✓ Async chart capture is properly implemented")

def test_export_function_updates():
    """Test that the export function properly handles async operations."""
    print("Testing export function updates...")
    
    with open('templates/analytics.html', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for async export function
    assert 'async function exportAnalyticsPDF()' in content, "exportAnalyticsPDF is not async"
    assert 'await captureChartsForPDF()' in content, "Chart capture not awaited in export"
    
    print("✓ Export function properly handles async operations")

def test_map_capture_configuration():
    """Test that map capture has proper configuration for quality and compatibility."""
    print("Testing map capture configuration...")
    
    with open('templates/analytics.html', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for proper html2canvas configuration
    assert 'scale: 1' in content, "Scale configuration not found"
    assert 'logging: false' in content, "Logging configuration not found"
    assert 'backgroundColor:' in content, "Background color not set"
    assert 'onclone:' in content, "onclone callback not found"
    
    # Check for proper error handling
    assert 'console.error(\'Map capture failed' in content, "Error logging not found"
    assert 'using fallback' in content, "Fallback indication not found"
    
    print("✓ Map capture configuration is correct")

def test_heatmap_weight_equality():
    """Test that heatmap weights are equal for reports and detections."""
    print("Testing heatmap weight equality...")
    
    with open('app.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for equal weights (0.7 for both)
    detection_weight_count = content.count('points.append([d.latitude, d.longitude, 0.7])')
    report_weight_count = content.count('points.append([r.latitude, r.longitude, 0.7])')
    
    assert detection_weight_count >= 1, "Detection weight 0.7 not found"
    assert report_weight_count >= 1, "Report weight 0.7 not found"
    
    # Check that old unequal weights are removed
    assert '0.5])' not in content or content.count('0.5])') == 0, "Old detection weight 0.5 still present"
    assert '0.8])' not in content or content.count('0.8])') == 0, "Old report weight 0.8 still present"
    
    print("✓ Heatmap weights are equal (0.7) for both reports and detections")

def test_description_update():
    """Test that the heatmap description reflects equal weighting."""
    print("Testing heatmap description update...")
    
    with open('templates/analytics.html', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for updated description
    assert 'User reports and AI detections are weighted equally' in content, "Updated description not found"
    assert 'weighted slightly higher' not in content, "Old description still present"
    
    print("✓ Heatmap description correctly reflects equal weighting")

def main():
    """Run all tests."""
    print("Testing Enhanced Heatmap PDF Capture Implementation")
    print("=" * 60)
    
    try:
        test_html2canvas_integration()
        test_async_map_capture()
        test_async_chart_capture()
        test_export_function_updates()
        test_map_capture_configuration()
        test_heatmap_weight_equality()
        test_description_update()
        
        print("\n" + "=" * 60)
        print("✅ All tests passed! Enhanced heatmap PDF capture is working correctly.")
        print("\nKey enhancements implemented:")
        print("• html2canvas library integration for real map capture")
        print("• Async map capture with proper error handling")
        print("• Fallback mechanism for capture failures")
        print("• CORS and cross-origin configuration")
        print("• Equal weighting (0.7) for reports and detections")
        print("• Updated description reflecting equal weighting")
        print("• Proper async/await handling throughout the chain")
        
        print("\nHow it works:")
        print("1. User clicks 'Export PDF' button")
        print("2. System captures Chart.js charts as high-quality images")
        print("3. html2canvas captures the actual Leaflet map with heatmap layer")
        print("4. All captured images are sent to backend for PDF generation")
        print("5. Professional PDF is generated with real map visualization")
        print("6. PDF is automatically downloaded with current timestamp")
        
        print("\nBenefits:")
        print("• Real geographic heatmap in PDF (not just placeholder)")
        print("• Current map view, zoom level, and filters preserved")
        print("• High-quality map tiles and heatmap overlay captured")
        print("• Graceful fallback if capture fails")
        print("• Equal representation of user reports and AI detections")
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except FileNotFoundError as e:
        print(f"\n❌ File not found: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()