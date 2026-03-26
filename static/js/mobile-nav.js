/**
 * Mobile Navigation Handler
 * Manages hamburger menu and mobile navigation
 */

(function() {
  'use strict';
  
  // Wait for DOM to be ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
  
  function init() {
    const hamburger = document.querySelector('.hamburger');
    const mobileNav = document.querySelector('.mobile-nav');
    const mobileNavOverlay = document.querySelector('.mobile-nav-overlay');
    const mobileNavClose = document.querySelector('.mobile-nav-close');
    const mobileNavLinks = document.querySelectorAll('.mobile-nav-links a');
    
    if (!hamburger || !mobileNav) return;
    
    // Open menu
    hamburger.addEventListener('click', function(e) {
      e.stopPropagation();
      openMenu();
    });
    
    // Close menu - overlay click
    if (mobileNavOverlay) {
      mobileNavOverlay.addEventListener('click', closeMenu);
    }
    
    // Close menu - close button
    if (mobileNavClose) {
      mobileNavClose.addEventListener('click', closeMenu);
    }
    
    // Close menu - link click
    mobileNavLinks.forEach(function(link) {
      link.addEventListener('click', function() {
        // Small delay to allow navigation to start
        setTimeout(closeMenu, 100);
      });
    });
    
    // Close menu on escape key
    document.addEventListener('keydown', function(e) {
      if (e.key === 'Escape' && mobileNav.classList.contains('active')) {
        closeMenu();
      }
    });
    
    // Handle window resize
    let resizeTimer;
    window.addEventListener('resize', function() {
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(function() {
        // Close menu if window is resized to desktop
        if (window.innerWidth > 768 && mobileNav.classList.contains('active')) {
          closeMenu();
        }
      }, 250);
    });
    
    function openMenu() {
      mobileNav.classList.add('active');
      hamburger.classList.add('active');
      document.body.classList.add('mobile-nav-open');
      
      // Set focus to close button for accessibility
      if (mobileNavClose) {
        setTimeout(function() {
          mobileNavClose.focus();
        }, 300);
      }
    }
    
    function closeMenu() {
      mobileNav.classList.remove('active');
      hamburger.classList.remove('active');
      document.body.classList.remove('mobile-nav-open');
      
      // Return focus to hamburger
      setTimeout(function() {
        hamburger.focus();
      }, 300);
    }
  }
})();
