(() => {
  const runDemoButtons = document.querySelectorAll("[data-aether-run-demo='true']");

  runDemoButtons.forEach((button) => {
    button.addEventListener("click", () => {
      const eventPayload = {
        action: "run_demo_click",
        timestamp: new Date().toISOString(),
      };
      console.info("[Aether Creator OS] Intent event:", eventPayload);
    });
  });

  const hero = document.querySelector(".aether-hero");
  if (!hero) return;

  const intensity = Number(hero.dataset.fractalIntensity || "0");
  hero.style.setProperty("--aether-fractal-opacity", String(Math.min(Math.max(intensity / 100, 0), 1)));
})();

