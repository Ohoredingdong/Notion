/* Shared photo crops for the approved recipe-card treatment. */
(() => {
  'use strict';
  const RECIPE_PHOTOS = './designs/miniature-kitchen/assets/recipe-photos-v1.png';
  let sequence = 0;
  const escape = value => String(value ?? '').replace(/[&<>"']/g, character => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[character]));
  const nameKey = value => String(value ?? '').normalize('NFKC').replace(/\s+/g, '');

  function dish(recipe, fit = 'cover') {
    const value = typeof recipe === 'string' ? {id: recipe, name: recipe} : recipe || {};
    const catalog = Array.isArray(window.KitchenCatalog) ? window.KitchenCatalog : [];
    const known = catalog.find(row => row.id === value.id) || catalog.find(row => nameKey(row.name) === nameKey(value.name || value.id));
    const match = /^recipe-([1-8])$/.exec(known?.id || '');
    if (!match) return window.UMFKitchenArt.dishArt({id: value.name || value.id || ''});
    const index = Number(match[1]) - 1, x = index % 2 * 512, y = Math.floor(index / 2) * 384;
    const clip = 'kitchen-recipe-photo-' + (++sequence), label = escape(value.name || known.name);
    return `<svg class="dish-art recipe-photo" data-recipe-photo="${known.id}" viewBox="${x} ${y} 512 384" preserveAspectRatio="${fit==='wide'?'none':'xMidYMid slice'}" role="img" aria-label="${label}" style="overflow:hidden"><defs><clipPath id="${clip}"><rect x="${x}" y="${y}" width="512" height="384"/></clipPath></defs><image href="${RECIPE_PHOTOS}" x="0" y="0" width="1024" height="1536" preserveAspectRatio="none" clip-path="url(#${clip})"/></svg>`;
  }

  window.KitchenStoryboardArt = Object.freeze({dish});
})();
