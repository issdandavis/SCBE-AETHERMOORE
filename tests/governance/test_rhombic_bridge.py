import numpy as np

from python.scbe.rhombic_bridge import rhombic_fusion, rhombic_score


def test_rhombic_fusion_low_when_modalities_match():
    x = np.array([1.0, 2.0, 3.0])
    audio = np.array([1.0, 2.0, 3.0])
    vision = np.array([1.0, 2.0, 3.0])
    governance = np.array([1.0, 2.0, 3.0])
    R = rhombic_fusion(x=x, audio=audio, vision=vision, governance=governance, k=0)
    assert R >= 0.0
    assert rhombic_score(R) > 0.1


def test_rhombic_fusion_spikes_on_mismatch():
    x = np.array([1.0, 2.0, 3.0])
    audio = np.array([1.0, 2.0, 3.0])
    vision = np.array([100.0, 200.0, 300.0])
    governance = np.array([1.0, 2.0, 3.0])
    R_good = rhombic_fusion(x=x, audio=audio, vision=audio, governance=governance, k=0)
    R_bad = rhombic_fusion(x=x, audio=audio, vision=vision, governance=governance, k=0)
    assert R_bad > R_good

