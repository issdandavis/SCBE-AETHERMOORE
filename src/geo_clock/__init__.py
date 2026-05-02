"""geo_clock — Auto-updating geo-clock for deployed AI agents.

Concentric-shell layout:

  * L0 ``agent_location``  — resolve where the agent is (with confidence)
  * L1 ``anchors``         — Earth anchor table (zone meridians, key sites)
  * L2 ``latency``         — fiber / LEO / vacuum RTT floors
  * L3 ``iss``             — ISS sub-point (open-notify, fail-soft)
  * L4 ``bodies``          — Moon + Mars (EDE constants, optional Horizons)
  * L5 ``compass``         — composer that bundles all of the above

Most callers want just two names::

    from src.geo_clock import compass, resolve
    view = compass(resolve())
"""

from .agent_location import AgentLocation, resolve
from .compass import compass

__all__ = ["AgentLocation", "compass", "resolve"]
