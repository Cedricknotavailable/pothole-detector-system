#!/usr/bin/env python3
"""
Test script to verify the Apply Filters button functionality for geographic filters.
This test checks that geographic filter changes require clicking Apply Filters.
"""

import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

def test_apply_filters_button():
    """Test that geographic filters require Apply Filters button to take effect."""
    
    # Setup Chrome driver with headless option
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        print("🚀 Starting Apply Filters button test...")
        
        # Navigate to analytics page
        driver.get("http://localhost:5000/analytics")
        
        # Wait for page to load
        wait = WebDriverWait(driver, 10)
        wait.until(EC.presence_of_element_located((By.ID, "globalAdminLevel")))
        
        print("✅ Analytics page loaded")
        
        # Get initial button state
        apply_btn = driver.find_element(By.ID, "applyFiltersBtn")
        initial_btn_text = apply_btn.text
        initial_btn_classes = apply_btn.get_attribute("class")
        
        print(f"📊 Initial Apply button state: '{initial_btn_text}', classes: '{initial_btn_classes}'")
        
        # Change admin level
        admin_level_select = Select(driver.find_element(By.ID, "globalAdminLevel"))
        admin_level_select.select_by_value("municipality")
        
        print("🔄 Changed admin level to municipality")
        
        # Wait a moment for JavaScript to process
        time.sleep(1)
        
        # Check if button state changed
        updated_btn_text = apply_btn.text
        updated_btn_classes = apply_btn.get_attribute("class")
        
        print(f"📊 Updated Apply button state: '{updated_btn_text}', classes: '{updated_btn_classes}'")
        
        # Verify button shows pending changes
        if "pending-changes" in updated_btn_classes:
            print("✅ Apply button correctly shows pending changes")
        else:
            print("❌ Apply button should show pending changes")
            return False
        
        if "Changes Pending" in updated_btn_text:
            print("✅ Apply button text correctly indicates pending changes")
        else:
            print("❌ Apply button text should indicate pending changes")
            return False
        
        # Check if admin level dropdown is highlighted
        admin_level_element = driver.find_element(By.ID, "globalAdminLevel")
        admin_level_classes = admin_level_element.get_attribute("class")
        
        if "changed" in admin_level_classes:
            print("✅ Admin level dropdown correctly highlighted as changed")
        else:
            print("❌ Admin level dropdown should be highlighted as changed")
            return False
        
        # Wait for area dropdown to load
        time.sleep(2)
        
        # Change admin area
        admin_area_select = Select(driver.find_element(By.ID, "globalAdminArea"))
        # Select the first non-"All Areas" option
        options = admin_area_select.options
        if len(options) > 1:
            admin_area_select.select_by_index(1)
            print(f"🔄 Changed admin area to: {options[1].text}")
            
            # Wait a moment for JavaScript to process
            time.sleep(1)
            
            # Check if area dropdown is highlighted
            admin_area_element = driver.find_element(By.ID, "globalAdminArea")
            admin_area_classes = admin_area_element.get_attribute("class")
            
            if "changed" in admin_area_classes:
                print("✅ Admin area dropdown correctly highlighted as changed")
            else:
                print("❌ Admin area dropdown should be highlighted as changed")
                return False
        
        # Click Apply Filters button
        apply_btn.click()
        print("🔘 Clicked Apply Filters button")
        
        # Wait a moment for JavaScript to process
        time.sleep(2)
        
        # Check if button state reset
        final_btn_text = apply_btn.text
        final_btn_classes = apply_btn.get_attribute("class")
        
        print(f"📊 Final Apply button state: '{final_btn_text}', classes: '{final_btn_classes}'")
        
        # Verify button state reset
        if "pending-changes" not in final_btn_classes:
            print("✅ Apply button correctly reset after clicking")
        else:
            print("❌ Apply button should reset after clicking")
            return False
        
        if final_btn_text == "Apply Filters":
            print("✅ Apply button text correctly reset")
        else:
            print("❌ Apply button text should reset to 'Apply Filters'")
            return False
        
        # Check if dropdowns are no longer highlighted
        final_admin_level_classes = driver.find_element(By.ID, "globalAdminLevel").get_attribute("class")
        final_admin_area_classes = driver.find_element(By.ID, "globalAdminArea").get_attribute("class")
        
        if "changed" not in final_admin_level_classes and "changed" not in final_admin_area_classes:
            print("✅ Dropdowns correctly reset highlighting")
        else:
            print("❌ Dropdowns should not be highlighted after applying filters")
            return False
        
        print("🎉 All tests passed! Apply Filters button works correctly.")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False
        
    finally:
        driver.quit()

if __name__ == "__main__":
    success = test_apply_filters_button()
    exit(0 if success else 1)