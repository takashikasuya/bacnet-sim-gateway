/* bbc-sim Admin UI — app.js */

/* --- Partial fetch (auto-refresh) --- */

async function fetchPartial(url, targetId) {
  try {
    const res = await fetch(url);
    if (res.ok) {
      document.getElementById(targetId).innerHTML = await res.text();
    }
  } catch (_) { /* network error — silently skip, next poll will retry */ }
}

/* --- JSON POST helper --- */

async function postJson(url, data) {
  const res = await fetch(url, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(data),
  });
  return res;
}

/* --- Context help popups --- */

let _activePopup = null;

function _closeActivePopup() {
  if (_activePopup) {
    _activePopup.remove();
    _activePopup = null;
  }
}

document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.ctx-help-btn').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      e.stopPropagation();
      const page = btn.dataset.page;
      if (!page) return;

      if (_activePopup) { _closeActivePopup(); return; }

      try {
        const res = await fetch('/ui/partials/help/' + page);
        if (!res.ok) return;
        const html = await res.text();
        const popup = document.createElement('div');
        popup.innerHTML = html;
        const inner = popup.firstElementChild;
        if (!inner) return;

        inner.style.position = 'absolute';
        inner.style.zIndex = '200';
        document.body.appendChild(inner);
        _activePopup = inner;

        const rect = btn.getBoundingClientRect();
        inner.style.top  = (rect.bottom + window.scrollY + 4) + 'px';
        inner.style.left = Math.max(8, rect.left + window.scrollX) + 'px';
      } catch (_) { /* network error */ }
    });
  });

  document.addEventListener('click', _closeActivePopup);

  /* --- First-run tour --- */
  if (!localStorage.getItem('bbc_sim_tour_done')) {
    showTour();
  }
});

/* --- Tour --- */

let _tourStep = 0;

function showTour() {
  _tourStep = 0;
  const overlay = document.getElementById('tour-overlay');
  if (!overlay) return;
  overlay.style.display = 'flex';
  _renderTourStep();
}

function closeTour() {
  const overlay = document.getElementById('tour-overlay');
  if (overlay) overlay.style.display = 'none';
  localStorage.setItem('bbc_sim_tour_done', '1');
}

function tourNext() {
  const steps = document.querySelectorAll('.tour-step');
  if (_tourStep < steps.length - 1) {
    _tourStep++;
    _renderTourStep();
  }
}

function tourPrev() {
  if (_tourStep > 0) {
    _tourStep--;
    _renderTourStep();
  }
}

function _renderTourStep() {
  const steps = document.querySelectorAll('.tour-step');
  steps.forEach((s, i) => s.style.display = i === _tourStep ? '' : 'none');

  const total = steps.length;
  const ind = document.getElementById('tour-indicator');
  if (ind) ind.textContent = (_tourStep + 1) + ' / ' + total;

  const prev = document.getElementById('tour-prev');
  const next = document.getElementById('tour-next');
  const close = document.getElementById('tour-close');

  if (prev)  prev.style.visibility  = _tourStep === 0 ? 'hidden' : 'visible';
  if (next)  next.style.display     = _tourStep < total - 1 ? '' : 'none';
  if (close) close.style.display    = _tourStep === total - 1 ? '' : 'none';
}
