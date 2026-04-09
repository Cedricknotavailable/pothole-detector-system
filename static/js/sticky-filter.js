/**
 * sticky-filter.js
 * Makes a filter bar behave like position:sticky using scroll events.
 * Works reliably on mobile where CSS sticky fails due to parent overflow constraints.
 *
 * Usage:
 *   initStickyFilter('mobileFilterBar', 'mobileFilterBarPlaceholder', 60, 1023)
 *
 * @param {string} barId         - ID of the filter bar element
 * @param {string} placeholderId - ID of the placeholder element
 * @param {number} topOffset     - px from top when fixed (e.g. topbar height)
 * @param {number} maxWidth      - only apply on screens <= this width
 */
function initStickyFilter(barId, placeholderId, topOffset, maxWidth) {
  var bar = document.getElementById(barId);
  var placeholder = document.getElementById(placeholderId);
  if (!bar || !placeholder) return;

  var isFixed = false;
  var originalTop = 0;

  function isMobile() {
    return window.innerWidth <= maxWidth;
  }

  function getOriginalTop() {
    // Must be called while bar is NOT fixed
    return bar.getBoundingClientRect().top + window.scrollY;
  }

  function fixBar() {
    placeholder.style.height = bar.offsetHeight + 'px';
    bar.style.position = 'fixed';
    bar.style.top = topOffset + 'px';
    bar.style.left = '0';
    bar.style.right = '0';
    bar.style.width = '100%';
    bar.style.zIndex = '200';
    bar.style.boxShadow = '0 2px 8px rgba(0,0,0,0.12)';
    isFixed = true;
  }

  function unfixBar() {
    placeholder.style.height = '0';
    bar.style.position = '';
    bar.style.top = '';
    bar.style.left = '';
    bar.style.right = '';
    bar.style.width = '';
    bar.style.zIndex = '';
    bar.style.boxShadow = '';
    isFixed = false;
  }

  function onScroll() {
    if (!isMobile()) {
      if (isFixed) unfixBar();
      return;
    }
    var scrollY = window.scrollY || window.pageYOffset;
    if (!isFixed && scrollY + topOffset >= originalTop) {
      fixBar();
    } else if (isFixed && scrollY + topOffset < originalTop) {
      unfixBar();
    }
  }

  // Update placeholder height when bar resizes (e.g. filter expands)
  if (window.ResizeObserver) {
    new ResizeObserver(function() {
      if (isFixed) placeholder.style.height = bar.offsetHeight + 'px';
    }).observe(bar);
  }

  // Capture original position after full render
  function init() {
    if (!isMobile()) return;
    originalTop = getOriginalTop();
    onScroll(); // run once in case page loaded already scrolled
  }

  // Run after DOM + images loaded
  if (document.readyState === 'complete') {
    setTimeout(init, 50);
  } else {
    window.addEventListener('load', function() { setTimeout(init, 50); });
  }

  window.addEventListener('scroll', onScroll, { passive: true });
  window.addEventListener('resize', function() {
    if (!isFixed) originalTop = getOriginalTop();
    onScroll();
  }, { passive: true });
}
