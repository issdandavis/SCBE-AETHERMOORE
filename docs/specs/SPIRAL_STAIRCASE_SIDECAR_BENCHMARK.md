# Decoupled spiral staircase benchmark

Status: registered after the coupled benchmark exposed a state/stack collision
and before this repair's full matrix was run.

## Repair under test

The coupled recurrent cell had to represent the current value, the ordered door
stack, the event, and the routing coordinate in one hidden vector. It fit initial
byte identity but did not fit even the seen-depth route strongly enough to make
deep evaluation diagnostic.

This repair separates two trainable rails:

- **state rail:** current value plus an action embedding, trained exhaustively on
  all 64 states and all eight reversible actions;
- **stack rail:** OPEN/CLOSE, action or missing receipt, realm, and schedule,
  trained to name the inverse action required by each CLOSE.

With an exact receipt, state-route loss has no gradient path into the stack rail.
Without a receipt, the stack head's soft action selects the state transition, so
the model must learn LIFO recall. This wiring is checked in preflight.

## Controls and gates

The seven arms keep identical trainable parameters. Phi schedule controls are
tested on the no-receipt path, where landing coordinates can actually affect
stack recall. Codec controls stay on the receipt path, where stack uncertainty
cannot hide an input-representation result.

The same three-seed, all-positive, greater-than-two-pooled-SD claim rule applies.
Training uses nesting depths 1..4; evaluation uses 1..12. Absolute support needs
at least 0.90 deep route floor and 0.70 deep full-route exact in every aligned
receipt seed.
