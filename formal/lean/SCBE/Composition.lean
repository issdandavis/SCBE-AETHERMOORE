import SCBE.Routing

namespace SCBE

/-- Restriction order; REVIEW is normalized to QUARANTINE at this boundary. -/
inductive Decision where
  | allow | quarantine | deny | snap
  deriving DecidableEq, Repr

def Decision.rank : Decision → Nat
  | .allow => 0 | .quarantine => 1 | .deny => 2 | .snap => 3

def combine (a b : Decision) : Decision := if a.rank ≤ b.rank then b else a

theorem combine_preserves_left (a b : Decision) : a.rank ≤ (combine a b).rank := by
  cases a <;> cases b <;> decide

theorem combine_preserves_right (a b : Decision) : b.rank ≤ (combine a b).rank := by
  cases a <;> cases b <;> decide

theorem combine_associative (a b c : Decision) :
    combine (combine a b) c = combine a (combine b c) := by
  cases a <;> cases b <;> cases c <;> decide

theorem combine_commutative (a b : Decision) : combine a b = combine b a := by
  cases a <;> cases b <;> decide

theorem combine_allow_iff (a b : Decision) :
    combine a b = .allow ↔ a = .allow ∧ b = .allow := by
  cases a <;> cases b <;> simp [combine, Decision.rank]

def aggregate : List Decision → Decision
  | [] => .allow
  | d :: rest => combine d (aggregate rest)

theorem aggregate_allow_iff (ds : List Decision) :
    aggregate ds = .allow ↔ ∀ d ∈ ds, d = .allow := by
  induction ds with
  | nil => simp [aggregate]
  | cons d rest ih => simp [aggregate, combine_allow_iff, ih]

theorem aggregate_never_weakens (ds : List Decision) (d : Decision) (hd : d ∈ ds) :
    d.rank ≤ (aggregate ds).rank := by
  induction ds with
  | nil => simp at hd
  | cons a rest ih =>
    rcases List.mem_cons.mp hd with h | h
    · subst d; exact combine_preserves_left _ _
    · exact le_trans (ih h) (combine_preserves_right _ _)

/-- The generic result specializes to all fourteen layers without changing the law. -/
theorem fourteen_layer_veto (layers : Fin 14 → Decision) (i : Fin 14) :
    (layers i).rank ≤ (aggregate (List.ofFn layers)).rank := by
  apply aggregate_never_weakens
  exact List.mem_ofFn.mpr ⟨i, rfl⟩

def admitReference {α : Type} (d : Decision) (old candidate : α) : α :=
  if d = .allow then candidate else old

theorem refused_reference_unchanged {α : Type} (d : Decision) (old candidate : α)
    (h : d ≠ .allow) : admitReference d old candidate = old := by
  simp [admitReference, h]

def authorizedStep {α : Type} (p : Policy α) (a b : α) (checks : List Decision) : Bool :=
  permits p a b && decide (aggregate checks = .allow)

theorem authorizedStep_contract {α : Type} {p : Policy α} {a b : α} {ds : List Decision}
    (h : authorizedStep p a b ds = true) :
    p.edge a b = true ∧ (∀ d ∈ ds, d = .allow) := by
  have hh : permits p a b = true ∧ aggregate ds = .allow := by
    simpa [authorizedStep] using h
  exact ⟨permitted_edge hh.1, (aggregate_allow_iff ds).mp hh.2⟩

end SCBE
