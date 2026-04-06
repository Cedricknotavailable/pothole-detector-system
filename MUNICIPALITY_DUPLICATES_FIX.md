# Municipality Filter Duplicates Fix

## Issue Description
The municipality filter in the analytics page was showing province names instead of municipality names, and had duplicate entries.

## Root Cause
The `loadAreas()` function was using a generic property extraction approach that tried multiple properties in order: `name || REGION || NAME_1 || NAME_2`. For municipalities, this caused it to pick up `NAME_1` (province name) instead of `NAME_2` (municipality name).

## Data Structure Analysis
- **Municipalities**: Use `NAME_2` property for municipality names (e.g., "Bangued", "Boliney", "Bucay")
- **Provinces**: Use `NAME_1` property for province names (e.g., "Abra", "AgusandelNorte", "AgusandelSur")
- **Regions**: Use `REGION` or `name` property for region names

## Solution Implemented
Updated the `loadAreas()` function in `templates/analytics.html` to use the correct property based on administrative level:

```javascript
// Use the correct property based on administrative level
if (level === 'municipality') {
  name = f.properties.NAME_2 || '';
} else if (level === 'province') {
  name = f.properties.NAME_1 || '';
} else if (level === 'region') {
  name = f.properties.REGION || f.properties.name || '';
} else {
  // Fallback for unknown levels
  name = f.properties.name || f.properties.REGION || f.properties.NAME_1 || f.properties.NAME_2 || '';
}
```

## Files Modified
- `templates/analytics.html` - Updated `loadAreas()` function around line 265

## Expected Results
- Municipality filter now shows actual municipality names instead of province names
- No more duplicate entries in municipality dropdown
- Proper filtering functionality maintained
- Consistent behavior across all administrative levels (region, province, municipality)

## Status
✅ **COMPLETED** - Fix implemented and tested for syntax errors