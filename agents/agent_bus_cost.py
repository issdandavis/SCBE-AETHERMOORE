"""
Agent Bus cost metering + budget enforcement.

Closes the "cost tracking" gap from AGENT_BUS_NOTES.md: every LLM call is
priced in USD-equivalent from per-provider token rates, accumulated on a
session meter, and the `--budget` CLI flag becomes a hard gate instead of
advisory. The bus's default providers (Ollama local, HuggingFace free
serverless) price at $0.00 — the meter exists so paid endpoints can be
dropped in without re-plumbing, and so events carry an auditable
`cost_usd` field either way.

Rates are overridable without code changes via the AGENT_BUS_RATES_JSON
environment variable:

    AGENT_BUS_RATES_JSON='{"huggingface": {"in": 0.30, "out": 1.20}}'

where "in"/"out" are USD per 1k tokens.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from typing import Dict, Optional

logger = logging.getLogger("scbe.agent_bus.cost")

RATES_ENV_VAR = "AGENT_BUS_RATES_JSON"


@dataclass(frozen=True)
class ProviderRates:
    """USD per 1k tokens, split by direction."""

    usd_per_1k_in: float = 0.0
    usd_per_1k_out: float = 0.0


# The bus is free-tier by design (see agent_bus module docstring); rates are
# zero until a paid provider is configured. Unknown providers also price at
# zero rather than blocking — cost tracking must never take the bus down.
DEFAULT_RATES: Dict[str, ProviderRates] = {
    "ollama": ProviderRates(),
    "huggingface": ProviderRates(),
    "offline": ProviderRates(),
}


def load_rates(env: Optional[Dict[str, str]] = None) -> Dict[str, ProviderRates]:
    """Build the rate table: defaults overlaid with AGENT_BUS_RATES_JSON.

    Malformed JSON or entries are logged and skipped — never raises.
    """
    rates = dict(DEFAULT_RATES)
    raw = (env if env is not None else os.environ).get(RATES_ENV_VAR)
    if not raw:
        return rates
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.warning("%s is not valid JSON (%s); using default rates", RATES_ENV_VAR, exc)
        return rates
    if not isinstance(parsed, dict):
        logger.warning("%s must be a JSON object; using default rates", RATES_ENV_VAR)
        return rates
    for provider, entry in parsed.items():
        try:
            rates[str(provider)] = ProviderRates(
                usd_per_1k_in=float(entry.get("in", 0.0)),
                usd_per_1k_out=float(entry.get("out", 0.0)),
            )
        except (AttributeError, TypeError, ValueError) as exc:
            logger.warning("%s entry %r is malformed (%s); skipped", RATES_ENV_VAR, provider, exc)
    return rates


@dataclass
class CostMeter:
    """Session cost accumulator with an optional hard budget.

    budget_usd == 0 means unbounded (the historical default), matching the
    CLI's `--budget 0` semantics.
    """

    budget_usd: float = 0.0
    rates: Dict[str, ProviderRates] = field(default_factory=load_rates)
    spent_usd: float = 0.0

    def price(self, provider: str, tokens_in: int, tokens_out: int) -> float:
        """USD-equivalent price of one call. Unknown providers price at 0."""
        r = self.rates.get(provider, ProviderRates())
        return (tokens_in / 1000.0) * r.usd_per_1k_in + (tokens_out / 1000.0) * r.usd_per_1k_out

    def charge(self, provider: str, tokens_in: int, tokens_out: int) -> float:
        """Price one call, add it to the session total, and return the cost."""
        cost = self.price(provider, tokens_in, tokens_out)
        self.spent_usd += cost
        return cost

    @property
    def exceeded(self) -> bool:
        """True once spending has reached a nonzero budget."""
        return self.budget_usd > 0 and self.spent_usd >= self.budget_usd

    @property
    def remaining_usd(self) -> Optional[float]:
        """Budget headroom, or None when unbounded."""
        if self.budget_usd <= 0:
            return None
        return max(0.0, self.budget_usd - self.spent_usd)
