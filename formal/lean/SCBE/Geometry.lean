import Mathlib.Data.Real.Sqrt
import Mathlib.Algebra.BigOperators.Group.Finset.Basic
import Mathlib.Tactic.Linarith
import Mathlib.Tactic.Positivity
import Mathlib.Tactic.Ring

/- Exact real arithmetic. These theorems do not model IEEE-754 rounding. -/
namespace SCBE

noncomputable section

def safetyScore (distance phase : ℝ) : ℝ := 1 / (1 + distance + 2 * phase)

theorem score_denominator_positive {d p : ℝ} (hd : 0 ≤ d) (hp : 0 ≤ p) :
    0 < 1 + d + 2 * p := by linarith

theorem safetyScore_positive {d p : ℝ} (hd : 0 ≤ d) (hp : 0 ≤ p) :
    0 < safetyScore d p :=
  div_pos zero_lt_one (score_denominator_positive hd hp)

theorem safetyScore_le_one {d p : ℝ} (hd : 0 ≤ d) (hp : 0 ≤ p) :
    safetyScore d p ≤ 1 := by
  unfold safetyScore
  apply (div_le_iff₀ (score_denominator_positive hd hp)).2
  linarith

theorem safetyScore_antitone {d₁ d₂ p₁ p₂ : ℝ}
    (hd : 0 ≤ d₁) (hp : 0 ≤ p₁) (hdd : d₁ ≤ d₂) (hpp : p₁ ≤ p₂) :
    safetyScore d₂ p₂ ≤ safetyScore d₁ p₁ := by
  unfold safetyScore
  apply (div_le_div_iff₀
    (score_denominator_positive (hd.trans hdd) (hp.trans hpp))
    (score_denominator_positive hd hp)).2
  nlinarith

theorem safetyScore_strict_distance {d₁ d₂ p : ℝ}
    (hd : 0 ≤ d₁) (hp : 0 ≤ p) (hdd : d₁ < d₂) :
    safetyScore d₂ p < safetyScore d₁ p := by
  unfold safetyScore
  apply (div_lt_div_iff₀
    (score_denominator_positive (le_trans hd (le_of_lt hdd)) hp)
    (score_denominator_positive hd hp)).2
  nlinarith

/-- A bounded score cannot reach the legacy exponential-score SNAP threshold. -/
theorem bounded_score_never_exceeds_100 {d p : ℝ} (hd : 0 ≤ d) (hp : 0 ≤ p) :
    ¬ (100 < safetyScore d p) := by
  have := safetyScore_le_one hd hp
  linarith

def evidenceRisk (score coherence : ℝ) : ℝ := max (1 - score) (1 - coherence)

theorem evidenceRisk_bounds {s c : ℝ}
    (hs0 : 0 ≤ s) (hs1 : s ≤ 1) (hc0 : 0 ≤ c) :
    0 ≤ evidenceRisk s c ∧ evidenceRisk s c ≤ 1 := by
  constructor
  · exact le_trans (sub_nonneg.mpr hs1) (le_max_left _ _)
  · exact max_le (by linarith) (by linarith)

theorem evidenceRisk_monotone {s₁ s₂ c₁ c₂ : ℝ}
    (hs : s₂ ≤ s₁) (hc : c₂ ≤ c₁) :
    evidenceRisk s₁ c₁ ≤ evidenceRisk s₂ c₂ := by
  exact max_le_max (by linarith) (by linarith)

def phi : ℝ := (1 + Real.sqrt 5) / 2

theorem phi_positive : 0 < phi := by
  have := Real.sqrt_nonneg (5 : ℝ)
  unfold phi
  linarith

theorem tongue_weight_positive (i : Fin 6) : 0 < phi ^ i.val :=
  pow_pos phi_positive _

theorem phi_greater_than_one : 1 < phi := by
  have hs := Real.sq_sqrt (show (0 : ℝ) ≤ 5 by linarith)
  have hn := Real.sqrt_nonneg (5 : ℝ)
  unfold phi
  nlinarith

def weightedEnergy {n : ℕ} (w x : Fin n → ℝ) : ℝ := ∑ i, w i * (x i) ^ 2

theorem weightedEnergy_nonnegative {n : ℕ} (w x : Fin n → ℝ) (hw : ∀ i, 0 ≤ w i) :
    0 ≤ weightedEnergy w x :=
  Finset.sum_nonneg (fun i _ => mul_nonneg (hw i) (sq_nonneg _))

theorem weightedEnergy_positive {n : ℕ} (w x : Fin n → ℝ)
    (hw : ∀ i, 0 < w i) (hx : ∃ i, x i ≠ 0) : 0 < weightedEnergy w x := by
  obtain ⟨i, hi⟩ := hx
  apply Finset.sum_pos'
  · intro j _
    exact mul_nonneg (le_of_lt (hw j)) (sq_nonneg _)
  · exact ⟨i, Finset.mem_univ i, mul_pos (hw i) (sq_pos_of_ne_zero hi)⟩

def normSq {n : ℕ} (u : Fin n → ℝ) : ℝ := ∑ i, (u i) ^ 2
def separationSq {n : ℕ} (u v : Fin n → ℝ) : ℝ := ∑ i, (u i - v i) ^ 2
def poincareArgument {n : ℕ} (u v : Fin n → ℝ) : ℝ :=
  1 + 2 * separationSq u v / ((1 - normSq u) * (1 - normSq v))

theorem separationSq_nonnegative {n : ℕ} (u v : Fin n → ℝ) :
    0 ≤ separationSq u v := Finset.sum_nonneg (fun _ _ => sq_nonneg _)

theorem separationSq_symmetric {n : ℕ} (u v : Fin n → ℝ) :
    separationSq u v = separationSq v u := by
  apply Finset.sum_congr rfl
  intro i _
  ring

theorem poincare_denominator_positive {n : ℕ} {u v : Fin n → ℝ}
    (hu : normSq u < 1) (hv : normSq v < 1) :
    0 < (1 - normSq u) * (1 - normSq v) :=
  mul_pos (sub_pos.mpr hu) (sub_pos.mpr hv)

/-- The acosh argument is in its real inverse-cosh domain inside the open ball. -/
theorem poincareArgument_at_least_one {n : ℕ} {u v : Fin n → ℝ}
    (hu : normSq u < 1) (hv : normSq v < 1) : 1 ≤ poincareArgument u v := by
  have hn := separationSq_nonnegative u v
  have hd := poincare_denominator_positive hu hv
  unfold poincareArgument
  have : 0 ≤ 2 * separationSq u v / ((1 - normSq u) * (1 - normSq v)) := by positivity
  linarith

theorem poincareArgument_symmetric {n : ℕ} (u v : Fin n → ℝ) :
    poincareArgument u v = poincareArgument v u := by
  simp only [poincareArgument, separationSq_symmetric u v, mul_comm]

theorem poincareArgument_self {n : ℕ} (u : Fin n → ℝ) :
    poincareArgument u u = 1 := by
  simp [poincareArgument, separationSq]

end
end SCBE
