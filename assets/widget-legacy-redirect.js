/* Compatibility entrypoints keep existing widget embeds on the current version. */
(() => {
  'use strict';
  const link = document.querySelector('link[rel="canonical"]');
  if (!link) return;
  const target = new URL(link.getAttribute('href'), location.href);
  if (target.origin !== location.origin || target.pathname === location.pathname) return;
  target.search = location.search;
  target.hash = location.hash;
  location.replace(target.href);
})();
