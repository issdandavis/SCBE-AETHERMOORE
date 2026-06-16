from __future__ import annotations

import json
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def run_node_json(source: str) -> dict:
    completed = subprocess.run(
        ["node", "-e", source],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


def test_ai_waves_lab_models_fiber_room() -> None:
    result = run_node_json("""
        const handler = require('./api/agent/ai-waves-lab');
        const req = {
          method: 'POST',
          body: {
            room: 'fiber-room',
            concept: '1550 nm single mode fiber waveguide',
            wavelength_nm: 1550,
            fiber_length_km: 10,
            n_core: 1.46,
            n_clad: 1.44,
            attenuation_db_km: 0.2,
            dispersion_ps_nm_km: 17,
            linewidth_nm: 0.1
          }
        };
        const res = {
          code: 200, headers: {},
          setHeader(name, value) { this.headers[name] = value; },
          status(code) { this.code = code; return this; },
          json(payload) { this.payload = payload; return this; },
          end() { return this; }
        };
        Promise.resolve(handler(req, res)).then(() => {
          console.log(JSON.stringify({code: res.code, payload: res.payload}));
        }).catch((error) => { console.error(error); process.exit(1); });
        """)

    assert result["code"] == 200
    payload = result["payload"]
    assert payload["schema_version"] == "aethermoore_ai_waves_lab_v1"
    assert payload["product"] == "AI Waves Lab"
    assert payload["room"] == "fiber-room"
    assert payload["math"]["outputs"]["total_loss_db"] == 2
    assert payload["math"]["outputs"]["numerical_aperture"] > 0
    assert payload["receipt_id"].startswith("waves_")


def test_ai_waves_lab_routes_photonic_and_flags_simulated_claim() -> None:
    result = run_node_json("""
        const handler = require('./api/agent/ai-waves-lab');
        const run = (body) => new Promise((resolve) => {
          const res = { setHeader(){}, status(){return this;},
            json(p){ resolve(p); return this; }, end(){return this;} };
          handler({ method: 'POST', body }, res);
        });
        Promise.all([
          run({ room: 'photonic-route-room', matmul_fraction: 0.9, nonlinear_op_fraction: 0.2, precision_required_bits: 16, branching_density: 0.05, memory_access_density: 0.1 }),
          run({ room: 'interference-room', wavelength_nm: 500, path_difference_um: 0.25, amplitude_1: 1, amplitude_2: 1 }),
          run({ room: 'refraction-room', n1: 1, n2: 1.5, incident_angle_deg: 30 })
        ]).then(([route, fringe, refract]) => {
          console.log(JSON.stringify({
            routeDecision: route.math.outputs.decision,
            hardwareClaim: route.math.outputs.hardware_claim,
            routeFlag: route.risk_flags.some((f) => f.includes('simulator')),
            fringe: fringe.math.outputs.fringe,
            refracted: refract.math.outputs.refracted_angle_deg
          }));
        }).catch((e) => { console.error(e); process.exit(1); });
        """)

    assert result["routeDecision"] in {"PHOTONIC_NPU", "PHOTONIC_NPU_WITH_VERIFY"}
    assert result["hardwareClaim"] == "simulated"
    assert result["routeFlag"] is True
    assert result["fringe"] == "destructive-biased"
    assert 19 < result["refracted"] < 20


def test_ai_waves_lab_page_contains_visualizer() -> None:
    page = (REPO_ROOT / "docs" / "ai-waves-lab.html").read_text(encoding="utf-8")

    assert "Wave, fiber, and photonic receipts with visuals" in page
    assert "<canvas" in page
    assert "/api/agent/ai-waves-lab" in page
    assert "photonic-route-room" in page
    assert "Buy $49 report" in page
    assert "Request $199 worksheet" in page
