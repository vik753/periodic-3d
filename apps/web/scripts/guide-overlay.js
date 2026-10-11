// Injected into the page while the guide video records (scripts/guide-video.mjs).
// Draws what a screen recording would show and the page itself does not: the mouse
// pointer with a ring on each click, captions, title cards and key caps. It also steps
// CSS animations frame by frame (window.__guide.tick), so the video is deterministic.
(() => {
  const css = `
    #guide-root { position: fixed; inset: 0; pointer-events: none; z-index: 2147483647;
      font-family: "Golos Text Variable", "Segoe UI", system-ui, sans-serif; }
    #guide-pointer { position: absolute; left: 0; top: 0; width: 26px; height: 26px;
      transform: translate(-3px, -2px); filter: drop-shadow(0 2px 4px rgba(0,0,0,.55)); }
    .guide-ring { position: absolute; width: 44px; height: 44px; margin: -22px 0 0 -22px;
      border-radius: 50%; border: 3px solid #ffd27a; animation: guide-ring .5s ease-out both; }
    @keyframes guide-ring { from { transform: scale(.3); opacity: 1; } to { transform: scale(1.25); opacity: 0; } }
    #guide-caption { position: absolute; left: 50%; bottom: 34px; max-width: min(78%, 980px);
      transform: translateX(-50%); padding: 14px 24px; border-radius: 18px;
      background: rgba(10, 13, 28, .86); box-shadow: 0 0 0 1px rgba(182,156,255,.35), 0 12px 40px rgba(0,0,0,.45);
      color: #f4f7ff; font-size: 25px; line-height: 1.35; text-align: center; opacity: 0;
      transition: opacity .35s ease; }
    #guide-caption.on { opacity: 1; }
    #guide-caption kbd { display: inline-block; min-width: 1.6em; padding: 1px 9px; margin: 0 2px;
      border-radius: 8px; background: #2a2f4a; box-shadow: inset 0 -2px 0 #11152a, 0 0 0 1px #4b5280;
      font: 600 .86em "Golos Text Variable", system-ui, sans-serif; color: #ffd27a; }
    #guide-caption b { color: #ffd27a; font-weight: 600; }
    #guide-title { position: absolute; inset: 0; display: flex; flex-direction: column;
      align-items: center; justify-content: center; gap: 18px; text-align: center;
      background: radial-gradient(ellipse at center, rgba(8,10,24,.55), rgba(8,10,24,.92));
      opacity: 0; transition: opacity .6s ease; }
    #guide-title.on { opacity: 1; }
    #guide-title h1 { margin: 0; font: 600 64px "Unbounded Variable", system-ui, sans-serif;
      letter-spacing: -.02em; color: #f4f7ff; }
    #guide-title p { margin: 0; font-size: 28px; color: #b69cff; }
    #guide-title small { font-size: 22px; color: rgba(233,238,248,.7); }
  `;
  const pointerSvg = `<svg viewBox="0 0 26 26" width="26" height="26"><path d="M3 2 L3 21 L8.2 16.4 L11.6 24 L15 22.5 L11.7 15 L18.6 15 Z" fill="#fff" stroke="#0b0d18" stroke-width="1.6" stroke-linejoin="round"/></svg>`;

  function mount() {
    if (document.getElementById('guide-root')) return;
    const style = document.createElement('style');
    style.textContent = css;
    document.head.appendChild(style);
    const root = document.createElement('div');
    root.id = 'guide-root';
    root.innerHTML = `<div id="guide-title"></div><div id="guide-caption"></div><div id="guide-pointer">${pointerSvg}</div>`;
    document.body.appendChild(root);
    const pointer = root.querySelector('#guide-pointer');
    window.addEventListener(
      'mousemove',
      (event) => {
        pointer.style.left = `${event.clientX}px`;
        pointer.style.top = `${event.clientY}px`;
      },
      true,
    );
    window.addEventListener(
      'mousedown',
      (event) => {
        const ring = document.createElement('div');
        ring.className = 'guide-ring';
        ring.style.left = `${event.clientX}px`;
        ring.style.top = `${event.clientY}px`;
        root.appendChild(ring);
        rings.push({ ring, age: 0 });
      },
      true,
    );
  }

  const rings = [];
  const seen = new WeakSet();

  window.__guide = {
    mount,
    caption(html) {
      const element = document.getElementById('guide-caption');
      if (!element) return;
      if (html) element.innerHTML = html;
      element.classList.toggle('on', Boolean(html));
    },
    title(html) {
      const element = document.getElementById('guide-title');
      if (!element) return;
      if (html) element.innerHTML = html;
      element.classList.toggle('on', Boolean(html));
    },
    hidePointer(hidden) {
      const pointer = document.getElementById('guide-pointer');
      if (pointer) pointer.style.visibility = hidden ? 'hidden' : 'visible';
    },
    /** Advance every CSS animation and transition by dt milliseconds of video time. */
    tick(dt) {
      for (const animation of document.getAnimations()) {
        if (!seen.has(animation)) {
          // Started during the last real-time gap: restart it on this video frame.
          seen.add(animation);
          animation.pause();
          animation.currentTime = 0;
        } else {
          animation.currentTime = (Number(animation.currentTime) || 0) + dt;
        }
      }
      for (let i = rings.length - 1; i >= 0; i -= 1) {
        rings[i].age += dt;
        if (rings[i].age > 700) {
          rings[i].ring.remove();
          rings.splice(i, 1);
        }
      }
    },
  };

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount);
  else mount();
})();
