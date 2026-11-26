'use strict';
const now = Date.now();

function isExpired(el) {
  const dl = el.dataset.deadline;
  if (!dl) return false;
  const ts = Date.parse(dl);
  return !Number.isNaN(ts) && ts < Date.now();
}

document.querySelectorAll('li[data-deadline]').forEach((n) => {
  if (isExpired(n)) n.hidden = true;
});

const form = document.querySelector('#search');
function filter() {
  const q = (document.querySelector('#query')?.value || '').trim().toLowerCase();
  const dept = document.querySelector('#department')?.value || '';
  const qual = document.querySelector('#qualification')?.value || '';
  let count = 0;
  const active = !!(q || dept || qual);
  document.querySelectorAll('.panel').forEach((panel) => {
    const items = [...panel.querySelectorAll('li[data-post]')];
    items.forEach((item) => {
      const match =
        !isExpired(item) &&
        (!q || item.textContent.toLowerCase().includes(q)) &&
        (!dept || item.dataset.department === dept) &&
        (!qual || item.dataset.qualification === qual);
      item.hidden = !match;
      if (match) count++;
    });
    panel.hidden = active && !items.some((i) => !i.hidden);
  });
  const s = document.querySelector('#search-status');
  if (s) {
    s.hidden = false;
    s.textContent = active ? count + ' matching updates' : 'Showing all categories';
  }
}

form?.addEventListener('submit', (e) => {
  e.preventDefault();
  filter();
});
form?.addEventListener('change', filter);
form?.addEventListener('reset', () => setTimeout(filter, 0));

document.querySelectorAll('[data-apply-box]').forEach((box) => {
  const dl = box.dataset.deadline;
  if (dl && Date.parse(dl) < now) {
    document.querySelectorAll('.detail .apply-btn').forEach((a) => {
      const label = document.createElement('span');
      label.className = 'closed-label';
      label.textContent = 'Application closed';
      a.replaceWith(label);
    });
  }
});

/* Remove obsolete service worker registrations for this website only. */
if ('serviceWorker' in navigator) {
  navigator.serviceWorker
    .getRegistrations()
    .then((rs) =>
      Promise.all(
        rs
          .filter((r) => new URL(r.scope).pathname === '/sarkarialert/')
          .map((r) => r.unregister())
      )
    )
    .catch(() => {});
}
