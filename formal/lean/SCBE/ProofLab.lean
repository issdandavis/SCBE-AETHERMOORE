import SCBE.Composition
import SCBE.Geometry

/-!
# SCBE proof lab

Small, readable examples for following a claim from its exact statement through
the proof term that Lean's kernel checks. These examples reuse the production
definitions; they do not introduce a second model of the system.
-/
namespace SCBE.ProofLab

/-- If DENY is one of the checks, their aggregate cannot be ALLOW. -/
theorem deny_member_blocks_allow (checks : List SCBE.Decision)
    (hdeny : SCBE.Decision.deny ∈ checks) : SCBE.aggregate checks ≠ .allow := by
  intro hallow
  have every_check_allows := (SCBE.aggregate_allow_iff checks).mp hallow
  have deny_allows := every_check_allows .deny hdeny
  cases deny_allows

/-- With two checks, aggregate ALLOW exposes both individual obligations. -/
theorem two_checks_allow_requires_each (left right : SCBE.Decision)
    (hallow : SCBE.aggregate [left, right] = .allow) :
    left = .allow ∧ right = .allow := by
  simpa using (SCBE.aggregate_allow_iff [left, right]).mp hallow

/-- The bounded safety score is exactly one at zero distance and zero phase. -/
theorem safety_score_at_origin : SCBE.safetyScore 0 0 = 1 := by
  simp [SCBE.safetyScore]

#check deny_member_blocks_allow
#check two_checks_allow_requires_each
#check safety_score_at_origin

#print deny_member_blocks_allow
#print axioms deny_member_blocks_allow

/- Uncommenting this example makes Lean reject the file:

example : SCBE.combine .deny .allow = .allow := by decide
-/

end SCBE.ProofLab
