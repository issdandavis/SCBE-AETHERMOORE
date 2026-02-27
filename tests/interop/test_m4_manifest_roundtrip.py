from src.m4mesh.manifest import FluxManifest


def test_manifest_roundtrip_and_hash_stable():
    manifest = FluxManifest(alpha_C=0.4, alpha_K=0.35, alpha_T=0.25)
    as_dict = manifest.to_dict()
    clone = FluxManifest.from_dict(as_dict)

    assert clone == manifest
    assert clone.hash() == manifest.hash()
    assert len(manifest.hash()) == 64
