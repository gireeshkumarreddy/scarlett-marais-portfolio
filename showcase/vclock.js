/* Virtual clock for frame-by-frame recording.
   Replaces timers, requestAnimationFrame, Date and performance.now so every frame of the
   site (GSAP, Lenis, CSS animations) advances by exactly the same step, however slow capture is. */
(() => {
  const RealDate = Date;
  const epoch = RealDate.now();
  let vt = 0, tid = 1, rid = 1;
  const timers = new Map(), rafs = new Map();

  performance.now = () => vt;
  function FakeDate(...a) {
    if (!(this instanceof FakeDate)) return new RealDate(epoch + vt).toString();
    return a.length ? new RealDate(...a) : new RealDate(epoch + vt);
  }
  FakeDate.prototype = RealDate.prototype;
  FakeDate.now = () => epoch + vt;
  FakeDate.parse = RealDate.parse;
  FakeDate.UTC = RealDate.UTC;
  window.Date = FakeDate;

  window.setTimeout = (fn, ms, ...args) => { const id = tid++; timers.set(id, { at: vt + Math.max(0, +ms || 0), fn, args, every: 0 }); return id; };
  window.setInterval = (fn, ms, ...args) => { const every = Math.max(1, +ms || 0), id = tid++; timers.set(id, { at: vt + every, fn, args, every }); return id; };
  window.clearTimeout = window.clearInterval = id => { timers.delete(id); };
  window.requestAnimationFrame = fn => { const id = rid++; rafs.set(id, fn); return id; };
  window.cancelAnimationFrame = id => { rafs.delete(id); };

  window.__advance = ms => {
    const target = vt + ms;
    for (;;) {
      let next = null;
      for (const [id, t] of timers) if (t.at <= target && (!next || t.at < next[1].at)) next = [id, t];
      if (!next) break;
      const [id, t] = next;
      vt = Math.max(vt, t.at);
      if (t.every) t.at += t.every; else timers.delete(id);
      try { typeof t.fn === 'function' ? t.fn(...t.args) : (0, eval)(t.fn); } catch (e) { console.error(e); }
    }
    vt = target;
    const cbs = [...rafs.values()];
    rafs.clear();
    for (const cb of cbs) { try { cb(vt); } catch (e) { console.error(e); } }
    // CSS animations and transitions follow the same clock
    for (const a of document.getAnimations()) {
      if (a.__v0 === undefined) { a.__v0 = vt - (a.currentTime || 0); a.pause(); }
      a.currentTime = vt - a.__v0;
    }
    return vt;
  };
})();
