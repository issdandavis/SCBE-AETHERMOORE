import SCBE.Geometry
import Mathlib.Tactic.FieldSimp

namespace SCBE

/-- Exact interval authority; polarity and address labels remain separate metadata. -/
structure RegionCell where
  lower : ℚ
  width : ℚ
  width_pos : 0 < width

def cellUpper (c : RegionCell) : ℚ := c.lower + c.width
def inCell (c : RegionCell) (x : ℚ) : Prop := c.lower ≤ x ∧ x < cellUpper c
def cellWithin (inner outer : RegionCell) : Prop :=
  outer.lower ≤ inner.lower ∧ cellUpper inner ≤ cellUpper outer

structure CellSplit where
  radix : Nat
  at_least_two : 2 ≤ radix
  index : Fin radix

theorem split_radix_positive (s : CellSplit) : (0 : ℚ) < s.radix := by
  exact_mod_cast (lt_of_lt_of_le (by decide : 0 < 2) s.at_least_two)

def childCell (c : RegionCell) (s : CellSplit) : RegionCell where
  lower := c.lower + (c.width / s.radix) * s.index.val
  width := c.width / s.radix
  width_pos := div_pos c.width_pos (split_radix_positive s)

theorem child_within_parent (c : RegionCell) (s : CellSplit) :
    cellWithin (childCell c s) c := by
  have hn := split_radix_positive s
  have hw := (childCell c s).width_pos
  have hi : (0 : ℚ) ≤ s.index.val := by positivity
  have hj : (s.index.val : ℚ) + 1 ≤ s.radix := by
    exact_mod_cast (Nat.succ_le_of_lt s.index.isLt)
  have hm := mul_le_mul_of_nonneg_left hj (le_of_lt hw)
  have hc : c.width / (s.radix : ℚ) * s.radix = c.width :=
    div_mul_cancel₀ _ (ne_of_gt hn)
  dsimp [cellWithin, childCell, cellUpper] at *
  constructor
  · exact le_add_of_nonneg_right (mul_nonneg (le_of_lt hw) hi)
  · nlinarith

theorem child_width_strictly_decreases (c : RegionCell) (s : CellSplit) :
    (childCell c s).width < c.width := by
  have hn := split_radix_positive s
  have htwo : (2 : ℚ) ≤ s.radix := by exact_mod_cast s.at_least_two
  apply (div_lt_iff₀ hn).2
  nlinarith [c.width_pos]

theorem cellWithin_trans {a b c : RegionCell}
    (hab : cellWithin a b) (hbc : cellWithin b c) : cellWithin a c :=
  ⟨hbc.1.trans hab.1, hab.2.trans hbc.2⟩

theorem contained_point_in_parent {inner outer : RegionCell} {x : ℚ}
    (h : cellWithin inner outer) (hx : inCell inner x) : inCell outer x :=
  ⟨h.1.trans hx.1, hx.2.trans_le h.2⟩

def refineCell : RegionCell → List CellSplit → RegionCell
  | c, [] => c
  | c, s :: rest => refineCell (childCell c s) rest

theorem finite_refinement_within_parent (c : RegionCell) (path : List CellSplit) :
    cellWithin (refineCell c path) c := by
  induction path generalizing c with
  | nil => exact ⟨le_refl _, le_refl _⟩
  | cons s rest ih => exact cellWithin_trans (ih _) (child_within_parent c s)

theorem refinement_append (c : RegionCell) (a b : List CellSplit) :
    refineCell c (a ++ b) = refineCell (refineCell c a) b := by
  induction a generalizing c with
  | nil => rfl
  | cons s rest ih => exact ih (childCell c s)

theorem separated_cells_disjoint {a b : RegionCell} {x : ℚ}
    (h : cellUpper a ≤ b.lower) : ¬ (inCell a x ∧ inCell b x) := by
  intro hx
  exact (not_lt_of_ge (h.trans hx.2.1)) hx.1.2

theorem shared_seam_owned_by_right {a b : RegionCell}
    (h : cellUpper a = b.lower) :
    ¬ inCell a (cellUpper a) ∧ inCell b (cellUpper a) := by
  constructor
  · simp [inCell]
  · rw [h]
    exact ⟨le_refl _, lt_add_of_pos_right _ b.width_pos⟩

theorem adjacent_children_share_seam (c : RegionCell) (a b : CellSplit)
    (hn : a.radix = b.radix) (hi : a.index.val + 1 = b.index.val) :
    cellUpper (childCell c a) = (childCell c b).lower := by
  have hq : (a.index.val : ℚ) + 1 = b.index.val := by exact_mod_cast hi
  have hrad : (a.radix : ℚ) = b.radix := by exact_mod_cast hn
  dsimp [cellUpper, childCell]
  rw [hrad, ← hq]
  ring

/-- Algebraically equals 2*(x-center)/width in the existing Python chart. -/
def localCoord (c : RegionCell) (x : ℚ) : ℚ := 2 * (x - c.lower) / c.width - 1
def globalCoord (c : RegionCell) (q : ℚ) : ℚ := c.lower + c.width * (q + 1) / 2

theorem chart_roundtrip (c : RegionCell) (x : ℚ) :
    globalCoord c (localCoord c x) = x := by
  dsimp [globalCoord, localCoord]
  field_simp [ne_of_gt c.width_pos]

theorem inverse_chart_roundtrip (c : RegionCell) (q : ℚ) :
    localCoord c (globalCoord c q) = q := by
  dsimp [globalCoord, localCoord]
  field_simp [ne_of_gt c.width_pos]
  ring

theorem cell_membership_iff_local (c : RegionCell) (x : ℚ) :
    inCell c x ↔ -1 ≤ localCoord c x ∧ localCoord c x < 1 := by
  have hlow : -1 ≤ localCoord c x ↔ c.lower ≤ x := by
    unfold localCoord
    rw [le_sub_iff_add_le, show (-1 : ℚ) + 1 = 0 by norm_num, le_div_iff₀ c.width_pos]
    constructor <;> intro h <;> linarith
  have hupp : localCoord c x < 1 ↔ x < cellUpper c := by
    unfold localCoord
    rw [sub_lt_iff_lt_add, div_lt_iff₀ c.width_pos]
    dsimp [cellUpper]
    constructor <;> intro h <;> linarith
  rw [hlow, hupp]
  rfl

/-- Rebase changes a chart, not the represented global point or its permissions. -/
theorem rebase_preserves_global (a b : RegionCell) (q : ℚ) :
    globalCoord b (localCoord b (globalCoord a q)) = globalCoord a q :=
  chart_roundtrip b _

noncomputable section

theorem normalized_weights_sum_one {n : Nat} (w : Fin n → ℝ)
    (h : (∑ i, w i) ≠ 0) : ∑ i, w i / (∑ j, w j) = 1 := by
  simp only [div_eq_mul_inv, ← Finset.sum_mul]
  exact mul_inv_cancel₀ h

theorem normalized_weights_nonnegative {n : Nat} (w : Fin n → ℝ)
    (hw : ∀ i, 0 ≤ w i) (i : Fin n) : 0 ≤ w i / (∑ j, w j) :=
  div_nonneg (hw i) (Finset.sum_nonneg (fun j _ => hw j))

theorem normalized_weighted_energy_bound {n : Nat} (w q : Fin n → ℝ)
    (hw : ∀ i, 0 ≤ w i) (hs : ∑ i, w i = 1)
    (hq : ∀ i, -1 ≤ q i ∧ q i ≤ 1) : weightedEnergy w q ≤ 1 := by
  calc
    weightedEnergy w q ≤ ∑ i, w i := by
      apply Finset.sum_le_sum
      intro i _
      have hsq : (q i) ^ 2 ≤ 1 := by nlinarith [hq i]
      simpa using mul_le_mul_of_nonneg_left hsq (hw i)
    _ = 1 := hs

def localBallPoint {n : Nat} (w q : Fin n → ℝ) : Fin n → ℝ :=
  fun i => (3 / 4 : ℝ) * Real.sqrt (w i) * q i

theorem local_ball_norm_identity {n : Nat} (w q : Fin n → ℝ)
    (hw : ∀ i, 0 ≤ w i) :
    normSq (localBallPoint w q) = (9 / 16 : ℝ) * weightedEnergy w q := by
  unfold normSq weightedEnergy
  rw [Finset.mul_sum]
  apply Finset.sum_congr rfl
  intro i _
  dsimp [localBallPoint]
  rw [mul_pow, mul_pow, Real.sq_sqrt (hw i)]
  ring

theorem local_ball_margin {n : Nat} (w q : Fin n → ℝ)
    (hw : ∀ i, 0 ≤ w i) (hs : ∑ i, w i = 1)
    (hq : ∀ i, -1 ≤ q i ∧ q i ≤ 1) :
    normSq (localBallPoint w q) ≤ 9 / 16 ∧ normSq (localBallPoint w q) < 1 := by
  rw [local_ball_norm_identity w q hw]
  have h := normalized_weighted_energy_bound w q hw hs hq
  constructor <;> linarith

end
end SCBE
