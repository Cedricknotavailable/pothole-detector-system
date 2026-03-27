"""
Test Task 8.4: Add audit log CSS to analytics.css

This test verifies that the audit log CSS styles have been added to analytics.css
according to the design specifications.

Requirements validated:
- 4.4: THE System SHALL preserve the audit log table layout and styling
- 4.5: THE System SHALL ensure the audit log section fits within the analytics page layout without overflow
"""

import re


def test_audit_filters_css():
    """Test that .audit-filters CSS is present with correct properties"""
    with open('static/css/analytics.css', 'r') as f:
        content = f.read()
    
    # Check for .audit-filters class
    assert '.audit-filters' in content, ".audit-filters class not found"
    
    # Extract the .audit-filters rule
    audit_filters_match = re.search(r'\.audit-filters\s*\{([^}]+)\}', content)
    assert audit_filters_match, ".audit-filters rule not found"
    
    filters_css = audit_filters_match.group(1)
    
    # Check for required properties
    assert 'display:' in filters_css or 'display :' in filters_css, "display property missing"
    assert 'grid' in filters_css, "grid display value missing"
    assert 'grid-template-columns:' in filters_css or 'grid-template-columns :' in filters_css, "grid-template-columns missing"
    assert 'gap:' in filters_css or 'gap :' in filters_css, "gap property missing"
    assert 'align-items:' in filters_css or 'align-items :' in filters_css, "align-items property missing"
    assert 'margin-bottom:' in filters_css or 'margin-bottom :' in filters_css, "margin-bottom property missing"
    
    print("✓ .audit-filters CSS is present with correct properties")


def test_audit_pagination_css():
    """Test that .audit-pagination CSS is present with correct properties"""
    with open('static/css/analytics.css', 'r') as f:
        content = f.read()
    
    # Check for .audit-pagination class
    assert '.audit-pagination' in content, ".audit-pagination class not found"
    
    # Extract the .audit-pagination rule
    pagination_match = re.search(r'\.audit-pagination\s*\{([^}]+)\}', content)
    assert pagination_match, ".audit-pagination rule not found"
    
    pagination_css = pagination_match.group(1)
    
    # Check for required properties
    assert 'display:' in pagination_css or 'display :' in pagination_css, "display property missing"
    assert 'flex' in pagination_css, "flex display value missing"
    assert 'justify-content:' in pagination_css or 'justify-content :' in pagination_css, "justify-content missing"
    assert 'padding:' in pagination_css or 'padding :' in pagination_css, "padding property missing"
    assert 'border-top:' in pagination_css or 'border-top :' in pagination_css, "border-top property missing"
    
    print("✓ .audit-pagination CSS is present with correct properties")


def test_audit_badge_css():
    """Test that .audit-badge CSS is present with correct properties"""
    with open('static/css/analytics.css', 'r') as f:
        content = f.read()
    
    # Check for .audit-badge base class
    assert '.audit-badge' in content, ".audit-badge class not found"
    
    # Extract the .audit-badge rule
    badge_match = re.search(r'\.audit-badge\s*\{([^}]+)\}', content)
    assert badge_match, ".audit-badge rule not found"
    
    badge_css = badge_match.group(1)
    
    # Check for required properties
    assert 'display:' in badge_css or 'display :' in badge_css, "display property missing"
    assert 'inline-block' in badge_css, "inline-block display value missing"
    assert 'padding:' in badge_css or 'padding :' in badge_css, "padding property missing"
    assert 'border-radius:' in badge_css or 'border-radius :' in badge_css, "border-radius property missing"
    assert 'font-size:' in badge_css or 'font-size :' in badge_css, "font-size property missing"
    assert 'font-weight:' in badge_css or 'font-weight :' in badge_css, "font-weight property missing"
    assert 'text-transform:' in badge_css or 'text-transform :' in badge_css, "text-transform property missing"
    
    print("✓ .audit-badge CSS is present with correct properties")


def test_audit_badge_variants():
    """Test that all audit badge variant classes are present"""
    with open('static/css/analytics.css', 'r') as f:
        content = f.read()
    
    # Check for all badge variants
    variants = [
        'audit-badge--auth',
        'audit-badge--user',
        'audit-badge--report',
        'audit-badge--defect',
        'audit-badge--settings',
        'audit-badge--backup'
    ]
    
    for variant in variants:
        assert f'.{variant}' in content, f".{variant} class not found"
        
        # Check that each variant has background and color
        variant_match = re.search(rf'\.{variant}\s*\{{([^}}]+)\}}', content)
        assert variant_match, f".{variant} rule not found"
        
        variant_css = variant_match.group(1)
        assert 'background:' in variant_css or 'background :' in variant_css, f"{variant} missing background"
        assert 'color:' in variant_css or 'color :' in variant_css, f"{variant} missing color"
    
    print(f"✓ All {len(variants)} audit badge variants are present with correct properties")


def test_audit_detail_cell_css():
    """Test that .audit-detail-cell CSS is present with correct properties"""
    with open('static/css/analytics.css', 'r') as f:
        content = f.read()
    
    # Check for .audit-detail-cell class
    assert '.audit-detail-cell' in content, ".audit-detail-cell class not found"
    
    # Extract the .audit-detail-cell rule
    detail_match = re.search(r'\.audit-detail-cell\s*\{([^}]+)\}', content)
    assert detail_match, ".audit-detail-cell rule not found"
    
    detail_css = detail_match.group(1)
    
    # Check for required properties for text truncation
    assert 'max-width:' in detail_css or 'max-width :' in detail_css, "max-width property missing"
    assert 'overflow:' in detail_css or 'overflow :' in detail_css, "overflow property missing"
    assert 'text-overflow:' in detail_css or 'text-overflow :' in detail_css, "text-overflow property missing"
    assert 'white-space:' in detail_css or 'white-space :' in detail_css, "white-space property missing"
    
    print("✓ .audit-detail-cell CSS is present with correct properties")


def test_audit_detail_kv_css():
    """Test that .audit-detail-kv CSS is present"""
    with open('static/css/analytics.css', 'r') as f:
        content = f.read()
    
    # Check for .audit-detail-kv class
    assert '.audit-detail-kv' in content, ".audit-detail-kv class not found"
    
    # Extract the .audit-detail-kv rule
    kv_match = re.search(r'\.audit-detail-kv\s*\{([^}]+)\}', content)
    assert kv_match, ".audit-detail-kv rule not found"
    
    kv_css = kv_match.group(1)
    
    # Check for required properties
    assert 'display:' in kv_css or 'display :' in kv_css, "display property missing"
    assert 'inline-block' in kv_css, "inline-block display value missing"
    assert 'margin-right:' in kv_css or 'margin-right :' in kv_css, "margin-right property missing"
    
    print("✓ .audit-detail-kv CSS is present with correct properties")


def test_css_responsive_layout():
    """Test that the CSS supports responsive layout"""
    with open('static/css/analytics.css', 'r') as f:
        content = f.read()
    
    # The audit-filters uses grid layout which is responsive
    assert 'grid-template-columns:' in content or 'grid-template-columns :' in content, \
        "Grid layout not found for responsive design"
    
    # The audit-pagination uses flexbox which is responsive
    pagination_match = re.search(r'\.audit-pagination\s*\{([^}]+)\}', content)
    assert pagination_match, ".audit-pagination rule not found"
    pagination_css = pagination_match.group(1)
    assert 'flex' in pagination_css, "Flexbox not used for responsive pagination"
    
    print("✓ CSS supports responsive layout")


def test_no_overflow_issues():
    """Test that CSS prevents overflow issues"""
    with open('static/css/analytics.css', 'r') as f:
        content = f.read()
    
    # Check that audit-detail-cell has overflow handling
    detail_match = re.search(r'\.audit-detail-cell\s*\{([^}]+)\}', content)
    assert detail_match, ".audit-detail-cell rule not found"
    
    detail_css = detail_match.group(1)
    assert 'overflow:' in detail_css or 'overflow :' in detail_css, "overflow property missing"
    assert 'hidden' in detail_css, "overflow:hidden not set"
    assert 'text-overflow:' in detail_css or 'text-overflow :' in detail_css, "text-overflow property missing"
    assert 'ellipsis' in detail_css, "text-overflow:ellipsis not set"
    
    print("✓ CSS prevents overflow issues with proper truncation")


if __name__ == '__main__':
    print("Testing Task 8.4: Audit Log CSS Addition\n")
    
    test_audit_filters_css()
    test_audit_pagination_css()
    test_audit_badge_css()
    test_audit_badge_variants()
    test_audit_detail_cell_css()
    test_audit_detail_kv_css()
    test_css_responsive_layout()
    test_no_overflow_issues()
    
    print("\n✅ All tests passed! Task 8.4 is complete.")
    print("\nSummary:")
    print("- ✓ .audit-filters styling added")
    print("- ✓ .audit-pagination styling added")
    print("- ✓ .audit-badge styling added with 6 action category variants")
    print("- ✓ .audit-detail-cell styling added")
    print("- ✓ .audit-detail-kv styling added")
    print("- ✓ Responsive layout ensured")
    print("- ✓ Overflow prevention implemented")
