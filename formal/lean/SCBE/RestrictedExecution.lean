import SCBE.Routing

namespace SCBE

/-- DCP workcell profile, deliberately separate from the L13 SNAP profile. -/
inductive WorkcellControl where
  | allow | quarantine | escalate | deny
  deriving DecidableEq, Repr

def scopeAllows (control : WorkcellControl) (inspection : Bool) : Bool :=
  match control with
  | .allow => true
  | .quarantine => inspection
  | .escalate | .deny => false

/-- Host-computed evidence. These fields are not assertions accepted from a caller. -/
structure CallEvidence where
  bindingCurrent : Bool
  argumentsValid : Bool
  codecValid : Bool
  toolGateAllows : Bool

def callChecks (e : CallEvidence) : Bool :=
  e.bindingCurrent && e.argumentsValid && e.codecValid && e.toolGateAllows

def dispatchAllowed {α : Type} (p : Policy α) (a b : α)
    (control : WorkcellControl) (inspection : Bool) (e : CallEvidence) : Bool :=
  permits p a b && scopeAllows control inspection && callChecks e

theorem dispatch_contract {α : Type} (p : Policy α) (a b : α)
    (control : WorkcellControl) (inspection : Bool) (e : CallEvidence) :
    dispatchAllowed p a b control inspection e = true ↔
    permits p a b = true ∧ scopeAllows control inspection = true ∧
    e.bindingCurrent = true ∧ e.argumentsValid = true ∧
    e.codecValid = true ∧ e.toolGateAllows = true := by
  simp [dispatchAllowed, callChecks, and_assoc]

theorem dispatch_requires_directed_edge {α : Type} {p : Policy α} {a b : α}
    {control : WorkcellControl} {inspection : Bool} {e : CallEvidence}
    (h : dispatchAllowed p a b control inspection e = true) : p.edge a b = true :=
  permitted_edge ((dispatch_contract p a b control inspection e).mp h).1

theorem quarantine_requires_inspection {α : Type} {p : Policy α} {a b : α}
    {inspection : Bool} {e : CallEvidence}
    (h : dispatchAllowed p a b .quarantine inspection e = true) : inspection = true :=
  ((dispatch_contract p a b .quarantine inspection e).mp h).2.1

theorem quarantine_blocks_unscoped {α : Type} (p : Policy α) (a b : α) (e : CallEvidence) :
    dispatchAllowed p a b .quarantine false e = false := by
  simp [dispatchAllowed, scopeAllows]

theorem deny_blocks_dispatch {α : Type} (p : Policy α) (a b : α) (i : Bool) (e : CallEvidence) :
    dispatchAllowed p a b .deny i e = false := by simp [dispatchAllowed, scopeAllows]

theorem escalate_requires_review {α : Type} (p : Policy α) (a b : α) (i : Bool) (e : CallEvidence) :
    dispatchAllowed p a b .escalate i e = false := by simp [dispatchAllowed, scopeAllows]

theorem quarantine_is_scope_reduction {α : Type} {p : Policy α} {a b : α}
    {i : Bool} {e : CallEvidence} (h : dispatchAllowed p a b .quarantine i e = true) :
    dispatchAllowed p a b .allow i e = true := by
  simp only [dispatchAllowed, Bool.and_eq_true] at *
  exact ⟨⟨h.1.1, rfl⟩, h.2⟩

theorem stale_binding_blocks_dispatch {α : Type} (p : Policy α) (a b : α)
    (c : WorkcellControl) (i : Bool) (e : CallEvidence) (h : e.bindingCurrent = false) :
    dispatchAllowed p a b c i e = false := by simp [dispatchAllowed, callChecks, h]

/-- Pure result model: invokes the supplied handler only on the checked branch. -/
def checkedCall {α β : Type} (p : Policy α) (a b : α)
    (c : WorkcellControl) (i : Bool) (e : CallEvidence) (handler : Unit → β) :
    WorkcellControl × Option β :=
  (c, if dispatchAllowed p a b c i e then some (handler ()) else none)

theorem checked_call_preserves_control {α β : Type} (p : Policy α) (a b : α)
    (c : WorkcellControl) (i : Bool) (e : CallEvidence) (handler : Unit → β) :
    (checkedCall p a b c i e handler).1 = c := rfl

theorem quarantine_returns_tool_result {α β : Type} (p : Policy α) (a b : α)
    (e : CallEvidence) (handler : Unit → β)
    (route : permits p a b = true) (checks : callChecks e = true) :
    checkedCall p a b .quarantine true e handler = (.quarantine, some (handler ())) := by
  simp [checkedCall, dispatchAllowed, scopeAllows, route, checks]

theorem blocked_call_has_no_result {α β : Type} (p : Policy α) (a b : α)
    (c : WorkcellControl) (i : Bool) (e : CallEvidence) (handler : Unit → β)
    (h : dispatchAllowed p a b c i e = false) :
    checkedCall p a b c i e handler = (c, none) := by simp [checkedCall, h]

/-- A total pure handler and satisfied checks provide a constructive progress witness. -/
theorem quarantine_progress_example :
    checkedCall forwardChain 0 1 .quarantine true ⟨true, true, true, true⟩
      (fun _ => (6 : Nat)) = (.quarantine, some 6) := by decide

end SCBE
