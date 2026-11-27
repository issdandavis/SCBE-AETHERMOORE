import SCBE.Geometry
import Mathlib.Data.List.Basic
import Mathlib.Data.Nat.Basic
import Mathlib.Tactic.Positivity
import Mathlib.Tactic.Ring

namespace SCBE

/-- A non-negative, integer representation of one weighted token contribution.

This is the quantized hardware model. The floating-point path geometry keeps
signed weights separately; its growth term uses their magnitudes.
-/
structure QuantizedWeightedToken where
  tokenValue : Nat
  weightMagnitude : Nat
  deriving DecidableEq, Repr

def QuantizedWeightedToken.contribution (token : QuantizedWeightedToken) : Nat :=
  token.weightMagnitude * token.tokenValue

/-- Exact natural-number reference sum for a sequence of weighted tokens. -/
def naturalWeightedSum (tokens : List QuantizedWeightedToken) : Nat :=
  (tokens.map QuantizedWeightedToken.contribution).sum

/-- Independent blocks combine to the same exact natural-number result. -/
theorem naturalWeightedSum_append (left right : List QuantizedWeightedToken) :
    naturalWeightedSum (left ++ right) =
      naturalWeightedSum left + naturalWeightedSum right := by
  simp [naturalWeightedSum]

/-- Any finite chunking of a token sequence preserves the exact total. -/
theorem naturalWeightedSum_chunks (chunks : List (List QuantizedWeightedToken)) :
    naturalWeightedSum chunks.flatten =
      (chunks.map naturalWeightedSum).sum := by
  induction chunks with
  | nil => rfl
  | cons head tail ih =>
      simp [naturalWeightedSum_append, ih]

/-- The modulus of an unsigned fixed-width word. -/
def wordModulus (width : Nat) : Nat := 2 ^ width

theorem wordModulus_positive (width : Nat) : 0 < wordModulus width := by
  simp [wordModulus]

/-- Hardware accumulation modeled as unsigned fixed-width wraparound. -/
def hardwareWeightedSum (width : Nat) (tokens : List QuantizedWeightedToken) : Nat :=
  naturalWeightedSum tokens % wordModulus width

theorem hardwareWeightedSum_spec (width : Nat) (tokens : List QuantizedWeightedToken) :
    hardwareWeightedSum width tokens =
      naturalWeightedSum tokens % wordModulus width := rfl

/-- Chunk results may be reduced modulo the word size before they are combined. -/
theorem hardwareWeightedSum_append
    (width : Nat) (left right : List QuantizedWeightedToken) :
    hardwareWeightedSum width (left ++ right) =
      (hardwareWeightedSum width left + hardwareWeightedSum width right) %
        wordModulus width := by
  simp [hardwareWeightedSum, naturalWeightedSum_append, Nat.add_mod]

/-- Fixed-width hardware refines the natural-number model when no wrap occurs. -/
theorem hardware_exact_of_noOverflow
    (width : Nat) (tokens : List QuantizedWeightedToken)
    (h : naturalWeightedSum tokens < wordModulus width) :
    hardwareWeightedSum width tokens = naturalWeightedSum tokens := by
  exact Nat.mod_eq_of_lt h

theorem hardwareWeightedSum_lt_modulus
    (width : Nat) (tokens : List QuantizedWeightedToken) :
    hardwareWeightedSum width tokens < wordModulus width := by
  exact Nat.mod_lt _ (wordModulus_positive width)

/-- A concrete witness that hardware and natural arithmetic diverge on overflow. -/
theorem eightBit_wrap_example :
    hardwareWeightedSum 8 [{ tokenValue := 200, weightMagnitude := 2 }] = 144 ∧
      naturalWeightedSum [{ tokenValue := 200, weightMagnitude := 2 }] = 400 := by
  decide

/-- Exact side length for one layer of the nested weight-token field.

`common` abstracts the bounded exponential growth term. The ratio theorem below
therefore applies to any common multiplier, independently of how it is computed.
-/
def nestedSide (base ratio common : ℝ) (index : Nat) : ℝ :=
  base * ratio ^ index * common

/-- Common growth preserves the declared ratio between adjacent layers. -/
theorem nestedSide_succ (base ratio common : ℝ) (index : Nat) :
    nestedSide base ratio common (index + 1) =
      ratio * nestedSide base ratio common index := by
  simp [nestedSide, pow_succ]
  ring

theorem nestedSide_positive
    {base ratio common : ℝ}
    (hbase : 0 < base) (hratio : 0 < ratio) (hcommon : 0 < common)
    (index : Nat) :
    0 < nestedSide base ratio common index := by
  exact mul_pos (mul_pos hbase (pow_pos hratio index)) hcommon

end SCBE
