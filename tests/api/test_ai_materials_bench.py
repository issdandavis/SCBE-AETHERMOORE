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


def test_ai_materials_bench_models_fiber_tube_stack() -> None:
    result = run_node_json("""
        const handler = require('./api/agent/ai-materials-bench');
        const req = {
          method: 'POST',
          body: {
            concept: 'glass tube carbon sleeve copper winding ferrite optical path',
            length_mm: 120,
            radius_mm: 5,
            turns: 180,
            current_a: 0.35,
            wire_diameter_mm: 0.2,
            frequency_hz: 1000,
            mu_relative: 1,
            n_core: 1.46,
            n_clad: 1.44
          },
          headers: {}
        };
        const res = {
          code: 200,
          headers: {},
          setHeader(name, value) { this.headers[name] = value; },
          status(code) { this.code = code; return this; },
          json(payload) { this.payload = payload; return this; },
          end() { return this; }
        };
        Promise.resolve(handler(req, res)).then(() => {
          console.log(JSON.stringify({code: res.code, payload: res.payload}));
        }).catch((error) => {
          console.error(error);
          process.exit(1);
        });
        """)

    assert result["code"] == 200
    payload = result["payload"]
    assert payload["schema_version"] == "aethermoore_ai_materials_bench_v1"
    assert payload["product"] == "AI Materials Bench"
    assert payload["architecture"]["name"] == "magneto-optic composite tube sleeve"
    assert payload["math"]["estimates"]["solenoid_field_mt"] > 0
    assert payload["math"]["estimates"]["coil_power_w"] > 0
    assert payload["receipt_id"].startswith("matbench_")
    assert any(layer["layer"] == "carbon skin" for layer in payload["architecture"]["stack"])


def test_named_material_drives_physics_and_flags_assumptions() -> None:
    result = run_node_json("""
        const handler = require('./api/agent/ai-materials-bench');
        const run = (body) => new Promise((resolve) => {
          const res = { setHeader(){}, status(){return this;},
            json(p){ resolve(p); return this; }, end(){return this;} };
          handler({ method: 'POST', body }, res);
        });
        Promise.all([
          run({ concept: 'copper coil over quartz', turns: 200, current_a: 1 }),
          run({ concept: 'silver coil over quartz', turns: 200, current_a: 1 }),
          run({ concept: 'aluminum coil over quartz', turns: 200, current_a: 1 }),
          run({ concept: 'silica fiber', n_core: 1.46 }),
          run({ concept: 'silver coil', current_a: 999, turns: 99999 }),
        ]).then(([cu, ag, al, fiber, extreme]) => {
          console.log(JSON.stringify({
            cu_conductor: cu.math.conductor,
            ag_conductor: ag.math.conductor,
            cu_r: cu.math.estimates.coil_resistance_ohm,
            ag_r: ag.math.estimates.coil_resistance_ohm,
            al_r: al.math.estimates.coil_resistance_ohm,
            assumed_nclad: fiber.math.assumed.some((a) => a.includes('n_clad')),
            nclad_echoed: fiber.math.inputs.n_clad,
            unphysical: extreme.risk_flags.some((f) => f.toLowerCase().includes('non-physical')),
          }));
        }).catch((e) => { console.error(e); process.exit(1); });
        """)

    assert result["cu_conductor"] == "copper"
    assert result["ag_conductor"] == "silver"
    assert result["ag_r"] < result["cu_r"]  # silver is less resistive than copper
    assert result["al_r"] > result["cu_r"]  # aluminum is more resistive
    assert result["assumed_nclad"] is True  # missing variable is disclosed
    assert result["nclad_echoed"] == 1.44
    assert result["unphysical"] is True  # extreme inputs flagged non-physical


def test_concept_report_is_a_sellable_deliverable() -> None:
    result = run_node_json("""
        const handler = require('./api/agent/ai-materials-bench');
        const run = (body) => new Promise((resolve) => {
          const res = { setHeader(){}, status(){return this;},
            json(p){ resolve(p); return this; }, end(){return this;} };
          handler({ method: 'POST', body }, res);
        });
        run({ concept: 'silver coil over quartz tube', turns: 200, current_a: 1 }).then((p) => {
          console.log(JSON.stringify({
            bom_items: p.bill_of_materials.items.length,
            total_low: p.bill_of_materials.estimated_total_low,
            total_high: p.bill_of_materials.estimated_total_high,
            voltage: p.safety.coil_voltage_v,
            max_current: p.safety.max_continuous_current_a,
            plan_steps: p.test_plan.length,
            report_has_bom: p.report_markdown.includes('Bill of materials'),
            report_has_plan: p.report_markdown.includes('Test plan'),
            report_has_receipt: p.report_markdown.includes(p.receipt_id),
            report_len: p.report_markdown.length,
          }));
        }).catch((e) => { console.error(e); process.exit(1); });
        """)

    assert result["bom_items"] >= 5  # a real parts list
    assert result["total_high"] > result["total_low"] > 0  # costed, with a range
    assert result["voltage"] > 0  # derived operating voltage
    assert result["max_current"] > 0  # derived safe-current limit
    assert result["plan_steps"] >= 4  # a measurement protocol
    assert result["report_has_bom"] is True  # the deliverable has the BOM
    assert result["report_has_plan"] is True  # ...and the test plan
    assert result["report_has_receipt"] is True  # ...and is provenance-stamped
    assert result["report_len"] > 600  # a substantive document


def test_ai_materials_bench_page_contains_visualizer() -> None:
    page = (REPO_ROOT / "docs" / "ai-materials-bench.html").read_text(encoding="utf-8")

    assert "Fiber/tube stack visualizer with real math" in page
    assert "<canvas" in page
    assert "magneto-optic composite tube sleeve" in page
    assert "/api/agent/ai-materials-bench" in page
    assert "Download concept report" in page
