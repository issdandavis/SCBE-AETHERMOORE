(() => {
  const nodes = document.querySelectorAll('.reveal');
  if (!('IntersectionObserver' in window) || nodes.length === 0) {
    nodes.forEach((node) => node.classList.add('is-visible'));
    return;
  }

  const observer = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-visible');
          observer.unobserve(entry.target);
        }
      }
    },
    { threshold: 0.16 },
  );

  nodes.forEach((node) => observer.observe(node));
})();
