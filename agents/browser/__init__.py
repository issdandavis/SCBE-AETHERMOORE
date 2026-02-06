"""
SCBE-AETHERMOORE Browser Agent with PHDM Brain
================================================

Geometrically-contained browser automation using Poincaré ball model
for provable safety boundaries on autonomous agent actions.

Components:
    - SimplePHDM: Poincaré Half-Disk Model brain for geometric containment
    - PHDMPlaywrightBrowser: PHDM-governed Playwright browser wrapper
"""

from .phdm_brain import SimplePHDM
from .playwright_wrapper import PHDMPlaywrightBrowser

__all__ = ["SimplePHDM", "PHDMPlaywrightBrowser"]
