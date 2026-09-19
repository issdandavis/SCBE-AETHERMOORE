import SCBE.Codecs
import SCBE.RestrictedExecution

namespace SCBE

/-- Renaming transports the entire policy; it cannot create new permissions. -/
def relabelPolicy {α β : Type} (p : Policy α) (e : α ≃ β) : Policy β where
  ready := p.ready
  known := fun b => p.known (e.symm b)
  edge := fun a b => p.edge (e.symm a) (e.symm b)

theorem relabel_preserves_permits {α β : Type} (p : Policy α) (e : α ≃ β) (a b : α) :
    permits (relabelPolicy p e) (e a) (e b) = permits p a b := by
  simp [permits, relabelPolicy]

theorem relabel_preserves_walk {α β : Type} (p : Policy α) (e : α ≃ β)
    (a : α) (xs : List α) : walk (relabelPolicy p e) (e a) (xs.map e) = walk p a xs := by
  induction xs generalizing a with
  | nil => rfl
  | cons b rest ih => simp [walk, relabel_preserves_permits, ih]

theorem relabel_preserves_execution {α β : Type} (p : Policy α) (e : α ≃ β)
    (fuel : Nat) (a : α) (xs : List α) :
    execute (relabelPolicy p e) fuel (e a) (xs.map e) = (execute p fuel a xs).map e := by
  induction fuel generalizing a xs with
  | zero => rfl
  | succ fuel ih =>
    cases xs with
    | nil => rfl
    | cons b rest =>
      simp only [List.map_cons, execute, relabel_preserves_permits]
      split <;> simp [ih]

theorem relabel_preserves_dispatch {α β : Type} (p : Policy α) (e : α ≃ β)
    (a b : α) (c : WorkcellControl) (inspection : Bool) (checks : CallEvidence) :
    dispatchAllowed (relabelPolicy p e) (e a) (e b) c inspection checks =
    dispatchAllowed p a b c inspection checks := by
  simp [dispatchAllowed, relabel_preserves_permits]

theorem six_tongue_dispatch_invariant {Token : Tongue → Type}
    (codecs : TongueCodecs Token) (t : Tongue) (p : Policy ByteSymbol)
    (a b : ByteSymbol) (c : WorkcellControl) (inspection : Bool) (checks : CallEvidence) :
    dispatchAllowed (relabelPolicy p (codecs t)) (codecs t a) (codecs t b) c inspection checks =
    dispatchAllowed p a b c inspection checks :=
  relabel_preserves_dispatch p (codecs t) a b c inspection checks

theorem codec_chunk_composition {Token : Tongue → Type} (codecs : TongueCodecs Token)
    (t : Tongue) (a b : List ByteSymbol) :
    encode codecs t (a ++ b) = encode codecs t a ++ encode codecs t b := by
  simp [encode]

theorem codec_no_sequence_alias {Token : Tongue → Type} (codecs : TongueCodecs Token)
    (t : Tongue) {a b : List ByteSymbol} (h : encode codecs t a = encode codecs t b) : a = b := by
  have hd := congrArg (decode codecs t) h
  simpa [codec_roundtrip] using hd

end SCBE
