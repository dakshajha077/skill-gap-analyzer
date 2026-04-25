/**
 * 3D Animations - Interactive 3D Effects
 * Includes mouse tracking, scroll-based animations, and 3D transformations
 */

document.addEventListener('DOMContentLoaded', () => {
  // ═══════════════════════════════════════════════════════════════
  // MOUSE MOVEMENT TRACKING FOR 3D EFFECTS
  // ═══════════════════════════════════════════════════════════════
  
  let mouseX = window.innerWidth / 2;
  let mouseY = window.innerHeight / 2;
  let mouseMoveRaf = false;

  document.addEventListener('mousemove', (e) => {
    mouseX = e.clientX;
    mouseY = e.clientY;

    if (!mouseMoveRaf) {
      mouseMoveRaf = true;
      requestAnimationFrame(() => {
        updateCubeRotations();
        updateShapesParallax();
        mouseMoveRaf = false;
      });
    }
  }, { passive: true });
  
  // ═══════════════════════════════════════════════════════════════
  // CUBE ROTATION BASED ON MOUSE
  // ═══════════════════════════════════════════════════════════════
  
  // Cache DOM elements once
  const _cubes  = Array.from(document.querySelectorAll('.cube-3d'));
  const _shapes = Array.from(document.querySelectorAll('.morphing-square, .pyramid-3d'));
  const _orbs   = Array.from(document.querySelectorAll('.glowing-orb'));

  function updateCubeRotations() {
    const cubes = _cubes;
    const centerX = window.innerWidth / 2;
    const centerY = window.innerHeight / 2;
    
    cubes.forEach(cube => {
      const rect = cube.getBoundingClientRect();
      const cubeX = rect.left + rect.width / 2;
      const cubeY = rect.top + rect.height / 2;
      
      const deltaX = mouseX - cubeX;
      const deltaY = mouseY - cubeY;
      
      const rotateX = (deltaY / window.innerHeight) * 20;
      const rotateY = (deltaX / window.innerWidth) * 20;
      
      // Subtle rotation effect - remove animation style to apply mouse effect
      cube.style.animation = 'none';
      cube.style.transform = `rotateX(${rotateX}deg) rotateY(${rotateY}deg)`;
    });
  }
  
  // ═══════════════════════════════════════════════════════════════
  // PARALLAX EFFECT FOR FLOATING SHAPES
  // ═══════════════════════════════════════════════════════════════
  
  function updateShapesParallax() {
    const shapes = _shapes;
    const centerX = window.innerWidth / 2;
    const centerY = window.innerHeight / 2;
    
    shapes.forEach(shape => {
      const rect = shape.getBoundingClientRect();
      const shapeX = rect.left + rect.width / 2;
      const shapeY = rect.top + rect.height / 2;
      
      const distX = (mouseX - centerX) * 0.02;
      const distY = (mouseY - centerY) * 0.02;
      
      shape.style.transform = `translate(${distX}px, ${distY}px)`;
    });
  }
  
  // ═══════════════════════════════════════════════════════════════
  // SCROLL-BASED 3D TRANSFORMS
  // ═══════════════════════════════════════════════════════════════
  
  let scrollY = 0;
  let rafId = null;
  
  window.addEventListener('scroll', () => {
    scrollY = window.scrollY;
    if (rafId) cancelAnimationFrame(rafId);
    rafId = requestAnimationFrame(updateScrollAnimations);
  });
  
  function updateScrollAnimations() {
    const orbs = document.querySelectorAll('.glowing-orb');
    const shapes = document.querySelectorAll('.morphing-square');
    
    orbs.forEach((orb, index) => {
      const offset = (scrollY * 0.5 + index * 100) % 1000;
      orb.style.cssText += `transform: translateY(${offset}px) rotateZ(${scrollY * 0.2}deg);`;
    });
    
    shapes.forEach((shape, index) => {
      const offset = (scrollY * 0.3 + index * 80) % 800;
      shape.style.cssText += `transform: translateX(${offset}px) rotateZ(${scrollY * 0.1}deg);`;
    });
  }
  
  // ═══════════════════════════════════════════════════════════════
  // INTERSECTION OBSERVER FOR FADE-IN ANIMATIONS
  // ═══════════════════════════════════════════════════════════════
  
  const fadeElements = document.querySelectorAll('.fade-in-on-scroll, .glow-effect');
  
  const observerOptions = {
    threshold: 0.1,
    rootMargin: '0px 0px -50px 0px'
  };
  
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('animated');
        entry.target.style.animation = 'fadeInUp 0.8s ease-out forwards';
        observer.unobserve(entry.target);
      }
    });
  }, observerOptions);
  
  fadeElements.forEach(el => observer.observe(el));
  
  // ═══════════════════════════════════════════════════════════════
  // CARD HOVER EFFECTS
  // ═══════════════════════════════════════════════════════════════
  
  const cards = document.querySelectorAll('.card');
  
  cards.forEach(card => {
    card.addEventListener('mouseenter', function() {
      this.style.transition = 'all 0.6s cubic-bezier(0.34, 1.56, 0.64, 1)';
      this.style.transform = 'translateY(-12px) rotateX(5deg) rotateY(-2deg)';
      this.style.boxShadow = `
        0 0 20px rgba(16, 185, 229, 0.4),
        0 20px 40px rgba(0, 0, 0, 0.15),
        inset 0 0 20px rgba(16, 185, 229, 0.1)
      `;
    });
    
    card.addEventListener('mouseleave', function() {
      this.style.transform = '';
      this.style.boxShadow = '';
    });
  });
  
  // ═══════════════════════════════════════════════════════════════
  // GLOW INTENSIFICATION ON HOVER
  // ═══════════════════════════════════════════════════════════════
  
  const glowElements = document.querySelectorAll('.glow-effect, .glow-intense');
  
  glowElements.forEach(element => {
    element.addEventListener('mouseenter', function() {
      this.style.transition = 'all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1)';
      this.style.boxShadow = `
        0 12px 30px rgba(16, 185, 229, 0.3),
        0 0 50px rgba(139, 92, 246, 0.2),
        inset 0 0 30px rgba(16, 185, 229, 0.15)
      `;
      this.style.transform = 'scale(1.02)';
    });
    
    element.addEventListener('mouseleave', function() {
      this.style.boxShadow = '';
      this.style.transform = '';
    });
  });
  
  // ═══════════════════════════════════════════════════════════════
  // ANIMATED 3D BAR CHARTS
  // ═══════════════════════════════════════════════════════════════
  
  const barCharts = document.querySelectorAll('.bar-chart-3d');
  
  barCharts.forEach(chart => {
    chart.addEventListener('mouseenter', function() {
      const bars = this.querySelectorAll('.bar-3d');
      bars.forEach((bar, index) => {
        bar.style.animation = `barRotate 2s ease-in-out ${index * 0.15}s infinite`;
      });
    });
    
    chart.addEventListener('mouseleave', function() {
      const bars = this.querySelectorAll('.bar-3d');
      bars.forEach(bar => {
        bar.style.animation = '';
      });
    });
  });
  
  // ═══════════════════════════════════════════════════════════════
  // BUTTON HOVER EFFECTS
  // ═══════════════════════════════════════════════════════════════
  
  const buttons = document.querySelectorAll('.btn');
  
  buttons.forEach(btn => {
    btn.addEventListener('mouseenter', function() {
      this.style.transition = 'all 0.4s cubic-bezier(0.34, 1.56, 0.64, 1)';
      this.style.transform = 'translateY(-3px) scale(1.05)';
      if (this.classList.contains('nav-yellow-glow')) {
        this.style.filter = 'drop-shadow(0 10px 26px rgba(251, 191, 36, 0.55))';
      } else {
        this.style.filter = 'drop-shadow(0 8px 20px rgba(16, 185, 229, 0.4))';
      }
    });
    
    btn.addEventListener('mouseleave', function() {
      this.style.transform = '';
      this.style.filter = '';
    });
  });
  
  // ═══════════════════════════════════════════════════════════════
  // RESPONSIVE SHAPE POSITIONING
  // ═══════════════════════════════════════════════════════════════
  
  window.addEventListener('resize', () => {
    updateCubeRotations();
    updateShapesParallax();
  });
  
  // ═══════════════════════════════════════════════════════════════
  // PAGE LOAD ANIMATION
  // ═══════════════════════════════════════════════════════════════
  
  document.body.classList.add('page-loaded');
});

/**
 * ADD CUSTOM ANIMATIONS TO STYLESHEET
 */
const animationStyles = document.createElement('style');
animationStyles.textContent = `
  @keyframes fadeInUp {
    from {
      opacity: 0;
      transform: translateY(30px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }
  
  @keyframes glowPulseIntense {
    0%, 100% {
      filter: drop-shadow(0 0 10px rgba(16, 185, 229, 0.6));
      box-shadow: 0 0 20px rgba(16, 185, 229, 0.4);
    }
    50% {
      filter: drop-shadow(0 0 30px rgba(16, 185, 229, 0.9));
      box-shadow: 0 0 40px rgba(16, 185, 229, 0.8), 0 0 60px rgba(139, 92, 246, 0.6);
    }
  }
  
  @keyframes textGlow {
    0%, 100% { text-shadow: 0 0 5px rgba(79, 70, 229, 0.2); }
    50% { text-shadow: 0 0 15px rgba(79, 70, 229, 0.6); }
  }
  
  .page-loaded {
    animation: fadeInUp 0.6s ease-out;
  }
  
  /* Ensure morphing shapes maintain animation */
  .morphing-square, .pyramid-3d, .glowing-orb {
    will-change: transform;
  }
`;
document.head.appendChild(animationStyles);
