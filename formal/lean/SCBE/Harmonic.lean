import SCBE.Geometry
import Mathlib.Analysis.SpecialFunctions.Pow.Real

namespace SCBE
noncomputable section

/-- QUADRATIC_EXP_COST, kept separate from the bounded L12 safety score. -/
def harmonicCost (base distance : ℝ) : ℝ := base ^ (distance ^ 2)

theorem harmonicCost_at_least_one {r d : ℝ} (hr : 1 ≤ r) :
    1 ≤ harmonicCost r d := Real.one_le_rpow hr (sq_nonneg d)

theorem harmonicCost_monotone {r d₁ d₂ : ℝ}
    (hr : 1 ≤ r) (hd : 0 ≤ d₁) (hdd : d₁ ≤ d₂) :
    harmonicCost r d₁ ≤ harmonicCost r d₂ := by
  apply Real.rpow_le_rpow_of_exponent_le hr
  nlinarith

theorem harmonicCost_strict {r d₁ d₂ : ℝ}
    (hr : 1 < r) (hd : 0 ≤ d₁) (hdd : d₁ < d₂) :
    harmonicCost r d₁ < harmonicCost r d₂ := by
  apply Real.rpow_lt_rpow_of_exponent_lt hr
  nlinarith

theorem cost_and_score_have_opposite_orders {r d₁ d₂ p : ℝ}
    (hr : 1 < r) (hd : 0 ≤ d₁) (hp : 0 ≤ p) (hdd : d₁ < d₂) :
    harmonicCost r d₁ < harmonicCost r d₂ ∧ safetyScore d₂ p < safetyScore d₁ p :=
  ⟨harmonicCost_strict hr hd hdd, safetyScore_strict_distance hd hp hdd⟩

end
end SCBE
