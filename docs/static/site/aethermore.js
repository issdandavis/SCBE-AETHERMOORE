(() => {
  const menuButton = document.querySelector('[data-menu-toggle]');
  const navigation = document.querySelector('[data-site-nav]');

  const closeMenu = () => {
    if (!menuButton || !navigation) return;
    menuButton.setAttribute('aria-expanded', 'false');
    navigation.dataset.open = 'false';
    menuButton.textContent = 'Menu';
  };

  if (menuButton && navigation) {
    menuButton.addEventListener('click', () => {
      const open = menuButton.getAttribute('aria-expanded') !== 'true';
      menuButton.setAttribute('aria-expanded', String(open));
      navigation.dataset.open = String(open);
      menuButton.textContent = open ? 'Close' : 'Menu';
    });

    navigation.addEventListener('click', (event) => {
      if (event.target.closest('a')) closeMenu();
    });

    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape') {
        closeMenu();
        menuButton.focus();
      }
    });
  }

  const routeCopy = {
    1: {
      label: '1 · Proposal',
      description:
        'The model proposes an action and explicit arguments; a proposal has no authority by itself.',
    },
    2: {
      label: '2 · Capability',
      description:
        'The host checks identity, capability, limits, and replay state before an effect.',
    },
    3: {
      label: '3 · Isolation',
      description:
        'Approved work enters a bounded worker without ambient access to unrelated tools or data.',
    },
    4: {
      label: '4 · Action',
      description: 'The permitted effect runs inside the declared scope and time limit.',
    },
    5: {
      label: '5 · Receipt',
      description:
        'Inputs, policy decision, execution result, and remaining human work are recorded.',
    },
  };

  const routeMap = document.querySelector('[data-route-map]');
  const routeButtons = [...document.querySelectorAll('[data-route-step]')];
  const routeReadout = document.querySelector('[data-route-readout]');
  const routeDescription = document.querySelector('[data-route-description]');

  const setRouteStep = (step) => {
    const copy = routeCopy[step];
    if (!copy || !routeMap) return;
    routeMap.dataset.activeStep = String(step);
    if (routeReadout) routeReadout.textContent = copy.label;
    if (routeDescription) routeDescription.textContent = copy.description;
    routeButtons.forEach((button) => {
      if (Number(button.dataset.routeStep) === step) {
        button.setAttribute('aria-current', 'step');
      } else {
        button.removeAttribute('aria-current');
      }
    });
  };

  routeButtons.forEach((button, index) => {
    button.addEventListener('click', () => setRouteStep(Number(button.dataset.routeStep)));
    button.addEventListener('keydown', (event) => {
      if (!['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'].includes(event.key)) return;
      event.preventDefault();
      const direction = ['ArrowRight', 'ArrowDown'].includes(event.key) ? 1 : -1;
      const next = routeButtons[(index + direction + routeButtons.length) % routeButtons.length];
      next.focus();
      next.click();
    });
  });

  const boundaryCopy = {
    1: ['Checkpoint 1 · Input', 'The request is named and normalized before it can become a plan.'],
    2: [
      'Checkpoint 2 · Proposal',
      'The model returns a structured action and arguments; it does not execute them.',
    ],
    3: [
      'Checkpoint 3 · Capability',
      'Policy, identity, limits, and replay state are checked at the boundary.',
    ],
    4: [
      'Checkpoint 4 · Isolation',
      'The permitted action runs without ambient authority and within a fixed lifetime.',
    ],
    5: [
      'Checkpoint 5 · Receipt',
      'The system preserves what was requested, decided, executed, and left unresolved.',
    ],
  };

  const boundaryCanvas = document.querySelector('[data-boundary-canvas]');
  const boundaryButtons = [...document.querySelectorAll('[data-boundary-step]')];
  const boundaryKicker = document.querySelector('[data-boundary-kicker]');
  const boundaryDescription = document.querySelector('[data-boundary-description]');
  const traceButton = document.querySelector('[data-trace-path]');
  let traceTimer = null;

  const setBoundaryStep = (step) => {
    const copy = boundaryCopy[step];
    if (!copy || !boundaryCanvas) return;
    boundaryCanvas.dataset.activeBoundary = String(step);
    if (boundaryKicker) boundaryKicker.textContent = copy[0];
    if (boundaryDescription) boundaryDescription.textContent = copy[1];
    boundaryButtons.forEach((button) => {
      if (Number(button.dataset.boundaryStep) === step) {
        button.setAttribute('aria-current', 'step');
      } else {
        button.removeAttribute('aria-current');
      }
    });
  };

  boundaryButtons.forEach((button, index) => {
    button.addEventListener('click', () => {
      if (traceTimer) window.clearTimeout(traceTimer);
      traceTimer = null;
      setBoundaryStep(Number(button.dataset.boundaryStep));
    });
    button.addEventListener('keydown', (event) => {
      if (!['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'].includes(event.key)) return;
      event.preventDefault();
      const direction = ['ArrowRight', 'ArrowDown'].includes(event.key) ? 1 : -1;
      const next =
        boundaryButtons[(index + direction + boundaryButtons.length) % boundaryButtons.length];
      next.focus();
      next.click();
    });
  });

  if (traceButton) {
    traceButton.addEventListener('click', () => {
      if (traceTimer) {
        window.clearTimeout(traceTimer);
        traceTimer = null;
      }
      const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      if (reducedMotion) {
        setBoundaryStep(5);
        return;
      }
      let step = 1;
      const advance = () => {
        setBoundaryStep(step);
        if (step < 5) {
          step += 1;
          traceTimer = window.setTimeout(advance, 430);
        } else {
          traceTimer = null;
        }
      };
      advance();
    });
  }
})();
