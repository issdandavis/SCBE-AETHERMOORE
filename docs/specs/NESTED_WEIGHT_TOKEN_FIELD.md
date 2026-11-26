# Nested Weight–Token Field

**Status:** executable reference geometry; cryptographic use is context binding only.
**Runtime:** `python/scbe/nested_weight_token_field.py`
**Tests:** `tests/tokenizer/test_nested_weight_token_field.py`

## The idea in plain language

Ten squares live inside one another in the same field. A seed identifies the
field. A complete token path supplies signed weights and coordinates. Each
layer receives a raw growth contribution, those contributions are combined and
raised to a declared power, and one bounded multiplier grows every layer. The
same multiplier preserves the ratio between every pair of squares.

The path also defines a local tangent. That tangent is the stack's local
z-axis. The squares rotate together in the plane perpendicular to it. The key
region is placed a declared distance behind the observed path in that tangent
chart. “Behind” is an address relation, not invisibility.

This creates the pocket only when the weighted path is supplied. The seed does
not have to predict every future point.

## Existing pieces this joins

- `python/scbe/token_tree_wafer_growth.py` already measures an ordered,
  full-decoded-byte token-path signal and changes the probability field without
  changing token or byte identity.
- `C:\dev\clay-wafer-net\clay_wafer_net\wafer_6d_quine.py` already supplies
  the contracting/rotating quine wafer used by that experiment.
- `docs/specs/MECHANICAL_LAYER_TANGENTIAL_TREE.md` already defines direction as
  an original token plus applied weights and local manifold state, then treats
  accumulated layer rotation as holonomy.
- `POCKET_WEIGHTSPACE.md` in the Clay training worktrees already defines a
  pocket as a bounded weight region with local training dynamics, a trace, and
  an exit/checkpoint rule.

The missing item was a small operator making those relations executable in one
replayable field.

## Reference equations

For `n` layers, base side `s0`, and nesting ratio `q`:

```text
g_i = E_path q^i
G   = (sum_i(g_i) / n)^p
rho = exp(gain * tanh(G))
s_i = s0 q^i rho
```

Therefore:

```text
s_(i+1) / s_i = q
```

for every adjacent pair. `tanh` bounds the common multiplier by
`exp(growth_gain)`, preventing an extreme token weight from exploding the
field.

Path energy combines RMS token-weight magnitude with weighted segment length.
The weight sign controls the directional moment and rotation; weight magnitude
controls growth. This keeps a negative or refuting token meaningful without
allowing it to create a negative square size.

That makes the interaction explicit instead of blending unlike jobs together:

- token order and coordinates define path topology and its tangent;
- absolute weight defines the local metric/dilation; and
- signed weight defines orientation within the tangent plane.

Each layer emits a 4×4 homogeneous matrix whose first two columns span the
rotated square, whose third column is the unit path tangent, and whose final
column is the key anchor. The inverse audit projects a world point back onto
those three axes.

## What is invariant

1. Token order and token IDs are retained in the receipt.
2. Replaying the same seed, path, and spec yields the same receipt.
3. All nesting ratios remain fixed under common growth.
4. Every square vertex round-trips through its matrix frame.
5. The local z-axis is the path tangent.
6. A weight, coordinate, token order, seed, or spec change changes the receipt.
7. Inputs that are empty, non-finite, directionless, or weightless fail closed.
8. The returned field contains its complete spec and can recompute its receipt.

## Security boundary

This is a representation and addressing primitive. It is not a key derivation
function, cipher, signature scheme, or source of entropy. Time, lore, token
weights, path distortion, and the seed label may all be observable or guessed.

For an agentic owner-key system:

- generate each operational key with an operating-system CSPRNG when the next
  pocket is actually created;
- sign the field receipt and the new public key with the currently authorized
  key before erasing that old private key;
- keep the stable owner root offline and use it only to authorize or recover a
  lineage;
- maintain an append-only spent-key/transition ledger so restoring an old local
  state cannot silently reuse a disposable key; and
- use an established authenticated key-exchange protocol for encryption. Do
  not turn this geometry into a home-grown key exchange.

The geometry answers *where this key/use lives and what path formed it*. The
cryptographic primitive answers *who authorized it*.

## Current measured boundary

The existing token-tree wafer receipt reports 64/64 requested trees distinct,
exact identity preservation per generation, no coordinate collisions in the
reported slice, and passing quine probes. It also explicitly reports no neural
training or model-quality gain. This new operator has deterministic unit tests;
it does not yet have a controlled neural benchmark or a production key-lineage
integration.
