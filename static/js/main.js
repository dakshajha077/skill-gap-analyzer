document.addEventListener('DOMContentLoaded', () => {
  // Auto-dismiss flash messages after 5 seconds
  setTimeout(() => {
    document.querySelectorAll('[id^="flash-"]').forEach(el => {
      el.style.animation = 'fadeOut 0.5s ease-out forwards';
      setTimeout(() => el.remove(), 500);
    });
  }, 5000);

  // Add smooth scroll behavior
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
      e.preventDefault();
      const target = document.querySelector(this.getAttribute('href'));
      if (target) {
        target.scrollIntoView({ behavior: 'smooth' });
      }
    });
  });

  // Page load animation trigger
  document.body.classList.add('page-loaded');
});

// Fade out animation
const style = document.createElement('style');
style.textContent = `
  @keyframes fadeOut {
    from { opacity: 1; transform: translateY(0); }
    to { opacity: 0; transform: translateY(-10px); }
  }
  .page-loaded { animation: fadeInUp 0.5s ease-out; }
`;
document.head.appendChild(style);
