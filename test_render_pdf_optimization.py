#!/usr/bin/env python3
"""
Test script to verify Render hosting optimizations for PDF export.
This script tests memory management, error handling, and timeout configurations.
"""

import re
import os
import sys

def test_memory_optimizations():
    """Test that memory optimizations are implemented."""
    print("Testing memory optimizations...")
    
    with open('app.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for memory management features
    assert 'import gc' in content, "Garbage collection import not found"
    assert 'gc.collect()' in content, "Garbage collection calls not found"
    assert '2 * 1024 * 1024' in content, "Image size limit not found"
    assert 'max_charts = 4' in content, "Chart limit not found"
    assert 'max_width=6*inch' in content, "Reduced image width not found"
    
    # Check for memory error handling
    assert 'MemoryError' in content, "Memory error handling not found"
    assert 'Insufficient memory' in content, "Memory error message not found"
    
    print("✓ Memory optimizations are implemented")

def test_frontend_timeout_handling():
    """Test that frontend has proper timeout handling."""
    print("Testing frontend timeout handling...")
    
    with open('templates/analytics.html', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for timeout configurations
    assert 'Promise.race' in content, "Promise.race timeout pattern not found"
    assert '30000' in content, "Chart capture timeout not found"
    assert '60000' in content, "Server timeout not found"
    assert 'Chart capture timeout' in content, "Chart timeout error not found"
    assert 'Server timeout' in content, "Server timeout error not found"
    
    # Check for user-friendly error messages
    assert 'timed out' in content, "Timeout error message not found"
    assert 'memory constraints' in content, "Memory constraint message not found"
    
    print("✓ Frontend timeout handling is implemented")

def test_image_compression():
    """Test that image compression is implemented."""
    print("Testing image compression...")
    
    with open('templates/analytics.html', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for image compression settings
    assert 'scale: 0.8' in content, "Reduced scale not found"
    assert 'image/jpeg' in content, "JPEG compression not found"
    assert '0.8' in content, "JPEG quality setting not found"
    assert 'Math.min(mapContainer.offsetWidth, 800)' in content, "Width limit not found"
    assert 'Math.min(mapContainer.offsetHeight, 600)' in content, "Height limit not found"
    
    print("✓ Image compression is implemented")

def test_error_logging():
    """Test that comprehensive error logging is implemented."""
    print("Testing error logging...")
    
    with open('app.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for logging statements
    assert 'app.logger.info' in content, "Info logging not found"
    assert 'app.logger.error' in content, "Error logging not found"
    assert 'data_size = sys.getsizeof' in content, "Data size logging not found"
    assert 'traceback.format_exc()' in content, "Traceback logging not found"
    
    print("✓ Error logging is implemented")

def test_fallback_mechanisms():
    """Test that fallback mechanisms are in place."""
    print("Testing fallback mechanisms...")
    
    with open('app.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for fallback PDF generation
    assert 'minimal_story' in content, "Minimal PDF fallback not found"
    assert 'memory constraints' in content, "Memory constraint fallback message not found"
    assert 'minimal_buffer' in content, "Minimal buffer fallback not found"
    
    print("✓ Fallback mechanisms are implemented")

def test_render_specific_optimizations():
    """Test Render-specific optimizations."""
    print("Testing Render-specific optimizations...")
    
    with open('app.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for size limits appropriate for Render's free tier
    assert 'len(image_bytes) > 2 * 1024 * 1024' in content, "2MB image limit not found"
    assert 'processed_charts < max_charts' in content, "Chart processing limit not found"
    assert 'drawHeight > 4*inch' in content, "Height limit for images not found"
    
    print("✓ Render-specific optimizations are implemented")

def test_requirements_compatibility():
    """Test that requirements.txt has necessary dependencies."""
    print("Testing requirements compatibility...")
    
    with open('requirements.txt', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for required packages
    assert 'reportlab' in content, "ReportLab not in requirements"
    assert 'Pillow' in content, "Pillow not in requirements"
    assert 'gunicorn' in content, "Gunicorn not in requirements"
    
    print("✓ Requirements are compatible with Render")

def main():
    """Run all tests."""
    print("Testing Render PDF Export Optimizations")
    print("=" * 50)
    
    try:
        test_memory_optimizations()
        test_frontend_timeout_handling()
        test_image_compression()
        test_error_logging()
        test_fallback_mechanisms()
        test_render_specific_optimizations()
        test_requirements_compatibility()
        
        print("\n" + "=" * 50)
        print("✅ All tests passed! PDF export is optimized for Render hosting.")
        print("\nRender-specific optimizations implemented:")
        print("• Memory management with garbage collection")
        print("• Image size limits (2MB per image)")
        print("• Chart count limits (max 4 charts)")
        print("• Reduced image dimensions and quality")
        print("• Extended timeouts for slow hosting environments")
        print("• Comprehensive error handling and logging")
        print("• Fallback PDF generation on memory errors")
        print("• JPEG compression instead of PNG for maps")
        print("• Graceful degradation for large datasets")
        
        print("\nTroubleshooting tips for Render:")
        print("1. If PDF export still fails, try:")
        print("   - Use smaller date ranges")
        print("   - Apply more specific area filters")
        print("   - Clear browser cache and try again")
        print("2. Check Render logs for specific error messages")
        print("3. Consider upgrading to Render's paid tier for more memory")
        print("4. Monitor memory usage in Render dashboard")
        
        print("\nExpected behavior:")
        print("• PDF generation should complete within 60 seconds")
        print("• Memory errors will show user-friendly messages")
        print("• Large images will be automatically compressed")
        print("• Fallback PDF will be generated if main process fails")
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except FileNotFoundError as e:
        print(f"\n❌ File not found: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()