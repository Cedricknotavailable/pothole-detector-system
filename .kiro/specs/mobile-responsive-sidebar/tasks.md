# Implementation Plan: Mobile Responsive Sidebar

## Overview

This implementation plan converts the mobile-responsive sidebar design into actionable coding tasks. The feature extends the existing mobile navigation pattern (currently on /index) to all application pages, providing a consistent hamburger menu and responsive sidebar experience across mobile, tablet, and desktop viewports.

The implementation leverages existing CSS and JavaScript modules (mobile-nav.css and mobile-nav.js) and applies them consistently to 7 pages that currently lack mobile navigation support.

## Tasks

- [x] 1. Verify and update mobile navigation assets
  - Verify that static/css/mobile-nav.css exists and contains all required styles
  - Verify that static/js/mobile-nav.js exists and contains all required functionality
  - Review index.html implementation as the reference pattern
  - _Requirements: 1.1, 1.2, 2.1, 2.2, 11.1, 11.2, 11.3, 11.4_

- [ ] 2. Update map.html with mobile navigation
  - [ ] 2.1 Add hamburger button to topbar in templates/map.html
    - Insert hamburger button structure after opening `<header class="topbar">` tag
    - Ensure button has three span elements and proper aria-label
    - _Requirements: 1.1, 1.3, 1.4, 1.5, 9.1, 9.4_
  
  - [ ] 2.2 Add mobile-nav structure to templates/map.html
    - Insert complete mobile-nav HTML after closing `</header>` tag
    - Include mobile-nav-overlay, mobile-nav-content, mobile-nav-header, and mobile-nav-links
    - Set "Map" link as active in mobile-nav-links
    - _Requirements: 2.1, 2.3, 2.4, 4.1, 4.2, 4.3, 4.4, 13.1, 13.4_
  
  - [ ] 2.3 Link CSS files in templates/map.html
    - Add mobile-nav.css link in `<head>` section
    - Ensure users.css is linked for base layout styles
    - _Requirements: 11.4, 13.1, 13.2, 13.3_
  
  - [ ] 2.4 Link mobile-nav.js in templates/map.html
    - Add mobile-nav.js script tag before closing `</body>` tag
    - _Requirements: 3.1, 3.2, 3.3, 5.1, 5.2, 6.1, 9.3, 9.6_
  
  - [ ] 2.5 Set active state on desktop sidebar in templates/map.html
    - Add `class="active"` to "Map" link in desktop sidebar nav
    - _Requirements: 13.2_

- [ ] 3. Update users.html with mobile navigation
  - [ ] 3.1 Add hamburger button to topbar in templates/users.html
    - Insert hamburger button structure after opening `<header class="topbar">` tag
    - Ensure button has three span elements and proper aria-label
    - _Requirements: 1.1, 1.3, 1.4, 1.5, 9.1, 9.4_
  
  - [ ] 3.2 Add mobile-nav structure to templates/users.html
    - Insert complete mobile-nav HTML after closing `</header>` tag
    - Set "User management" link as active in mobile-nav-links
    - _Requirements: 2.1, 2.3, 2.4, 4.1, 4.2, 4.3, 4.4, 13.1, 13.4_
  
  - [ ] 3.3 Link CSS files in templates/users.html
    - Add mobile-nav.css link in `<head>` section if not already present
    - _Requirements: 11.4, 13.1, 13.2, 13.3_
  
  - [ ] 3.4 Link mobile-nav.js in templates/users.html
    - Add mobile-nav.js script tag before closing `</body>` tag
    - _Requirements: 3.1, 3.2, 3.3, 5.1, 5.2, 6.1, 9.3, 9.6_
  
  - [ ] 3.5 Set active state on desktop sidebar in templates/users.html
    - Add `class="active"` to "User management" link in desktop sidebar nav
    - _Requirements: 13.2_

- [ ] 4. Update defects.html with mobile navigation
  - [ ] 4.1 Add hamburger button to topbar in templates/defects.html
    - Insert hamburger button structure after opening `<header class="topbar">` tag
    - Ensure button has three span elements and proper aria-label
    - _Requirements: 1.1, 1.3, 1.4, 1.5, 9.1, 9.4_
  
  - [ ] 4.2 Add mobile-nav structure to templates/defects.html
    - Insert complete mobile-nav HTML after closing `</header>` tag
    - Set "Defects Management" link as active in mobile-nav-links
    - _Requirements: 2.1, 2.3, 2.4, 4.1, 4.2, 4.3, 4.4, 13.1, 13.4_
  
  - [ ] 4.3 Link CSS files in templates/defects.html
    - Add mobile-nav.css link in `<head>` section
    - _Requirements: 11.4, 13.1, 13.2, 13.3_
  
  - [ ] 4.4 Link mobile-nav.js in templates/defects.html
    - Add mobile-nav.js script tag before closing `</body>` tag
    - _Requirements: 3.1, 3.2, 3.3, 5.1, 5.2, 6.1, 9.3, 9.6_
  
  - [ ] 4.5 Set active state on desktop sidebar in templates/defects.html
    - Add `class="active"` to "Defects Management" link in desktop sidebar nav
    - _Requirements: 13.2_

- [ ] 5. Update settings.html with mobile navigation
  - [ ] 5.1 Add hamburger button to topbar in templates/settings.html
    - Insert hamburger button structure after opening `<header class="topbar">` tag
    - Ensure button has three span elements and proper aria-label
    - _Requirements: 1.1, 1.3, 1.4, 1.5, 9.1, 9.4_
  
  - [ ] 5.2 Add mobile-nav structure to templates/settings.html
    - Insert complete mobile-nav HTML after closing `</header>` tag
    - Set "Settings" link as active in mobile-nav-links
    - _Requirements: 2.1, 2.3, 2.4, 4.1, 4.2, 4.3, 4.4, 13.1, 13.4_
  
  - [ ] 5.3 Link CSS files in templates/settings.html
    - Add mobile-nav.css link in `<head>` section
    - _Requirements: 11.4, 13.1, 13.2, 13.3_
  
  - [ ] 5.4 Link mobile-nav.js in templates/settings.html
    - Add mobile-nav.js script tag before closing `</body>` tag
    - _Requirements: 3.1, 3.2, 3.3, 5.1, 5.2, 6.1, 9.3, 9.6_
  
  - [ ] 5.5 Set active state on desktop sidebar in templates/settings.html
    - Add `class="active"` to "Settings" link in desktop sidebar nav
    - _Requirements: 13.2_

- [ ] 6. Update backup_management.html with mobile navigation
  - [ ] 6.1 Add hamburger button to topbar in templates/backup_management.html
    - Insert hamburger button structure after opening `<header class="topbar">` tag
    - Ensure button has three span elements and proper aria-label
    - _Requirements: 1.1, 1.3, 1.4, 1.5, 9.1, 9.4_
  
  - [ ] 6.2 Add mobile-nav structure to templates/backup_management.html
    - Insert complete mobile-nav HTML after closing `</header>` tag
    - Set "Backup Management" link as active in mobile-nav-links
    - _Requirements: 2.1, 2.3, 2.4, 4.1, 4.2, 4.3, 4.4, 13.1, 13.4_
  
  - [ ] 6.3 Link CSS files in templates/backup_management.html
    - Add mobile-nav.css link in `<head>` section
    - _Requirements: 11.4, 13.1, 13.2, 13.3_
  
  - [ ] 6.4 Link mobile-nav.js in templates/backup_management.html
    - Add mobile-nav.js script tag before closing `</body>` tag
    - _Requirements: 3.1, 3.2, 3.3, 5.1, 5.2, 6.1, 9.3, 9.6_
  
  - [ ] 6.5 Set active state on desktop sidebar in templates/backup_management.html
    - Add `class="active"` to "Backup Management" link in desktop sidebar nav
    - _Requirements: 13.2_

- [ ] 7. Update analytics.html with mobile navigation
  - [ ] 7.1 Add hamburger button to topbar in templates/analytics.html
    - Insert hamburger button structure after opening `<header class="topbar">` tag
    - Ensure button has three span elements and proper aria-label
    - _Requirements: 1.1, 1.3, 1.4, 1.5, 9.1, 9.4_
  
  - [ ] 7.2 Add mobile-nav structure to templates/analytics.html
    - Insert complete mobile-nav HTML after closing `</header>` tag
    - Set "Analytics" link as active in mobile-nav-links
    - _Requirements: 2.1, 2.3, 2.4, 4.1, 4.2, 4.3, 4.4, 13.1, 13.4_
  
  - [ ] 7.3 Link CSS files in templates/analytics.html
    - Add mobile-nav.css link in `<head>` section
    - _Requirements: 11.4, 13.1, 13.2, 13.3_
  
  - [ ] 7.4 Link mobile-nav.js in templates/analytics.html
    - Add mobile-nav.js script tag before closing `</body>` tag
    - _Requirements: 3.1, 3.2, 3.3, 5.1, 5.2, 6.1, 9.3, 9.6_
  
  - [ ] 7.5 Set active state on desktop sidebar in templates/analytics.html
    - Add `class="active"` to "Analytics" link in desktop sidebar nav
    - _Requirements: 13.2_

- [ ] 8. Update activity_logs.html with mobile navigation
  - [ ] 8.1 Add hamburger button to topbar in templates/activity_logs.html
    - Insert hamburger button structure after opening `<header class="topbar">` tag
    - Ensure button has three span elements and proper aria-label
    - _Requirements: 1.1, 1.3, 1.4, 1.5, 9.1, 9.4_
  
  - [ ] 8.2 Add mobile-nav structure to templates/activity_logs.html
    - Insert complete mobile-nav HTML after closing `</header>` tag
    - Set "Activity Logs" link as active in mobile-nav-links
    - _Requirements: 2.1, 2.3, 2.4, 4.1, 4.2, 4.3, 4.4, 13.1, 13.4_
  
  - [ ] 8.3 Link CSS files in templates/activity_logs.html
    - Add mobile-nav.css link in `<head>` section
    - _Requirements: 11.4, 13.1, 13.2, 13.3_
  
  - [ ] 8.4 Link mobile-nav.js in templates/activity_logs.html
    - Add mobile-nav.js script tag before closing `</body>` tag
    - _Requirements: 3.1, 3.2, 3.3, 5.1, 5.2, 6.1, 9.3, 9.6_
  
  - [ ] 8.5 Set active state on desktop sidebar in templates/activity_logs.html
    - Add `class="active"` to "Activity Logs" link in desktop sidebar nav
    - _Requirements: 13.2_

- [ ] 9. Checkpoint - Verify all pages have mobile navigation
  - Test each page in browser to ensure hamburger button appears on mobile/tablet viewports
  - Verify desktop sidebar remains visible on desktop viewports
  - Ensure all tests pass, ask the user if questions arise
  - _Requirements: 7.1_

- [ ]* 10. Write property-based tests for mobile navigation
  - [ ]* 10.1 Property test for hamburger visibility based on viewport
    - **Property 1: Hamburger Menu Visibility Based on Viewport**
    - **Validates: Requirements 1.1, 1.2**
    - Generate random viewport widths (320px - 2560px)
    - Verify hamburger is visible when viewport ≤ 1024px
    - Verify hamburger is hidden when viewport > 1024px
  
  - [ ]* 10.2 Property test for sidebar default visibility
    - **Property 2: Sidebar Default Visibility Based on Viewport**
    - **Validates: Requirements 2.1, 2.2, 2.4**
    - Generate random viewport widths
    - Verify desktop sidebar visible by default when viewport > 1024px
    - Verify mobile nav hidden by default when viewport ≤ 1024px
  
  - [ ]* 10.3 Property test for sidebar toggle interaction
    - **Property 3: Sidebar Toggle Interaction**
    - **Validates: Requirements 3.1, 3.2**
    - Generate random initial sidebar states (open/closed)
    - Verify clicking hamburger toggles to opposite state
    - Verify smooth animation occurs (300ms duration)
  
  - [ ]* 10.4 Property test for hamburger button interactivity during animation
    - **Property 4: Hamburger Button Remains Interactive During Animation**
    - **Validates: Requirements 3.4**
    - Verify hamburger button never has pointer-events:none or disabled attribute
    - Test during animation states
  
  - [ ]* 10.5 Property test for hamburger icon animation
    - **Property 5: Hamburger Icon Animation on State Change**
    - **Validates: Requirements 3.5**
    - Verify 'active' class added when sidebar opens
    - Verify 'active' class removed when sidebar closes
  
  - [ ]* 10.6 Property test for sidebar positioning on mobile/tablet
    - **Property 6: Sidebar Does Not Occupy Layout Space on Mobile/Tablet**
    - **Validates: Requirements 2.3**
    - Verify mobile-nav uses fixed positioning when viewport ≤ 1024px
    - Verify it doesn't affect document flow when hidden
  
  - [ ]* 10.7 Property test for sidebar overlay behavior
    - **Property 7: Sidebar Overlays Content on Mobile/Tablet**
    - **Validates: Requirements 4.1**
    - Verify sidebar has high z-index when visible on mobile/tablet
    - Verify it overlays main content rather than pushing it
  
  - [ ]* 10.8 Property test for overlay appearance
    - **Property 8: Overlay Appears When Sidebar Opens**
    - **Validates: Requirements 4.2**
    - Verify overlay opacity > 0 when sidebar transitions to open
  
  - [ ]* 10.9 Property test for overlay hiding
    - **Property 9: Overlay Hides When Sidebar Closes**
    - **Validates: Requirements 4.5**
    - Verify overlay opacity = 0 or visibility hidden when sidebar closes
  
  - [ ]* 10.10 Property test for clicking overlay closes sidebar
    - **Property 10: Clicking Overlay Closes Sidebar**
    - **Validates: Requirements 5.1, 5.2**
    - Verify clicking overlay element closes sidebar on mobile/tablet
  
  - [ ]* 10.11 Property test for clicking inside sidebar keeps it open
    - **Property 11: Clicking Inside Sidebar Keeps It Open**
    - **Validates: Requirements 5.3**
    - Verify clicking mobile-nav-content (not links) doesn't close sidebar
  
  - [ ]* 10.12 Property test for click-outside only on mobile/tablet
    - **Property 12: Click-Outside Only Works on Mobile/Tablet**
    - **Validates: Requirements 5.4**
    - Verify overlay doesn't exist or isn't visible on desktop (>1024px)
  
  - [ ]* 10.13 Property test for navigation link click closes sidebar
    - **Property 13: Navigation Link Click Closes Sidebar on Mobile/Tablet**
    - **Validates: Requirements 6.1**
    - Verify clicking nav link closes sidebar on mobile/tablet
  
  - [ ]* 10.14 Property test for desktop sidebar remains open on link click
    - **Property 14: Desktop Sidebar Remains Open on Link Click**
    - **Validates: Requirements 6.2**
    - Verify clicking nav link doesn't trigger close on desktop
  
  - [ ]* 10.15 Property test for layout adaptation on viewport change
    - **Property 15: Layout Adapts to Viewport Changes Without Reload**
    - **Validates: Requirements 7.2**
    - Generate viewport width changes (resize events)
    - Verify layout adapts by showing/hiding appropriate nav elements
  
  - [ ]* 10.16 Property test for main content width on mobile/tablet
    - **Property 16: Main Content Uses Full Width on Mobile/Tablet**
    - **Validates: Requirements 7.3, 7.4**
    - Verify main content uses full viewport width minus padding on mobile/tablet
  
  - [ ]* 10.17 Property test for main content accounts for sidebar on desktop
    - **Property 17: Main Content Accounts for Sidebar on Desktop**
    - **Validates: Requirements 7.5**
    - Verify main content positioned to account for sidebar width on desktop
  
  - [ ]* 10.18 Property test for Escape key closes sidebar
    - **Property 18: Escape Key Closes Sidebar and Returns Focus**
    - **Validates: Requirements 9.6**
    - Verify pressing Escape closes sidebar on mobile/tablet
    - Verify focus returns to hamburger button
  
  - [ ]* 10.19 Property test for desktop sidebar always visible
    - **Property 19: Desktop Sidebar Always Visible Across Navigation**
    - **Validates: Requirements 10.3**
    - Verify sidebar remains visible on desktop across all pages

- [ ]* 11. Write unit tests for mobile navigation
  - [ ]* 11.1 Test hamburger button HTML structure
    - Verify hamburger button has three span elements
    - Verify aria-label attribute is present and descriptive
    - Test on all 8 pages
  
  - [ ]* 11.2 Test mobile-nav HTML structure
    - Verify mobile-nav structure exists on all pages
    - Verify navigation links are duplicated in both desktop and mobile nav
    - Verify correct active state on each page
  
  - [ ]* 11.3 Test CSS media query breakpoints
    - Verify breakpoints at 767px, 768px, 1024px, 1025px
    - Test hamburger visibility at each breakpoint
    - Test sidebar visibility at each breakpoint
  
  - [ ]* 11.4 Test CSS dimensions and styling
    - Verify hamburger button is 44x44px minimum
    - Verify mobile nav width is 280px (max 85vw)
    - Verify navigation link height is 48px on mobile
    - Verify overlay background is rgba(0, 0, 0, 0.5)
    - Verify animation duration is 300ms
    - Verify transform usage (translateX)
  
  - [ ]* 11.5 Test JavaScript event listeners
    - Verify event listeners are registered on page load
    - Verify openMenu() adds 'active' class and 'mobile-nav-open' body class
    - Verify closeMenu() removes classes
    - Verify resize handler debouncing (250ms)
    - Verify navigation link click delay (100ms)
  
  - [ ]* 11.6 Test accessibility attributes
    - Verify hamburger button is keyboard focusable
    - Verify focus indicator is visible
    - Verify ARIA labels are present
    - Verify focus management on menu open/close
  
  - [ ]* 11.7 Test complete open/close cycle
    - Test hamburger click opens menu
    - Test overlay click closes menu
    - Test Escape key closes menu
    - Test navigation link click closes menu and navigates
    - Test resize from mobile to desktop closes menu

- [ ] 12. Final checkpoint - Cross-browser and device testing
  - Test on Chrome, Firefox, Safari, Edge
  - Test on real mobile devices (iOS, Android)
  - Test on tablets (iPad, Android tablets)
  - Test keyboard navigation on all pages
  - Test with screen readers (NVDA, JAWS, VoiceOver)
  - Verify all animations are smooth (60 FPS)
  - Ensure all tests pass, ask the user if questions arise
  - _Requirements: 7.1, 8.1, 8.2, 9.1, 9.2, 9.3, 9.4, 9.6, 12.1, 12.2, 12.3_

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- The implementation follows the existing pattern from index.html
- All pages use the same mobile-nav.css and mobile-nav.js files for consistency
- Property tests validate universal correctness properties across all viewport sizes
- Unit tests validate specific examples, edge cases, and accessibility compliance
- Checkpoints ensure incremental validation and user feedback opportunities
