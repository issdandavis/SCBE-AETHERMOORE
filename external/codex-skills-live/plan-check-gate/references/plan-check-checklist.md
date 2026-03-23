# Plan Check Checklist

Use this checklist before writing code.

## 1) Scope
- What is the exact problem?
- What must remain unchanged?
- What is out of scope?

## 2) Facts vs Assumptions
- List verified facts with source links.
- List assumptions separately.
- Remove assumptions that can be verified quickly.

## 3) Research Quality
- Prefer primary sources (official docs/specs/repos/papers).
- Add publication/update dates for time-sensitive claims.
- Flag uncertain claims explicitly.

## 4) Plan Quality
- Small reversible steps.
- Clear test points after each step.
- Failure/rollback path exists.

## 5) Approval Gate
- Return `decision: hold` until user confirms.
- Start coding only after explicit go/no-go.

## Prompt Snippets
- "Run plan-check gate before coding."
- "List verified facts + assumptions first."
- "Give me source-backed plan, then wait for approval."
