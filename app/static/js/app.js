/* BilimAI — fireflies + sparkles engine */
(function () {
  'use strict';

  const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* Fireflies over the meadow */
  const ff = document.getElementById('fireflies');
  if (ff && !prefersReduced) {
    const N = window.innerWidth < 700 ? 12 : 26;
    for (let i = 0; i < N; i++) {
      const f = document.createElement('div');
      f.className = 'firefly';
      f.style.left = Math.random() * 100 + '%';
      f.style.top = (20 + Math.random() * 70) + '%';
      const dur = 6 + Math.random() * 8;
      f.style.animationDuration = dur + 's';
      f.style.animationDelay = (-Math.random() * dur) + 's';
      ff.appendChild(f);
    }
  }

  /* Ripple effect on .btn */
  document.addEventListener('click', (e) => {
    const btn = e.target.closest('.btn');
    if (!btn || prefersReduced) return;
    const rect = btn.getBoundingClientRect();
    const r = document.createElement('span');
    Object.assign(r.style, {
      position: 'absolute',
      width: '6px', height: '6px',
      background: 'rgba(255,255,255,0.55)',
      borderRadius: '50%',
      left: (e.clientX - rect.left) + 'px',
      top: (e.clientY - rect.top) + 'px',
      pointerEvents: 'none',
      transform: 'translate(-50%, -50%)',
      transition: 'width 0.6s, height 0.6s, opacity 0.6s'
    });
    btn.appendChild(r);
    requestAnimationFrame(() => {
      r.style.width = r.style.height = '320px';
      r.style.opacity = '0';
    });
    setTimeout(() => r.remove(), 700);
  });
})();
