#!/usr/bin/env python3
"""
Debug script to check notification message construction logic
"""

def test_notification_logic():
    """Test the notification message logic without database operations"""
    
    print("=== Testing Notification Message Logic ===")
    
    # Test scenarios
    scenarios = [
        {"current_count": 1, "threshold": 5, "locked": False},
        {"current_count": 2, "threshold": 5, "locked": False},
        {"current_count": 4, "threshold": 5, "locked": False},
        {"current_count": 5, "threshold": 5, "locked": True},
        {"current_count": 6, "threshold": 5, "locked": True},
    ]
    
    report_title = "Test Pothole Report"
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n--- Scenario {i} ---")
        print(f"Current count: {scenario['current_count']}")
        print(f"Threshold: {scenario['threshold']}")
        print(f"Account locked: {scenario['locked']}")
        
        # Calculate remaining flags (this is the logic from the actual function)
        remaining_flags = max(0, scenario['threshold'] - scenario['current_count'])
        print(f"Remaining flags: {remaining_flags}")
        
        # Construct message (this is the logic from the actual function)
        if scenario['locked']:
            msg = f"Your report '{report_title}' has been flagged as a false report and removed. Your account has been locked due to submitting {scenario['current_count']} false reports."
        else:
            msg = f"Your report '{report_title}' has been flagged as a false report and removed. You have submitted {scenario['current_count']} false report(s). {remaining_flags} more false report(s) will result in account suspension. Please ensure your reports are accurate."
        
        print(f"Message: {msg}")
        print()

if __name__ == '__main__':
    test_notification_logic()