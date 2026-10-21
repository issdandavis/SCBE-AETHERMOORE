# Lattice-snap spiral staircase benchmark

Status: registered after the decoupled first seed reached perfect one-step
accuracy but accumulated off-node error at long depth, and before this repair's
full matrix was run.

## Repair under test

The decoupled state rail learned every individual reversible operation, but its
continuous state moved farther from the 64 valid token nodes with each repeated
operation. This repair keeps the learned proposal and adds one operation:

1. propose the next continuous state;
2. score all 64 conserved token prototypes;
3. select the closest node in the forward pass;
4. use the soft score gradient in the backward pass.

This is a straight-through discrete projection. It is the mathematical version
of a fixed switch state: motion is learned, while each completed step lands on a
valid token node before another realm can act. The stack/receipt rail remains
separate and all controls retain identical parameters.

The same arms, depths, three seeds, two-pooled-SD rules, and absolute thresholds
from the decoupled benchmark apply. A preflight check requires every captured
forward state to equal one of the current 64 prototypes while a nonzero soft
gradient still reaches the transition proposal.
