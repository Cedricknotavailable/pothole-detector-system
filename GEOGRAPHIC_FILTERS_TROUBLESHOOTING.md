# Geographic Filters Troubleshooting Guide

## Issue Description
User reports that geographic filters in the analytics page are broken:
1. All admin level filter options output province options
2. Specific areas for regions and municipalities are gone
3. Graphs and charts don't respond to geo filters

## Debug Version Implemented

I've added debug logging to help identify the issue. The following functions now include console logging:

### 1. `loadAreas()` Function
- Logs the admin level being loaded
- Shows number of features loaded from JSON file
- Displays first 3 area names for each level
- Shows total unique areas found

### 2. `refreshAll()` Function  
- Logs when charts are being refreshed
- Shows current filter parameters

### 3. `onGlobalLevelChange()` Function
- Logs when admin level changes
- Confirms when areas are loaded and charts refresh

## Troubleshooting Steps

### Step 1: Check Browser Console
1. Open the analytics page
2. Press F12 to open Developer Tools
3. Go to Console tab
4. Change the Admin Level dropdown from Province to Region
5. Look for debug messages starting with 🔍, 📊, 🌍, ✅, 🔄

**Expected Console Output:**
```
🔄 Admin level changed to: region
🔍 Loading areas for level: region
📊 Loaded 17 features for region
🌍 Region 0: Ilocos
🌍 Region 1: Cagayan Valley  
🌍 Region 2: Central Luzon
✅ Found 17 unique areas for region
✅ Areas loaded, refreshing charts...
🔄 Refreshing all charts and KPIs with filters: admin_level=region&start_date=...
```

### Step 2: Check Network Tab
1. In Developer Tools, go to Network tab
2. Change admin level and watch for requests
3. Look for requests to:
   - `/static/data/regions.json`
   - `/static/data/provinces.json` 
   - `/static/data/municipalities.json`
   - `/api/analytics/overview?admin_level=...`

### Step 3: Verify Data Files
The following files should exist and be accessible:
- `/static/data/regions.json` (17 regions)
- `/static/data/provinces.json` (81 provinces)
- `/static/data/municipalities.json` (1,634 municipalities)

### Step 4: Test Each Admin Level

#### Region Level
- Should show: Ilocos, Cagayan Valley, Central Luzon, CALABARZON, etc.
- Console should show: `🌍 Region X: [region name]`

#### Province Level  
- Should show: Abra, Agusan del Norte, Agusan del Sur, etc.
- Console should show: `🏛️ Province X: [province name]`

#### Municipality Level
- Should show: Bangued, Butuan, Prosperidad, etc.
- Console should show: `🏘️ Municipality X: [municipality name]`

## Common Issues & Solutions

### Issue 1: All Levels Show Same Data
**Cause:** Browser cache or old JavaScript
**Solution:** 
- Hard refresh (Ctrl+F5)
- Clear browser cache
- Try incognito/private browsing mode

### Issue 2: Console Shows Errors
**Possible Errors:**
- `❌ loadAreas error: Failed to fetch` → Data files missing
- `❌ loadAreas error: Unexpected token` → Corrupted JSON files
- `TypeError: Cannot read property 'NAME_1'` → Data structure issue

### Issue 3: Charts Don't Update
**Check:**
- Console shows `🔄 Refreshing all charts...` message
- Network tab shows API requests with correct parameters
- No JavaScript errors in console

### Issue 4: Dropdown Shows "All Areas" Only
**Possible Causes:**
- Data file not loading (check Network tab)
- Property names incorrect (check console logs)
- JavaScript error preventing population

## Expected Behavior

### When Working Correctly:
1. **Region Level:** Shows 17 Philippine regions
2. **Province Level:** Shows 81 provinces  
3. **Municipality Level:** Shows 1,634+ municipalities
4. **Charts Update:** All charts refresh when area filter changes
5. **API Calls:** Backend receives correct admin_level and admin_area parameters

### Data Structure:
- **Regions:** Use `name` or `REGION` property
- **Provinces:** Use `NAME_1` property
- **Municipalities:** Use `NAME_2` property

## Quick Fix Commands

If issues persist, try these in browser console:

```javascript
// Test loadAreas function directly
loadAreas('globalAdminArea', 'region');
loadAreas('globalAdminArea', 'province'); 
loadAreas('globalAdminArea', 'municipality');

// Check current filter values
console.log('Current filters:', getGlobalFilters().toString());

// Test data file access
fetch('/static/data/regions.json').then(r => r.json()).then(d => console.log('Regions:', d.features.length));
```

## Rollback Instructions

If debug logging is too verbose, remove the console.log statements:

1. Remove all lines containing `console.log` from the functions
2. Keep the core functionality intact
3. The debug version doesn't change any logic, only adds logging

## Contact Information

If the issue persists after following these steps:
1. Share the console output from Step 1
2. Share any error messages from Network tab
3. Specify which browser and version you're using
4. Confirm if the issue occurs on both localhost and Render