import Mathlib.Data.List.Basic

namespace SCBE

/-- An immutable, named directed policy. Geometry is not an authority field. -/
structure Policy (α : Type) where
  ready : Bool
  known : α → Bool
  edge : α → α → Bool

def permits {α : Type} (p : Policy α) (a b : α) : Bool :=
  p.ready && p.known a && p.known b && p.edge a b

theorem permits_iff {α : Type} (p : Policy α) (a b : α) :
    permits p a b = true ↔
      p.ready = true ∧ p.known a = true ∧ p.known b = true ∧ p.edge a b = true := by
  simp [permits, and_assoc]

theorem permitted_edge {α : Type} {p : Policy α} {a b : α}
    (h : permits p a b = true) : p.edge a b = true := (permits_iff p a b).mp h |>.2.2.2

def walk {α : Type} (p : Policy α) : α → List α → Bool
  | _, [] => true
  | a, b :: rest => permits p a b && walk p b rest

def LegalWalk {α : Type} (p : Policy α) : α → List α → Prop
  | _, [] => True
  | a, b :: rest => p.edge a b = true ∧ LegalWalk p b rest

theorem walk_only_directed_edges {α : Type} (p : Policy α) (a : α) (xs : List α)
    (h : walk p a xs = true) : LegalWalk p a xs := by
  induction xs generalizing a with
  | nil => trivial
  | cons b rest ih =>
    have hh : permits p a b = true ∧ walk p b rest = true := by simpa [walk] using h
    exact ⟨permitted_edge hh.1, ih b hh.2⟩

def execute {α : Type} (p : Policy α) : Nat → α → List α → List α
  | 0, _, _ => []
  | _ + 1, _, [] => []
  | fuel + 1, a, b :: rest =>
    if permits p a b then b :: execute p fuel b rest else []

theorem execution_fuel_bound {α : Type} (p : Policy α) (fuel : Nat) (a : α) (xs : List α) :
    (execute p fuel a xs).length ≤ fuel := by
  induction fuel generalizing a xs with
  | zero => simp [execute]
  | succ fuel ih =>
    cases xs with
    | nil => simp [execute]
    | cons b rest =>
      simp only [execute]
      split
      · simpa using Nat.succ_le_succ (ih b rest)
      · simp

theorem execution_legal {α : Type} (p : Policy α) (fuel : Nat) (a : α) (xs : List α) :
    LegalWalk p a (execute p fuel a xs) := by
  induction fuel generalizing a xs with
  | zero => trivial
  | succ fuel ih =>
    cases xs with
    | nil => trivial
    | cons b rest =>
      simp only [execute]
      split
      next h => exact ⟨permitted_edge h, ih b rest⟩
      next => trivial

def forwardChain : Policy Nat := ⟨true, fun n => n < 3, fun a b => b == a + 1⟩

/-- The reverse transition is denied even when its endpoints are both known. -/
theorem reverse_edge_denied : permits forwardChain 1 0 = false := by decide

theorem known_destination_is_insufficient :
    forwardChain.known 0 = true ∧ permits forwardChain 1 0 = false := by decide

/-- Any symmetric gate that accepts a one-way edge also accepts its illegal reverse. -/
theorem symmetric_gate_cannot_enforce_direction {α : Type} (g : α → α → Bool)
    (symmetric : ∀ a b, g a b = g b a) (a b : α) (h : g a b = true) :
    g b a = true := by rw [← symmetric a b]; exact h

end SCBE
