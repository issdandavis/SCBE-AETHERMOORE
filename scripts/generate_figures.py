"""Generate ASCII figures for SCBE-AETHERMOORE patent application."""
import math

def figure1():
    print("=" * 80)
    print("FIGURE 1: FOURTEEN-LAYER PIPELINE BLOCK DIAGRAM")
    print("=" * 80)
    print()
    lines = [
        "                    +----------------------------+",
        "                    |  INPUT: Context c(t)       |",
        "                    |  Authorization Request     |",
        "                    +-------------+--------------+",
        "                                 |",
        "  GROUP I: PREPARATION           |",
        "  +------------------------------+-------------------------------+",
        "  |  +------------------------+  |                               |",
        "  |  | L1: Complex Context    |<-+                               |",
        "  |  | c_j = A_j*e^(i*th_j)  |                                  |",
        "  |  +----------+-------------+                                  |",
        "  |             |                                                |",
        "  |  +----------v-------------+                                  |",
        "  |  | L2: Realification      |                                  |",
        "  |  | x = [Re(c), Im(c)]    |                                  |",
        "  |  +----------+-------------+                                  |",
        "  |             |                                                |",
        "  |  +----------v-------------+                                  |",
        "  |  | L3: SPD Weighting      |     G_k = phi^k (golden ratio)  |",
        "  |  | x_G = G^(1/2)*x       |                                  |",
        "  |  +----------+-------------+                                  |",
        "  |             |                                                |",
        "  |  +----------v-------------+                                  |",
        "  |  | L4: Poincare Embed     |     eps-clamping: ||u|| < 1-eps  |",
        "  |  | u=tanh(a||x||)*x/||x|||                                  |",
        "  |  +----------+-------------+                                  |",
        "  +-------------+-----------------------------------------------+",
        "                |",
        "  GROUP II: GEOMETRIC CORE",
        "  +-------------+-----------------------------------------------+",
        "  |  +----------v-------------------------------------------+   |",
        "  |  | L5: HYPERBOLIC DISTANCE  ** THE INVARIANT **          |   |",
        "  |  | d_H=arcosh(1+2||u-v||^2/((1-||u||^2)(1-||v||^2)))    |   |",
        "  |  | CANNOT BE CIRCUMVENTED -- MATHEMATICAL LAW            |   |",
        "  |  +----------+-------------------------------------------+   |",
        "  |             |                                                |",
        "  |  +----------v-------------+  +---------------------------+  |",
        "  |  | L6: Breathing          |  | L7: Phase Transform       |  |",
        "  |  | Diffeomorphism         |<>| Mobius + Rotation         |  |",
        "  |  | b>1: contain           |  | ISOMETRY: preserves d_H   |  |",
        "  |  | b<1: diffuse           |  | T = Q*(a (+) u)           |  |",
        "  |  +----------+-------------+  +----------+----------------+  |",
        "  +-------------+---------------------------+-------------------+",
        "                |",
        "  GROUP III: SIGNAL AGGREGATION",
        "  +-------------+-----------------------------------------------+",
        "  |  +----------v-------------+                                  |",
        "  |  | L8: Multi-Well Realm   |     d* = min_k d_H(u~, mu_k)   |",
        "  |  +----------+-------------+                                  |",
        "  |             |                                                |",
        "  |  +----------v-------------+  +---------------------------+  |",
        "  |  | L9: Spectral           |  | L10: Spin Coherence       |  |",
        "  |  | S = 1 - r_HF (FFT)    |->| C = |sum(e^(i*phi_j))|/N  |  |",
        "  |  +------------------------+  +----------+----------------+  |",
        "  |                                         |                    |",
        "  |  +--------------------------------------v-----------------+ |",
        "  |  | L11: Triadic Temporal Distance                          | |",
        "  |  | d_tri = sqrt(lam1*d1^2 + lam2*d2^2 + lam3*dG^2)       | |",
        "  |  +----------+---------------------------------------------+ |",
        "  +-------------+-----------------------------------------------+",
        "                |",
        "  GROUP IV: DECISION",
        "  +-------------+-----------------------------------------------+",
        "  |  +----------v-------------------------------------------+   |",
        "  |  | L12: HARMONIC WALL  ================================ |   |",
        "  |  | H(d,R) = R^(d^2)   == VERTICAL WALL =============== |   |",
        "  |  | d=1->2.7  d=3->8103  d=5->7.2e10                    |   |",
        "  |  +----------+-------------------------------------------+   |",
        "  |             |                                                |",
        "  |  +----------v-------------------------------------------+   |",
        "  |  | L13: RISK DECISION GATE                               |   |",
        "  |  | Risk' = B * H(d*) * T * I                             |   |",
        "  |  | +--------+ +-------------+ +---------+               |   |",
        "  |  | | ALLOW  | | QUARANTINE  | |  DENY   |               |   |",
        "  |  | | R<0.33 | | 0.33<=R<0.67| | R>=0.67 |               |   |",
        "  |  | +--------+ +-------------+ +---------+               |   |",
        "  |  +----------+-------------------------------------------+   |",
        "  |             |                                                |",
        "  |  +----------v-------------+                                  |",
        "  |  | L14: Audio Axis        |     Parallel FFT telemetry      |",
        "  |  +------------------------+                                  |",
        "  +-------------------------------------------------------------+",
    ]
    for line in lines:
        print(line)
    print()


def figure2():
    print("=" * 80)
    print("FIGURE 2: HARMONIC WALL DATA -- H(d,R) = R^(d^2), R = e")
    print("=" * 80)
    print()
    print("  Key Data Points:")
    print("  +--------+--------------+----------+------------------------------+")
    print("  |  d     |  H(d) = e^d2 |  log10 H |  Security Interpretation     |")
    print("  +--------+--------------+----------+------------------------------+")
    data = [
        (0, "Trusted center"),
        (0.5, "Normal operation"),
        (1.0, "Modest increase"),
        (1.5, "Noticeable barrier"),
        (2.0, "Significant barrier"),
        (2.5, "Strong barrier"),
        (3.0, "Prohibitive cost"),
        (4.0, "Computationally infeasible"),
        (5.0, "Exceeds global compute"),
    ]
    for d, interp in data:
        h = math.exp(d**2)
        logh = math.log10(h)
        if h < 1e6:
            print(f"  |  {d:<4.1f}  |  {h:>12.2f}|  {logh:>7.3f} |  {interp:<28s} |")
        else:
            print(f"  |  {d:<4.1f}  |  {h:>12.2e}|  {logh:>7.3f} |  {interp:<28s} |")
    print("  +--------+--------------+----------+------------------------------+")
    print()
    print(f"  Critical thresholds:")
    print(f"  128-bit (post-quantum):  d_crit = {math.sqrt(128*math.log(2)):.4f}")
    print(f"  256-bit (classical):     d_crit = {math.sqrt(256*math.log(2)):.4f}")
    print()


def figure3():
    print("=" * 80)
    print("FIGURE 3: POINCARE BALL CROSS-SECTION WITH RING BOUNDARIES")
    print("=" * 80)
    print()
    size = 15
    for y in range(-size, size + 1):
        line = "  "
        for x in range(-size * 2, size * 2 + 1):
            nx = x / (size * 2)
            ny = y / size
            r = math.sqrt(nx**2 + ny**2)
            if abs(r - 1.0) < 0.04:
                line += "#"
            elif abs(r - 0.95) < 0.03:
                line += "%"
            elif abs(r - 0.80) < 0.03:
                line += "="
            elif abs(r - 0.60) < 0.03:
                line += "-"
            elif abs(r - 0.40) < 0.03:
                line += "."
            elif abs(r - 0.20) < 0.03:
                line += ":"
            elif r < 0.05:
                line += "@"
            elif r > 1.0:
                line += " "
            else:
                line += " "
        print(line)
    print()
    print("  Ring Levels:")
    print("  @ Ring 0 (r < 0.20): CORE -- Most trusted")
    print("  : Ring 1 (0.20 <= r < 0.40): Inner -- High trust")
    print("  . Ring 2 (0.40 <= r < 0.60): Middle -- Moderate trust")
    print("  - Ring 3 (0.60 <= r < 0.80): Outer -- Low trust")
    print("  = Ring 4 (0.80 <= r < 0.95): Edge -- Minimal trust")
    print("  # Boundary (r -> 1.0): INFINITE COST -- Unreachable")
    print()


def figure4():
    print("=" * 80)
    print("FIGURE 4: SIX SACRED TONGUES -- PHASE AND WEIGHT DIAGRAM")
    print("=" * 80)
    print()
    lines = [
        "                          KO (0 deg)",
        "                       w = 1.000",
        "                     Intent/Binding",
        "                          |",
        "   DR (300 deg)           |           AV (60 deg)",
        "   w = 11.090             |           w = 1.618",
        "   Authority              |           Diplomacy",
        '          \\               |               /',
        '           \\              |              /',
        '            \\             |             /',
        '             \\            |            /',
        '              \\           |           /',
        "               +----------+----------+",
        '              /           |           \\',
        '             /            |            \\',
        '            /             |             \\',
        '           /              |              \\',
        '          /               |               \\',
        "   UM (240 deg)           |           RU (120 deg)",
        "   w = 6.854              |           w = 2.618",
        "   Concealment            |           Temporal",
        "                          |",
        "                      CA (180 deg)",
        "                      w = 4.236",
        "                      Ecological",
    ]
    for line in lines:
        print(line)
    print()
    print("  Harmonic Frequencies (Musical Intervals):")
    print("  +------+----------+--------------+------------------+")
    print("  | Code | Interval | Freq. Ratio  | Phase Offset     |")
    print("  +------+----------+--------------+------------------+")
    print("  |  KO  | Root     |    1/1       |   0 deg = 0      |")
    print("  |  AV  | Major 2nd|    9/8       |  60 deg = pi/3   |")
    print("  |  RU  | Major 3rd|    5/4       | 120 deg = 2pi/3  |")
    print("  |  CA  | Perf. 4th|    4/3       | 180 deg = pi     |")
    print("  |  UM  | Perf. 5th|    3/2       | 240 deg = 4pi/3  |")
    print("  |  DR  | Major 6th|    5/3       | 300 deg = 5pi/3  |")
    print("  +------+----------+--------------+------------------+")
    print()


def figure5():
    print("=" * 80)
    print("FIGURE 5: SACRED EGG HATCH DECISION FLOWCHART")
    print("=" * 80)
    print()
    lines = [
        "  +-----------------------------------------------------------+",
        "  |              SACRED EGG HATCH REQUEST                      |",
        "  |              E = (hdr, C, tag, policy)                     |",
        "  +----------------------------+------------------------------+",
        "                               |",
        "                  +------------v-----------+",
        "                  | P_tongue: Domain       |",
        "                  | membership check       |---- FAIL --+",
        "                  +------------+-----------+             |",
        "                          PASS |                         |",
        "                  +------------v-----------+             |",
        "                  | P_geo: Ring level      |             |",
        "                  | <= ring_max?           |---- FAIL --+",
        "                  +------------+-----------+             |",
        "                          PASS |                         |",
        "                  +------------v-----------+             |",
        "                  | P_path: Monotone       |             |",
        "                  | ring descent?          |---- FAIL --+",
        "                  +------------+-----------+             |",
        "                          PASS |                         |",
        "                  +------------v-----------+             |",
        "                  | P_quorum: |A| >= q     |             |",
        "                  | All sigs verify?       |---- FAIL --+",
        "                  +------------+-----------+             |",
        "                          PASS |                         v",
        "                  +------------v-----------+  +------------------+",
        "                  | P_crypto: AEAD         |  | FAIL-TO-NOISE    |",
        "                  | K = HKDF(ss,DST,256)   |  | output=random(|C|)|",
        "                  | Decrypt(K, C, tag)     |  | Indistinguishable |",
        "                  +------------+-----------+  | from success      |",
        "                          PASS |              +------------------+",
        "             +------------------+",
        "             v",
        "  +-------------------+",
        "  | SUCCESS           |",
        "  | Return plaintext  |",
        "  +-------------------+",
    ]
    for line in lines:
        print(line)
    print()
    print("  DST = Enc(tongue) || Enc(ring) || Enc(cell) || Enc(pathDigest) || Enc(epoch)")
    print("  Any change to ANY component -> completely different key -> decryption fails")
    print()


def figure10():
    print("=" * 80)
    print("FIGURE 10: ANTI-FRAGILE SHOCK ABSORBER")
    print("=" * 80)
    print()
    print("  Psi(P) = 1 + (max-1)*tanh(beta*P),  max=1.56, beta=3.0")
    print()
    for row in range(12, -1, -1):
        val = 1.0 + row * 0.05
        label = f"  {val:.2f} |"
        line = ""
        for col in range(50):
            P = col / 50.0
            psi = 1.0 + (1.56 - 1.0) * math.tanh(3.0 * P)
            if abs(psi - val) < 0.03:
                line += "*"
            else:
                line += " "
        print(f"{label}{line}")
    print(f"  1.00 |" + "-" * 50)
    print(f"       +" + "-" * 50)
    print(f"        0.0       0.2       0.4       0.6       0.8       1.0")
    print(f"                    Attack Pressure P")
    print()
    print("  P=0.0: Psi = 1.00 (no expansion)")
    print("  P=0.5: Psi ~ 1.38 (38% distance increase)")
    print("  P=1.0: Psi ~ 1.56 (56% distance increase)")
    print()
    print("  The harder you attack, the further you get from the target.")
    print()


if __name__ == "__main__":
    figure1()
    print()
    figure2()
    print()
    figure3()
    print()
    figure4()
    print()
    figure5()
    print()
    figure10()
