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

/* GA4 Consent Controls + Duplicate-Free, Zero-PII Event Tracking */
(() => {
  if (window.__saAnalyticsBound) return;
  window.__saAnalyticsBound = true;

  const CONSENT_KEY = 'sa_ga_consent';
  const gaId = document.body?.dataset?.gaId || '';

  function getConsent() {
    try {
      return localStorage.getItem(CONSENT_KEY);
    } catch {
      return null;
    }
  }

  function setConsent(choice) {
    try {
      localStorage.setItem(CONSENT_KEY, choice);
    } catch {}
    if (gaId) {
      window['ga-disable-' + gaId] = choice === 'denied';
    }
    if (typeof window.gtag === 'function') {
      window.gtag('consent', 'update', {
        analytics_storage: choice === 'denied' ? 'denied' : 'granted',
        ad_storage: 'denied',
        ad_user_data: 'denied',
        ad_personalization: 'denied',
      });
    }
  }

  function sendEvent(name, params) {
    if (!gaId || getConsent() === 'denied' || typeof window.gtag !== 'function') return;
    window.gtag('event', name, params);
  }

  // Strip query parameters/hash from external URLs so zero PII or tokens are ever transmitted
  function safeUrlInfo(href) {
    try {
      const u = new URL(href, window.location.href);
      return {
        domain: u.hostname || '',
        path: (u.origin + u.pathname).slice(0, 140),
        isExternal: u.hostname && u.hostname !== window.location.hostname,
      };
    } catch {
      return { domain: '', path: '', isExternal: false };
    }
  }

  // 1. Track category page visit once per load
  const pageType = document.body?.dataset?.pageType || '';
  const pageCat = document.body?.dataset?.category || '';
  if (pageType === 'category' && pageCat && !window.__saCatTracked) {
    window.__saCatTracked = true;
    sendEvent('category_visit', {
      category_slug: pageCat,
      page_path: window.location.pathname,
    });
  }

  // 2. Deduplicated click tracking with mutual exclusion (1 click = max 1 event)
  const recentEvents = new Map();
  document.addEventListener('click', (ev) => {
    const a = ev.target?.closest?.('a[href]');
    if (!a) return;
    const rawHref = a.getAttribute('href') || '';
    if (!rawHref || rawHref.startsWith('#') || rawHref.startsWith('mailto:') || rawHref.startsWith('tel:')) return;

    const info = safeUrlInfo(a.href);
    const labelTxt = (a.textContent || '').trim().toLowerCase();
    const postId = a.closest('li[data-post]')?.dataset?.postId || document.body?.dataset?.postId || '';

    let eventName = '';
    let payload = {};

    if (a.classList.contains('referral-cta') || info.path.includes('/loans-and-cards/')) {
      eventName = 'referral_click';
      payload = { link_domain: info.domain, target_path: info.path, section: 'loans_and_cards' };
    } else if (a.classList.contains('apply-btn') || a.classList.contains('pending-btn')) {
      eventName = 'apply_online_click';
      payload = {
        link_domain: info.domain,
        post_id: postId || 'list',
        category: pageCat || 'jobs',
        link_status: a.classList.contains('pending-btn') ? 'verification_pending' : 'open',
      };
    } else if (
      a.classList.contains('notice-btn') ||
      info.path.toLowerCase().endsWith('.pdf') ||
      labelTxt.includes('notification')
    ) {
      eventName = 'notification_download';
      payload = {
        link_domain: info.domain,
        file_type: info.path.toLowerCase().endsWith('.pdf') ? 'pdf' : 'official_notice',
        post_id: postId || 'list',
      };
    } else if (info.isExternal) {
      eventName = 'outbound_click';
      payload = { link_domain: info.domain, target_path: info.path, page_type: pageType || 'site' };
    }

    if (!eventName) return;

    const dedupeKey = eventName + '|' + info.path;
    const ts = Date.now();
    if (ts - (recentEvents.get(dedupeKey) || 0) < 1500) return;
    recentEvents.set(dedupeKey, ts);
    sendEvent(eventName, payload);
  });

  // 3. Consent banner & footer/privacy toggle UI (CLS-free fixed banner only when unset)
  function showConsentBanner() {
    if (document.querySelector('#sa-consent-bar')) return;
    const prefix = document.body?.dataset?.assetPrefix || './';
    const bar = document.createElement('div');
    bar.id = 'sa-consent-bar';
    bar.className = 'consent-bar';
    bar.setAttribute('role', 'region');
    bar.setAttribute('aria-label', 'Analytics privacy preferences');
    bar.innerHTML =
      '<div><strong>Privacy &amp; Analytics:</strong> Sarkari Alert uses anonymized Google Analytics 4 (no PII or personal documents) to improve job &amp; yojana updates. ' +
      `<a href="${prefix}privacy/">Privacy Policy</a></div>` +
      '<div class="consent-actions">' +
      '<button type="button" class="consent-accept">Allow Analytics</button>' +
      '<button type="button" class="consent-decline">Essential Only (Opt Out)</button>' +
      '</div>';
    bar.querySelector('.consent-accept').addEventListener('click', () => {
      setConsent('granted');
      bar.remove();
      updateConsentStatusLabel();
    });
    bar.querySelector('.consent-decline').addEventListener('click', () => {
      setConsent('denied');
      bar.remove();
      updateConsentStatusLabel();
    });
    document.body.appendChild(bar);
  }

  function updateConsentStatusLabel() {
    const el = document.querySelector('#privacy-consent-state');
    if (!el) return;
    const c = getConsent();
    el.textContent = c === 'denied' ? 'Opted Out (Analytics Disabled)' : 'Analytics Enabled (Anonymized, Zero PII)';
  }

  if (gaId && getConsent() === null) {
    showConsentBanner();
  }
  updateConsentStatusLabel();

  document.querySelector('#manage-analytics-consent')?.addEventListener('click', showConsentBanner);
  document.querySelector('#privacy-allow-analytics')?.addEventListener('click', () => {
    setConsent('granted');
    document.querySelector('#sa-consent-bar')?.remove();
    updateConsentStatusLabel();
  });
  document.querySelector('#privacy-deny-analytics')?.addEventListener('click', () => {
    setConsent('denied');
    document.querySelector('#sa-consent-bar')?.remove();
    updateConsentStatusLabel();
  });
})();

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
