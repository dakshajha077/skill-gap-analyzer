/**
 * DYNAMIC UI ENHANCEMENTS: Scroll Animations & Parallax Effects
 * Performance-optimized: RAF throttling, cached DOM queries, removed card parallax.
 */

// ── Intersection Observer for Fade-In / Slide-In Animations ──────────────────
document.addEventListener('DOMContentLoaded', function () {
  const observer = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.1, rootMargin: '0px 0px -50px 0px' });

  document.querySelectorAll('.fade-in-on-scroll, .slide-in-left, .slide-in-right, .scale-in')
    .forEach(function (el) { observer.observe(el); });
});

// ── Parallax — clouds only (cards removed to fix scroll lag) ─────────────────
(function () {
  // Cache cloud elements once
  var clouds        = Array.from(document.querySelectorAll('.cloud'));
  var sectionClouds = Array.from(document.querySelectorAll('.section-cloud'));

  if (clouds.length === 0 && sectionClouds.length === 0) return;

  var rafPending = false;

  function applyParallax() {
    var scrollY = window.scrollY;

    clouds.forEach(function (cloud, index) {
      var speed = 1 + index * 0.1;
      cloud.style.transform = 'translateY(' + (scrollY * 0.5 * speed) + 'px)';
    });

    sectionClouds.forEach(function (cloud, index) {
      var speed = 0.3 + index * 0.15;
      cloud.style.transform = 'translateY(' + (scrollY * speed) + 'px) translateX(' +
        (Math.sin(scrollY * 0.002) * 20) + 'px)';
    });

    rafPending = false;
  }

  window.addEventListener('scroll', function () {
    if (!rafPending) {
      rafPending = true;
      requestAnimationFrame(applyParallax);
    }
  }, { passive: true });
})();

// ── Scroll Progress Bar ───────────────────────────────────────────────────────
(function () {
  var progressBar = document.createElement('div');
  progressBar.id = 'scroll-progress-bar';
  Object.assign(progressBar.style, {
    position: 'fixed', top: '0', left: '0',
    height: '3px', width: '0%',
    background: 'linear-gradient(90deg, #4f46e5 0%, #7c3aed 50%, #8b5cf6 100%)',
    zIndex: '9999', willChange: 'width',
    boxShadow: '0 0 10px rgba(79,70,229,0.5)'
  });
  document.body.appendChild(progressBar);

  var rafPending = false;
  window.addEventListener('scroll', function () {
    if (!rafPending) {
      rafPending = true;
      requestAnimationFrame(function () {
        var docH    = document.documentElement.scrollHeight - window.innerHeight;
        var pct     = docH > 0 ? (window.scrollY / docH) * 100 : 0;
        progressBar.style.width = pct + '%';
        rafPending = false;
      });
    }
  }, { passive: true });
})();

// ── Button Click Ripple ───────────────────────────────────────────────────────
document.addEventListener('click', function (e) {
  var btn = e.target.closest('.btn');
  if (!btn) return;

  var ripple = document.createElement('span');
  var rect   = btn.getBoundingClientRect();
  var size   = Math.max(rect.width, rect.height);
  ripple.style.cssText = 'position:absolute;border-radius:50%;background:rgba(255,255,255,0.5);' +
    'transform:scale(0);animation:ripple-animation 0.6s ease-out;pointer-events:none;' +
    'width:' + size + 'px;height:' + size + 'px;' +
    'left:' + (e.clientX - rect.left - size / 2) + 'px;' +
    'top:'  + (e.clientY - rect.top  - size / 2) + 'px;';
  btn.appendChild(ripple);
  setTimeout(function () { ripple.remove(); }, 600);
});

// ── Card Glow on Mouse Move ───────────────────────────────────────────────────
document.querySelectorAll('.glow-effect').forEach(function (card) {
  card.addEventListener('mousemove', function (e) {
    var rect  = this.getBoundingClientRect();
    var glowX = ((e.clientX - rect.left) / rect.width)  * 100;
    var glowY = ((e.clientY - rect.top)  / rect.height) * 100;
    this.style.backgroundImage =
      'radial-gradient(600px at ' + glowX + '% ' + glowY + '%, rgba(79,70,229,0.05), transparent 80%)';
  });
  card.addEventListener('mouseleave', function () {
    this.style.backgroundImage = '';
  });
});

// ── Smooth Scroll for Internal Links ─────────────────────────────────────────
document.querySelectorAll('a[href^="#"]').forEach(function (anchor) {
  anchor.addEventListener('click', function (e) {
    var href = this.getAttribute('href');
    if (href !== '#') {
      e.preventDefault();
      var target = document.querySelector(href);
      if (target) target.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  });
});

// ── Lazy Load Background Images ───────────────────────────────────────────────
(function () {
  var imageObserver = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (entry.isIntersecting) {
        var bg = entry.target.getAttribute('data-bg-image');
        if (bg) {
          Object.assign(entry.target.style, {
            backgroundImage: "url('" + bg + "')",
            backgroundSize: 'cover',
            backgroundPosition: 'center'
          });
        }
        imageObserver.unobserve(entry.target);
      }
    });
  });
  document.querySelectorAll('[data-bg-image]').forEach(function (el) {
    imageObserver.observe(el);
  });
})();

// ── Stagger animation delays for cards ───────────────────────────────────────
document.querySelectorAll('.card').forEach(function (el, index) {
  el.style.animationDelay = (index * 0.1) + 's';
});

// ── Ripple CSS injection ──────────────────────────────────────────────────────
if (!document.getElementById('ripple-styles')) {
  var style = document.createElement('style');
  style.id = 'ripple-styles';
  style.textContent =
    '.btn{overflow:hidden;position:relative;}' +
    '@keyframes ripple-animation{to{transform:scale(4);opacity:0;}}';
  document.head.appendChild(style);
}

// ── Reduce motion for low-end devices ────────────────────────────────────────
if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
  document.body.style.setProperty('--animation-duration', '0.01s');
}
