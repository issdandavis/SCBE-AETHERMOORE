"""opcode_vectors.py -- the VECTOR + STRAND layer over the six-tongue opcode set (Issac, 2026-07-18:
"do we have custom vector arrays aligned to my 6 opcode sets from my tokenizer that we can then
make custom context strands for underlying relationships for new information uptake?").

WHAT THIS CONNECTS (it builds nothing new; it assembles what already exists):
  * tongue_semantics -- 128 opcodes, each a realm + a meaning gloss + a skeleton + 6 tongue words.
  * node_catalog     -- each opcode as a typed node (input/output ports) + the edge-legality rule.
This module turns that symbolic substrate into (1) a real VECTOR per opcode, aligned so row i is
the SAME instruction all six tongues name, and (2) three kinds of relationship STRAND over them,
and (3) an UPTAKE hook that places a brand-new op into the space and wires its strands.

HONEST FIREWALL (structural, not learned): the vectors are DETERMINISTIC features derived from the
opcode's realm / port-types / edge-legality -- they are NOT embeddings trained on a corpus, and this
module does NOT do gradient learning. The strands are TYPE-LEGAL composition + realm/meaning cognates,
COMPUTED, not inferred from data. This is the addressable substrate a learned layer would sit ON:
"aligned vector arrays + relationship strands" is real; "learned from new information" is the next
layer and is explicitly not claimed here. The proof it is meaningful: a NEW op lands (by cosine) next
to its own realm's ops, with zero training -- structure alone carries the relationship. designed !=
discovered; addresses != learns.
"""
from __future__ import annotations
import sys
from dataclasses import dataclass

sys.path.insert(0, r"C:/dev/loom")
sys.path.insert(0, r"C:/dev")
import numpy as np
import tongue_semantics as TS
import node_catalog as NC

# ---- the type vocabulary (ports). node_catalog knows N/B/L/F for the scalar machine; the array
# realms (4-A) transform GRIDS, so we add G. G accepts G, and the scalar accept-rule is reused. ----
TVOCAB = ("N", "B", "L", "F", "G")
_TIDX = {t: i for i, t in enumerate(TVOCAB)}
REALM_ORDER = sorted(TS.REALM)               # 0..10, stable
_RIDX = {r: i for i, r in enumerate(REALM_ORDER)}


def _accepts(out_t: str, in_t: str) -> bool:
    """Can an output port of type out_t feed an input port of type in_t? Reuse node_catalog's rule
    for the scalar types; grids only feed grids."""
    if in_t == "G" or out_t == "G":
        return in_t == "G" and out_t == "G"
    return NC.edge_ok(out_t, in_t)


@dataclass(frozen=True)
class Op:
    """One opcode, fully addressed: byte, realm, meaning, ports, and its word in all six tongues."""
    byte: int
    gloss: str                    # tongue-independent meaning, e.g. 'judge.bind'
    realm: int                    # high nibble
    inputs: tuple                 # port types
    outputs: tuple
    tongues: dict                 # {'KO': "ael'baenaed", ...} -- the 6 opcode-set surfaces


def _all_ops() -> dict:
    """Every opcode as an Op, aligned across all six tongues. Scalar ops (realms 0-3) get exact
    ports from node_catalog; array ops (4-A) are grid->grid (their structural signature)."""
    try:
        _, ca_word, _ = TS._scbe()
    except Exception:
        ca_word = None
    byte_to_scalar = {n.byte: n for n in NC.CATALOG.values()}
    ops = {}
    for byte in sorted(TS.OP_GLOSS):
        realm = byte >> 4
        tongues = {}
        for code in TS.ORDER:                        # KO AV RU CA UM DR
            try:
                tongues[code] = TS.render(code, byte, ca_word)
            except Exception:
                tongues[code] = ""
        if byte in byte_to_scalar:                   # exact typed ports from the garage
            nd = byte_to_scalar[byte]
            ins, outs = nd.inputs, nd.outputs
        elif byte in TS.FORM_BIND:                    # array realm: transforms a grid
            ins, outs = ("G",), ("G",)
        else:
            ins, outs = ("N",), ("N",)               # fallback (shouldn't happen for bound ops)
        ops[byte] = Op(byte, TS.gloss(byte), realm, tuple(ins), tuple(outs), tongues)
    return ops


def vector(op: Op) -> np.ndarray:
    """The deterministic STRUCTURAL vector for an opcode. Every component is grounded in the op's
    own realm / ports / executability -- nothing hand-tuned, nothing learned."""
    v = []
    # realm one-hot (11): which KIND of thought
    oh = [0.0] * len(REALM_ORDER); oh[_RIDX[op.realm]] = 1.0; v += oh
    v.append((op.byte & 0xF) / 15.0)                 # low-nibble position in its realm
    v.append(1.0 if op.realm >= 4 else 0.0)          # array machine vs scalar machine
    v.append(1.0 if op.byte in TS.FORM_BIND else 0.0)  # does it execute on a grid
    v.append(len(op.inputs) / 3.0)                   # input arity
    v.append(len(op.outputs) / 2.0)                  # output arity
    it = [0.0] * len(TVOCAB)                          # input port types (multi-hot)
    for t in op.inputs:
        it[_TIDX[t]] += 1.0
    v += [x / max(1.0, len(op.inputs)) for x in it]
    ot = [0.0] * len(TVOCAB)                          # output port types (multi-hot)
    for t in op.outputs:
        ot[_TIDX[t]] += 1.0
    v += [x / max(1.0, len(op.outputs)) for x in ot]
    return np.asarray(v, dtype=np.float32)


def build_matrix(ops: dict):
    """The VECTOR ARRAY aligned to the six opcode sets: row i == byte order[i] == the one thing all
    six tongues name. Returns (order, matrix[n,d], {byte: row})."""
    order = sorted(ops)
    M = np.stack([vector(ops[b]) for b in order])
    return order, M, {b: i for i, b in enumerate(order)}


def canonical_substrate() -> tuple[tuple[int, ...], np.ndarray]:
    """Return the one frozen opcode-byte order and its structural features.

    Learned Clay components should consume this function instead of creating
    independent opcode anchors.  The returned matrix is a copy so a caller
    cannot mutate this module's canonical structural view by accident.
    """

    order, matrix, _ = build_matrix(_all_ops())
    if len(order) != 128 or matrix.shape != (128, 26):
        raise RuntimeError(f"canonical opcode contract changed: {len(order)=}, {matrix.shape=}")
    if len(set(order)) != len(order):
        raise RuntimeError("canonical opcode byte order contains duplicates")
    return tuple(order), matrix.copy()


# ---- CONTEXT STRANDS: the underlying relationships, three kinds -----------------------------------
def strands(ops: dict) -> dict:
    """Three relationship strands over the opcode set:
      compose -- A -> {B : A's output can legally feed one of B's inputs}   (the wiring relationship)
      realm   -- A -> {B : same realm}                                      (cognates by kind)
      meaning -- A -> {B : same verb across realms, e.g. join@0x00 & join@0xA5}  (semantic echo)"""
    verbs = {b: ops[b].gloss.split(".", 1)[1] for b in ops}
    compose, realm, meaning = {}, {}, {}
    for a in ops:
        oa = ops[a]
        compose[a] = sorted(
            b for b in ops if b != a
            and any(_accepts(ot, it) for ot in oa.outputs for it in ops[b].inputs))
        realm[a] = sorted(b for b in ops if b != a and ops[b].realm == oa.realm)
        meaning[a] = sorted(b for b in ops if b != a and verbs[b] == verbs[a])
    return {"compose": compose, "realm": realm, "meaning": meaning}


# ---- CONTEXT MESH: one neutral base per opcode + per-field weight layers that BALANCE to neutral --
# Named views into the base vector so the per-context masks are principled, not arbitrary indices.
_D_REALM = slice(0, 11)   # realm one-hot          -- the MEANING facet (what KIND of thought)
_I_LO = 11                # position within realm  -- the transmitted SYMBOL
_I_ARR = 12               # array vs scalar
_I_EXEC = 13              # executes on a grid
_S_PORTS = slice(14, 26)  # arity + port types     -- the OPERATION facet
CONTEXTS = ("code", "speak", "comms", "data")


def context_masks(dim: int) -> dict:
    """Per-field weight layers over the base dims. Each field up-weights the facet it actually reads:
    code -> ports/exec (the operation), speak -> realm-meaning (the thought), comms/audio -> the
    transmitted symbol (low nibble), data -> structure. The masks are then MEAN-CENTERED so their
    average across the four fields is 1.0 in every dim -- the fields BALANCE to the neutral base, and
    each context is a dynamic delta off it (Issac: 'balance out to a neutral start but a dynamic inner
    reality difference'). FIREWALL: the facet groupings are DESIGNED (grounded in what each domain
    reads), not learned; a cross-training loop over real usage would REPLACE these seed masks. This is
    the balanced, addressable scaffold that learning sits on -- not the learned result."""
    w = {c: np.ones(dim, np.float32) for c in CONTEXTS}
    w["code"][_S_PORTS] *= 1.8;  w["code"][_I_EXEC] *= 1.8;  w["code"][_I_ARR] *= 1.4
    w["speak"][_D_REALM] *= 1.8; w["speak"][_I_LO] *= 1.4
    w["comms"][_D_REALM] *= 1.3; w["comms"][_I_LO] *= 1.8       # audio-over-air: the symbol carries
    w["data"][_S_PORTS] *= 1.4;  w["data"][_I_ARR] *= 1.8
    mean = np.stack([w[c] for c in CONTEXTS]).mean(0) + 1e-9
    for c in CONTEXTS:                                          # renormalize: mean_context == 1 per dim
        w[c] = w[c] / mean
    return w


def context_mesh(ops: dict):
    """The neural-mesh tensor [n_ops, n_contexts, dim]: the SAME reused token seen from four fields.
    The mean over the four contexts == the neutral base (verified), so one substrate carries a bundle
    of related meanings that differ by field. Returns (order, base, mesh, masks)."""
    order, base, _ = build_matrix(ops)
    w = context_masks(base.shape[1])
    mesh = np.stack([np.stack([base[i] * w[c] for c in CONTEXTS]) for i in range(len(order))])
    return order, base, mesh, w


# ---- NEW INFORMATION UPTAKE: place a new op into the space + wire its strands ---------------------
def uptake(ops: dict, realm_name: str, verb: str, in_types=("N", "N"), out_types=("N",)):
    """Absorb a NEW op: assign it the next free byte in its realm, build its vector, and wire its
    strands against the existing catalog -- WITHOUT mutating the source of truth (an overlay). This
    is the 'new information uptake' hook: structure alone places and relates it, no retraining."""
    realm = next(r for r, n in TS.REALM.items() if n == realm_name)
    used = {b & 0xF for b in ops if b >> 4 == realm}
    free = [i for i in range(16) if i not in used]
    if not free:
        raise ValueError(f"realm {realm_name} (0x{realm:X}_) is full -- no free byte for a new op")
    byte = (realm << 4) | free[0]
    new = Op(byte, f"{realm_name}.{verb}", realm, tuple(in_types), tuple(out_types), tongues={})
    ov = vector(new)
    order, M, _ = build_matrix(ops)
    sims = M @ ov / (np.linalg.norm(M, axis=1) * (np.linalg.norm(ov) + 1e-9) + 1e-9)
    nearest = [(order[i], ops[order[i]].gloss, float(sims[i]))
               for i in np.argsort(-sims)[:5]]
    can_feed = sorted(b for b in ops
                      if any(_accepts(ot, it) for ot in out_types for it in ops[b].inputs))
    return {"byte": byte, "vector": ov, "nearest": nearest, "compose_into": can_feed}


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ops = _all_ops()
    order, M, idx = build_matrix(ops)
    st = strands(ops)
    fails = []

    print("=== vector array aligned to the six opcode sets ===\n")
    print(f"  {len(order)} opcodes  ->  matrix {M.shape}  (row = byte = the one thing all 6 tongues name)")
    print(f"  vector dims: {len(REALM_ORDER)} realm one-hot + lo-nibble + array-flag + exec-flag")
    print(f"               + in/out arity + in/out port-type multi-hot over {TVOCAB}\n")
    # show a couple aligned rows with their six-tongue surfaces
    print("  a few rows, with all six tongue words for the SAME byte:")
    for b in (0x00, 0x29, 0x47, 0x61):
        o = ops[b]
        words = " ".join(f"{c}:{o.tongues.get(c,'')}" for c in TS.ORDER)
        print(f"    0x{b:02X} {o.gloss:16} |v|={np.linalg.norm(M[idx[b]]):.2f}  {words}")

    print("\n=== context strands (underlying relationships) ===\n")
    for kind in ("compose", "realm", "meaning"):
        deg = [len(st[kind][b]) for b in order]
        print(f"  {kind:8} strand: {sum(deg)} directed links, mean degree {np.mean(deg):.1f}")
    # a meaning echo across realms is the interesting one -- show it
    for b in (0x00,):
        ms = st["meaning"][b]
        print(f"    meaning-echo of 0x{b:02X} ({ops[b].gloss}): "
              + ", ".join(f"0x{m:02X} {ops[m].gloss}" for m in ms))

    print("\n=== context mesh (reuse ONE token across fields: code / speak / comms / data) ===\n")
    corder, base, mesh, w = context_mesh(ops)
    neutral = mesh.mean(axis=1)                       # average the four field-views
    recon = float(np.max(np.abs(neutral - base)))
    print(f"  mesh tensor {mesh.shape}  (ops x contexts x dim); fields = {CONTEXTS}")
    print(f"  fields BALANCE to the neutral base: max|mean_field - base| = {recon:.2e}")
    if recon > 1e-4:
        fails.append(f"contexts do not average back to neutral (drift {recon:.2e})")
    b0 = 0x00; i0 = corder.index(b0)
    print(f"  op 0x{b0:02X} ({ops[b0].gloss}) -- how far each field-view sits from neutral (inner difference):")
    for j, c in enumerate(CONTEXTS):
        print(f"    {c:6}: |delta| = {np.linalg.norm(mesh[i0, j] - base[i0]):.3f}")

    def _nn(space, i, k=6):
        s = space @ space[i] / (np.linalg.norm(space, axis=1) * np.linalg.norm(space[i]) + 1e-9)
        return set(int(x) for x in np.argsort(-s)[1:k + 1])
    shared = len(_nn(mesh[:, 0, :], i0) & _nn(mesh[:, 1, :], i0))
    print(f"  cross-field mesh: op 0x{b0:02X} keeps {shared}/6 nearest neighbors between CODE and SPEAK views")

    print("\n=== new-information uptake (place + wire a brand-new op, no retraining) ===\n")
    NR, NV = "form", "spiral"
    up = uptake(ops, NR, NV, in_types=("G",), out_types=("G",))
    print(f"  new op '{NR}.{NV}' -> assigned byte 0x{up['byte']:02X}")
    print(f"  nearest existing ops by vector cosine (structure alone should pull it to {NR.upper()}):")
    for b, g, s in up["nearest"]:
        tag = "  <- same realm" if g.startswith(NR + ".") else ""
        print(f"    0x{b:02X} {g:16} cos={s:.3f}{tag}")
    top_realm = up["nearest"][0][1].split(".")[0]
    if top_realm != NR:
        fails.append(f"uptake placed {NR}.{NV} nearest to a {top_realm} op (space not meaningful)")
    print(f"  it can compose into {len(up['compose_into'])} ops downstream")

    # VERIFY alignment: every row has a word in all six tongues (or CA blank only if scbe absent)
    missing = sum(1 for b in order for c in ("KO", "AV", "RU", "UM", "DR") if not ops[b].tongues.get(c))
    if missing:
        fails.append(f"{missing} tongue surfaces missing (rows not fully aligned to the 6 sets)")

    print()
    if fails:
        print("  SELF-TEST: FAIL")
        for f in fails[:8]:
            print("   -", f)
        return 1
    print("  SELF-TEST: PASS  (128 opcodes as one aligned vector array across all six tongues;")
    print("                    compose/realm/meaning strands computed; a new op self-places by")
    print("                    structure into its own realm -- the substrate for learned uptake.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
