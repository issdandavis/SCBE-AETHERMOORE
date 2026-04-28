"""Conditional constrained-decoding booster.

Engages a regex-grammar logits processor only when measured contract trend
underperforms expectation derived from in-session and prior-session telemetry.
Latches once fired so a single recovery turn doesn't disengage the brake.

Trend signal:
  primary  = log entry "contract_eval_accuracy"   (set by ContractEvalCallback)
  fallback = log entry "mean_token_accuracy"      (HF Trainer default)

Expectation:
  expected_slope = 0.6 * in_session_slope_from_first_three
                 + 0.4 * median(prior_session_slopes)

Fire condition:
  measured_slope < fire_ratio * expected_slope
  for `consecutive_required` consecutive eval steps.

When engaged, downstream generators (ContractEvalCallback, post-train scorer)
read `is_engaged()` and wrap `model.generate(...)` with a lm-format-enforcer
RegexParser. The booster itself does not modify weights or generate.
"""

from __future__ import annotations

import json
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

try:
    from transformers import TrainerCallback, TrainerControl, TrainerState, TrainingArguments
except Exception:  # pragma: no cover - allow import in eval-only contexts
    TrainerCallback = object  # type: ignore[assignment,misc]
    TrainerState = object  # type: ignore[assignment,misc]
    TrainerControl = object  # type: ignore[assignment,misc]
    TrainingArguments = object  # type: ignore[assignment,misc]


_TONGUE = r"(?:KO|AV|RU|CA|UM|DR)"
DSL_GRAMMAR = (
    r"(?:well_select\([A-Z][A-Z0-9_]{0,23}\)"
    rf"|tongue_shift\({_TONGUE} -> {_TONGUE}\)"
    r"|seal\(\))(?:\n#[^\n]*)*"
)


@dataclass
class _SlopeWindow:
    values: list[tuple[float, float]] = field(default_factory=list)  # (step, metric)

    def add(self, step: float, value: float) -> None:
        self.values.append((float(step), float(value)))

    def trailing(self, k: int) -> list[tuple[float, float]]:
        return self.values[-k:] if len(self.values) >= k else list(self.values)

    def linear_slope(self, k: int) -> float | None:
        pts = self.trailing(k)
        if len(pts) < 2:
            return None
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        n = len(pts)
        sx = sum(xs)
        sy = sum(ys)
        sxx = sum(x * x for x in xs)
        sxy = sum(x * y for x, y in zip(xs, ys))
        denom = n * sxx - sx * sx
        if denom == 0:
            return None
        return (n * sxy - sx * sy) / denom


def _scan_prior_session_slopes(reports_dir: Path, metric_keys: Iterable[str]) -> list[float]:
    slopes: list[float] = []
    if not reports_dir.exists():
        return slopes
    for path in sorted(reports_dir.glob("*_training_curve_*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        metrics = payload.get("metrics") or []
        if not isinstance(metrics, list) or len(metrics) < 4:
            continue
        # First-three-step slope on whichever metric key exists in the report.
        for key in metric_keys:
            ys = [m.get(key) for m in metrics[:3] if isinstance(m, dict) and m.get(key) is not None]
            if len(ys) < 2:
                continue
            xs = list(range(len(ys)))
            n = len(ys)
            sx = sum(xs)
            sy = sum(ys)
            sxx = sum(x * x for x in xs)
            sxy = sum(x * y for x, y in zip(xs, ys))
            denom = n * sxx - sx * sx
            if denom == 0:
                continue
            slopes.append((n * sxy - sx * sy) / denom)
            break
    return slopes


class TrendGrowthBooster(TrainerCallback):  # type: ignore[misc]
    """Latching trigger that engages constrained decoding on growth shortfall.

    Args:
        trend_window:        eval steps in the trailing slope window (default 3).
        fire_ratio:          measured/expected ratio that counts as a shortfall (default 0.5).
        consecutive_required:eval steps the shortfall must persist (default 2).
        in_session_weight:   weight on in-session expectation (default 0.6).
        prior_session_weight:weight on prior-session expectation (default 0.4).
        primary_metric:      log key for trend metric (default "contract_eval_accuracy").
        fallback_metric:     log key when primary is missing (default "mean_token_accuracy").
        prior_reports_dir:   directory of *_training_curve_*.json reports.
        fire_log_path:       jsonl audit trail; written each fire/check.
        latch:               once True, stays engaged for the rest of the run.
    """

    def __init__(
        self,
        *,
        trend_window: int = 3,
        fire_ratio: float = 0.5,
        consecutive_required: int = 2,
        in_session_weight: float = 0.6,
        prior_session_weight: float = 0.4,
        primary_metric: str = "contract_eval_accuracy",
        fallback_metric: str = "mean_token_accuracy",
        prior_reports_dir: str | Path = "artifacts/training_reports",
        fire_log_path: str | Path = "artifacts/training_reports/booster_fire_log.jsonl",
        latch: bool = True,
    ) -> None:
        self.trend_window = max(2, int(trend_window))
        self.fire_ratio = float(fire_ratio)
        self.consecutive_required = max(1, int(consecutive_required))
        self.in_session_weight = float(in_session_weight)
        self.prior_session_weight = float(prior_session_weight)
        self.primary_metric = primary_metric
        self.fallback_metric = fallback_metric
        self.prior_reports_dir = Path(prior_reports_dir)
        self.fire_log_path = Path(fire_log_path)
        self._latch = bool(latch)

        self._engaged: bool = False
        self._consecutive_short: int = 0
        self._window = _SlopeWindow()
        self._first_three: list[tuple[float, float]] = []
        self._prior_slopes: list[float] = _scan_prior_session_slopes(
            self.prior_reports_dir,
            (self.primary_metric, self.fallback_metric),
        )
        self.grammar: str = DSL_GRAMMAR

    def is_engaged(self) -> bool:
        return self._engaged

    def disengage(self) -> None:
        if not self._latch:
            self._engaged = False
            self._consecutive_short = 0

    def _read_metric(self, log_history: list[dict]) -> tuple[float, float] | None:
        for entry in reversed(log_history):
            if not isinstance(entry, dict):
                continue
            step = entry.get("step")
            if step is None:
                continue
            for key in (self.primary_metric, self.fallback_metric):
                value = entry.get(key)
                if value is None:
                    continue
                return float(step), float(value)
        return None

    def _expected_slope(self) -> float | None:
        in_slope: float | None = None
        if len(self._first_three) >= 2:
            xs = [p[0] for p in self._first_three]
            ys = [p[1] for p in self._first_three]
            n = len(xs)
            sx = sum(xs)
            sy = sum(ys)
            sxx = sum(x * x for x in xs)
            sxy = sum(x * y for x, y in zip(xs, ys))
            denom = n * sxx - sx * sx
            if denom != 0:
                in_slope = (n * sxy - sx * sy) / denom

        prior_median = statistics.median(self._prior_slopes) if self._prior_slopes else None

        if in_slope is None and prior_median is None:
            return None
        if in_slope is None:
            return prior_median
        if prior_median is None:
            return in_slope
        return self.in_session_weight * in_slope + self.prior_session_weight * prior_median

    def _log(self, payload: dict) -> None:
        try:
            self.fire_log_path.parent.mkdir(parents=True, exist_ok=True)
            with self.fire_log_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(payload, sort_keys=True) + "\n")
        except Exception:
            pass

    def evaluate(self, log_history: list[dict]) -> dict:
        """Side-effect-free check; returns decision dict."""
        sample = self._read_metric(log_history)
        if sample is None:
            return {"sampled": False, "engaged": self._engaged}

        step, value = sample
        if not self._window.values or step != self._window.values[-1][0]:
            self._window.add(step, value)
            if len(self._first_three) < 3:
                self._first_three.append((step, value))

        measured = self._window.linear_slope(self.trend_window)
        expected = self._expected_slope()
        decision = {
            "sampled": True,
            "step": step,
            "value": value,
            "measured_slope": measured,
            "expected_slope": expected,
            "engaged": self._engaged,
            "consecutive_short": self._consecutive_short,
        }

        if self._engaged and self._latch:
            return decision
        if measured is None or expected is None:
            return decision

        threshold = self.fire_ratio * expected
        is_short = measured < threshold if expected > 0 else measured < 0
        if is_short:
            self._consecutive_short += 1
        else:
            self._consecutive_short = 0
        decision["consecutive_short"] = self._consecutive_short
        decision["threshold"] = threshold

        if self._consecutive_short >= self.consecutive_required:
            self._engaged = True
            decision["engaged"] = True
            decision["fired_at_utc"] = datetime.now(timezone.utc).isoformat()
            self._log(
                {
                    "event": "fire",
                    **{k: v for k, v in decision.items() if k != "sampled"},
                    "prior_slopes": self._prior_slopes,
                    "trend_window": self.trend_window,
                    "fire_ratio": self.fire_ratio,
                    "primary_metric": self.primary_metric,
                    "fallback_metric": self.fallback_metric,
                }
            )
        return decision

    # transformers TrainerCallback hooks -------------------------------------------------
    def on_evaluate(self, args, state, control, **kwargs):  # type: ignore[override]
        log_history = getattr(state, "log_history", None) or []
        self.evaluate(list(log_history))
        return control

    def on_step_end(self, args, state, control, **kwargs):  # type: ignore[override]
        log_history = getattr(state, "log_history", None) or []
        if log_history:
            self.evaluate(list(log_history))
        return control
