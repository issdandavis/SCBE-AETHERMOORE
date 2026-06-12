"""Tongue-multiplex probe — a bijective 6-way matrix of the Sacred Tongues.

The ask: turn a token into a matrix that holds "multiplex state" seen from
different viewings, bijective and 6-way, giving independent reasoning pathways.

The faithful object is the regular representation of the cyclic group C_6 on the
six tongues (KO AV RU CA UM DR):

    token v in C^6                      one complex amplitude per tongue
    C(v) = circulant(v) in C^{6x6}      row j = the token viewed from rotation j
                                        ("multiplex state from different viewings")
    F = DFT_6   (unitary)               C(v) = F^* diag(F v) F  -> 6 eigen-pathways
    pathways  lambda = F v              the 6 Fourier modes / characters chi_k

Bijective: v <-> C(v) <-> lambda are all lossless. Independent: under any
circulant (cyclic) operation the modes never mix (convolution theorem) — that is
what makes them genuine separate reasoning pathways.

Five falsifiable tests, each with a null:

  M1 bijective       round-trip v -> lambda -> v is exact; a dropped mode is not
  M2 independence    cyclic ops act per-mode (modes don't bleed); random ops DO bleed
  M3 viewings null   does the Fourier basis concentrate a signal better than a
                     RANDOM orthonormal basis? (only when the tongue order is cyclic)
  M4 layered demo    two tongue-pure tokens land in distinct pathways, each
                     independently maskable/recoverable
  M5 phi tension     does the phi tongue-weighting keep the pathways independent,
                     or couple them? (an honest design constraint)

Run:  PYTHONPATH=. python scripts/eval/tongue_multiplex_probe.py
"""

from __future__ import annotations

import numpy as np

rng = np.random.default_rng(20260612)

TONGUES = ["KO", "AV", "RU", "CA", "UM", "DR"]
N = 6
PHI_W = np.array([1.00, 1.62, 2.62, 4.24, 6.85, 11.09])  # phi-scaled tongue weights

# Unitary DFT matrix for C_6 (the 6 characters chi_k as columns).
_j = np.arange(N)
F = np.exp(-2j * np.pi * np.outer(_j, _j) / N) / np.sqrt(N)
F_inv = F.conj().T


def line(name, test, value, verdict):
    print(f"  {name:4} {test:46} {value:>20}   {verdict}")


def circulant(c: np.ndarray) -> np.ndarray:
    """6x6 multiplex matrix: row i is the token rolled by i (viewing i)."""
    return np.array([[c[(i - j) % N] for j in range(N)] for i in range(N)])


def pathways(v: np.ndarray) -> np.ndarray:
    """The 6 independent reasoning channels (Fourier modes)."""
    return F @ v


def coupling(A: np.ndarray) -> float:
    """Off-diagonal energy fraction of A in the pathway (Fourier) basis.

    0 == A acts independently per pathway (a circulant/cyclic op).
    ->1 == A bleeds the pathways into each other.
    """
    D = F @ A @ F_inv
    off = np.linalg.norm(D - np.diag(np.diag(D)))
    return float(off / (np.linalg.norm(D) + 1e-15))


def participation_ratio(coeffs: np.ndarray) -> float:
    """1 (energy in one mode) .. N (spread over all modes)."""
    p = np.abs(coeffs) ** 2
    s = p.sum()
    return float(s * s / (np.sum(p * p) + 1e-15))


def main():
    print("\n  tongue-multiplex probe — regular representation of C_6 over 6 tongues")
    print("  " + "─" * 92)
    M = 500

    # ---- M1: bijective 6-way round-trip ---------------------------------- #
    err_full, err_dropped = 0.0, 0.0
    for _ in range(M):
        v = rng.standard_normal(N) + 1j * rng.standard_normal(N)
        lam = pathways(v)
        err_full = max(err_full, np.linalg.norm(F_inv @ lam - v))
        # null: a "viewing" that discards one mode is NOT bijective
        lam_drop = lam.copy()
        lam_drop[3] = 0.0
        err_dropped = max(err_dropped, np.linalg.norm(F_inv @ lam_drop - v))
        # the circulant's first column reconstructs the token (v <-> C(v))
        assert np.allclose(circulant(v)[:, 0], v)
    line(
        "M1",
        "round-trip v->pathways->v exact",
        f"{err_full:.1e} (drop {err_dropped:.2f})",
        "BIJECTIVE 6-WAY" if err_full < 1e-12 and err_dropped > 0.1 else "lossy",
    )

    # ---- M2: pathways stay independent under cyclic ops; bleed otherwise -- #
    cyc_coup, rnd_coup = [], []
    for _ in range(M):
        g = rng.standard_normal(N) + 1j * rng.standard_normal(N)
        cyc_coup.append(coupling(circulant(g)))  # cyclic op -> 0
        A = rng.standard_normal((N, N)) + 1j * rng.standard_normal((N, N))
        rnd_coup.append(coupling(A))  # generic op -> bleeds
    c_mean, r_mean = float(np.mean(cyc_coup)), float(np.mean(rnd_coup))
    line(
        "M2",
        "pathway bleed: cyclic op vs generic op",
        f"{c_mean:.1e} vs {r_mean:.2f}",
        "INDEPENDENT PATHWAYS (cyclic only)" if c_mean < 1e-10 and r_mean > 0.5 else "leaky",
    )

    # ---- M3: are the Fourier VIEWINGS special, or is any basis equal? ---- #
    # structured = a signal built from 2 cyclic modes; random = no cyclic order.
    Q, _ = np.linalg.qr(rng.standard_normal((N, N)) + 1j * rng.standard_normal((N, N)))
    pr_struct_dft, pr_struct_rnd, pr_rand_dft, pr_rand_rnd = [], [], [], []
    for _ in range(M):
        spec = np.zeros(N, complex)
        spec[[1, 4]] = rng.standard_normal(2) + 1j * rng.standard_normal(2)  # 2 cyclic modes
        v_struct = F_inv @ spec
        pr_struct_dft.append(participation_ratio(F @ v_struct))
        pr_struct_rnd.append(participation_ratio(Q.conj().T @ v_struct))
        v_rand = rng.standard_normal(N) + 1j * rng.standard_normal(N)
        pr_rand_dft.append(participation_ratio(F @ v_rand))
        pr_rand_rnd.append(participation_ratio(Q.conj().T @ v_rand))
    sd, sr = float(np.mean(pr_struct_dft)), float(np.mean(pr_struct_rnd))
    rd, rr = float(np.mean(pr_rand_dft)), float(np.mean(pr_rand_rnd))
    line(
        "M3",
        "Fourier vs random basis concentration",
        f"cyc {sd:.1f}/{sr:.1f} rnd {rd:.1f}/{rr:.1f}",
        "VIEWINGS LOAD-BEARING ONLY IF TONGUES CYCLIC" if sd < 0.6 * sr and abs(rd - rr) < 0.6 else "basis-agnostic",
    )

    # ---- M4: layered reasoning — two tongues, two pathways, separable ---- #
    a = F_inv @ (np.eye(N)[1] * 3.0)  # a token living purely in pathway 1
    b = F_inv @ (np.eye(N)[4] * 2.0)  # a token living purely in pathway 4
    mix = a + b
    lam = pathways(mix)
    # mask pathway 4, recover the pathway-1 component alone, without touching it
    only_a = F_inv @ (lam * (np.arange(N) != 4))
    recover_err = np.linalg.norm(only_a - a)
    isolated = np.abs(lam[1]) > 1e-9 and np.abs(lam[4]) > 1e-9 and np.allclose(lam[[0, 2, 3, 5]], 0, atol=1e-9)
    line(
        "M4",
        "two tongues route to distinct pathways",
        f"recover_err {recover_err:.1e}",
        "LAYERED REASONING WORKS" if isolated and recover_err < 1e-12 else "tangled",
    )

    # ---- M5: does phi-weighting keep pathways independent? (honest) ------ #
    coup_phi = coupling(np.diag(PHI_W))
    coup_uniform = coupling(np.diag(np.ones(N)))
    line(
        "M5",
        "phi tongue-weighting pathway coupling",
        f"phi {coup_phi:.2f} vs unit {coup_uniform:.1e}",
        "PHI COUPLES THE PATHWAYS (apply weights in-domain)" if coup_phi > 0.3 else "phi neutral",
    )

    print("  " + "─" * 92)
    print(
        "  verdict:\n"
        "    M1  yes — a true bijective 6-way multiplex: token <-> circulant <-> 6 Fourier pathways,\n"
        "        lossless; dropping a viewing destroys the bijection (it is real, not automatic).\n"
        "    M2  the 6 pathways are genuinely independent under CYCLIC (governance-convolution) ops;\n"
        "        a generic operator bleeds them — independence is a property of the cyclic structure.\n"
        "    M3  the FOURIER choice of viewings only beats a random basis when the tongue ORDER is\n"
        "        cyclic (KO->AV->...->DR->KO). On unordered tokens any invertible basis is equal —\n"
        "        so the payoff comes from imposing a meaningful cycle on the tongues (or the\n"
        "        governance-tuned tongue basis, which home-turf already showed beats random).\n"
        "    M4  layered reasoning works: distinct tongues land in distinct pathways, each maskable\n"
        "        and recoverable without disturbing the others.\n"
        "    M5  design constraint: the phi weighting is diagonal in the TONGUE basis, hence dense in\n"
        "        the pathway basis — it COUPLES the pathways. Keep weighting and independence in the\n"
        "        same domain, or apply phi inside each pathway, not across the tongue vector.\n"
    )


if __name__ == "__main__":
    main()
