'use strict';

const crypto = require('node:crypto');

const C = 299792458;

function setCors(res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST,OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
}

function readBody(req, maxBytes = 12000) {
  if (req.body && typeof req.body === 'object') return Promise.resolve(req.body);
  return new Promise((resolve, reject) => {
    let raw = '';
    req.on('data', (chunk) => {
      raw += chunk;
      if (raw.length > maxBytes) {
        reject(new Error('request body too large'));
        req.destroy();
      }
    });
    req.on('end', () => {
      if (!raw.trim()) return resolve({});
      try {
        resolve(JSON.parse(raw));
      } catch (error) {
        reject(error);
      }
    });
    req.on('error', reject);
  });
}

function sha(value) {
  return crypto.createHash('sha256').update(String(value)).digest('hex');
}

function numA(body, key, fallback, min, max, assumed) {
  const raw = body ? body[key] : undefined;
  const parsed = Number(raw);
  if (raw === undefined || raw === null || raw === '' || !Number.isFinite(parsed)) {
    assumed.push(`${key} = ${fallback} (assumed default)`);
    return fallback;
  }
  const clamped = Math.max(min, Math.min(max, parsed));
  if (clamped !== parsed) assumed.push(`${key} = ${clamped} (clamped from ${parsed})`);
  return clamped;
}

function inferRoom(body) {
  const explicit = String(body.room || '').toLowerCase().trim();
  if (explicit) return explicit;
  const concept = String(body.concept || '').toLowerCase();
  if (concept.includes('photonic') || concept.includes('accelerator') || concept.includes('npu')) return 'photonic-route';
  if (concept.includes('fiber') || concept.includes('waveguide') || concept.includes('otdr')) return 'fiber-room';
  if (concept.includes('refraction') || concept.includes('prism') || concept.includes('snell')) return 'refraction-room';
  if (concept.includes('interference') || concept.includes('slit') || concept.includes('fringe')) return 'interference-room';
  if (concept.includes('transistor') || concept.includes('cavity') || concept.includes('bistable')) return 'optical-switch-room';
  return 'fiber-room';
}

function fiberCalc(body, assumed) {
  const wavelengthNm = numA(body, 'wavelength_nm', 1550, 380, 2500, assumed);
  const lengthKm = numA(body, 'fiber_length_km', 10, 0.001, 500, assumed);
  const nCore = numA(body, 'n_core', 1.46, 1, 4, assumed);
  const nClad = numA(body, 'n_clad', 1.44, 1, 4, assumed);
  const attenuationDbKm = numA(body, 'attenuation_db_km', 0.2, 0, 20, assumed);
  const dispersionPsNmKm = numA(body, 'dispersion_ps_nm_km', 17, -200, 200, assumed);
  const linewidthNm = numA(body, 'linewidth_nm', 0.1, 0, 50, assumed);
  const frequencyHz = C / (wavelengthNm * 1e-9);
  const phaseVelocity = C / nCore;
  const groupDelayNs = (nCore * lengthKm * 1000 / C) * 1e9;
  const totalLossDb = attenuationDbKm * lengthKm;
  const powerRatio = Math.pow(10, -totalLossDb / 10);
  const numericalAperture = Math.sqrt(Math.max(0, nCore * nCore - nClad * nClad));
  const pulseBroadeningPs = Math.abs(dispersionPsNmKm) * linewidthNm * lengthKm;
  return {
    room: 'fiber-room',
    inputs: { wavelength_nm: wavelengthNm, fiber_length_km: lengthKm, n_core: nCore, n_clad: nClad, attenuation_db_km: attenuationDbKm, dispersion_ps_nm_km: dispersionPsNmKm, linewidth_nm: linewidthNm },
    outputs: {
      optical_frequency_thz: Number((frequencyHz / 1e12).toPrecision(6)),
      phase_velocity_m_s: Number(phaseVelocity.toPrecision(6)),
      group_delay_ns: Number(groupDelayNs.toPrecision(6)),
      total_loss_db: Number(totalLossDb.toPrecision(6)),
      output_power_ratio: Number(powerRatio.toPrecision(6)),
      numerical_aperture: Number(numericalAperture.toPrecision(6)),
      dispersion_broadening_ps: Number(pulseBroadeningPs.toPrecision(6)),
    },
  };
}

function interferenceCalc(body, assumed) {
  const wavelengthNm = numA(body, 'wavelength_nm', 532, 380, 2500, assumed);
  const pathDiffUm = numA(body, 'path_difference_um', 0.25, -10000, 10000, assumed);
  const a1 = numA(body, 'amplitude_1', 1, 0, 100, assumed);
  const a2 = numA(body, 'amplitude_2', 1, 0, 100, assumed);
  const phase = 2 * Math.PI * (pathDiffUm * 1e-6) / (wavelengthNm * 1e-9);
  const resultant = Math.sqrt(a1 * a1 + a2 * a2 + 2 * a1 * a2 * Math.cos(phase));
  const normalizedIntensity = (resultant * resultant) / Math.max(1e-12, (a1 + a2) * (a1 + a2));
  return {
    room: 'interference-room',
    inputs: { wavelength_nm: wavelengthNm, path_difference_um: pathDiffUm, amplitude_1: a1, amplitude_2: a2 },
    outputs: {
      phase_difference_rad: Number(phase.toPrecision(6)),
      resultant_amplitude: Number(resultant.toPrecision(6)),
      normalized_intensity: Number(normalizedIntensity.toPrecision(6)),
      fringe: Math.cos(phase) >= 0 ? 'constructive-biased' : 'destructive-biased',
    },
  };
}

function refractionCalc(body, assumed) {
  const n1 = numA(body, 'n1', 1, 1, 4, assumed);
  const n2 = numA(body, 'n2', 1.5, 1, 4, assumed);
  const theta1Deg = numA(body, 'incident_angle_deg', 35, 0, 89.9, assumed);
  const theta1 = theta1Deg * Math.PI / 180;
  const sinTheta2 = (n1 / n2) * Math.sin(theta1);
  const totalInternal = Math.abs(sinTheta2) > 1;
  const theta2Deg = totalInternal ? null : Math.asin(sinTheta2) * 180 / Math.PI;
  const criticalDeg = n1 > n2 ? Math.asin(n2 / n1) * 180 / Math.PI : null;
  const brewsterDeg = Math.atan(n2 / n1) * 180 / Math.PI;
  return {
    room: 'refraction-room',
    inputs: { n1, n2, incident_angle_deg: theta1Deg },
    outputs: {
      refracted_angle_deg: theta2Deg === null ? null : Number(theta2Deg.toPrecision(6)),
      total_internal_reflection: totalInternal,
      critical_angle_deg: criticalDeg === null ? null : Number(criticalDeg.toPrecision(6)),
      brewster_angle_deg: Number(brewsterDeg.toPrecision(6)),
    },
  };
}

function opticalSwitchCalc(body, assumed) {
  const gainPeak = numA(body, 'gain_peak', 2.0, 0, 20, assumed);
  const absorberPeak = numA(body, 'absorber_peak', 1.5, 0, 20, assumed);
  const linearLoss = numA(body, 'linear_loss', 0.6, 0, 20, assumed);
  const lockingBandwidth = numA(body, 'locking_bandwidth', 1.0, 0.001, 1000, assumed);
  const detuning = numA(body, 'detuning', 0.3, -1000, 1000, assumed);
  const netSmallSignal = 0.81 * Math.exp(gainPeak - absorberPeak - linearLoss);
  const lockMargin = lockingBandwidth - Math.abs(detuning);
  const bistableLikely = absorberPeak > linearLoss && gainPeak > linearLoss && netSmallSignal < 1.2;
  return {
    room: 'optical-switch-room',
    inputs: { gain_peak: gainPeak, absorber_peak: absorberPeak, linear_loss: linearLoss, locking_bandwidth: lockingBandwidth, detuning },
    outputs: {
      small_signal_round_trip_gain: Number(netSmallSignal.toPrecision(6)),
      injection_locked: lockMargin > 0,
      lock_margin: Number(lockMargin.toPrecision(6)),
      bistable_screen: bistableLikely ? 'candidate' : 'not-established',
      cascadability_note: 'screening estimate only; use src/physics_sim/optical_transistor.py for full fixed-point/null-gate run',
    },
  };
}

function photonicRouteCalc(body, assumed) {
  const matmul = numA(body, 'matmul_fraction', 0.75, 0, 1, assumed);
  const nonlinear = numA(body, 'nonlinear_op_fraction', 0.12, 0, 1, assumed);
  const precision = Math.round(numA(body, 'precision_required_bits', 16, 1, 128, assumed));
  const opticalInput = Boolean(body.input_is_optical_signal);
  const branching = numA(body, 'branching_density', 0.08, 0, 1, assumed);
  const memory = numA(body, 'memory_access_density', 0.12, 0, 1, assumed);
  const precisionScore = Math.max(0, 1 - Math.max(0, precision - 16) / 32);
  let score = matmul * 0.28 + nonlinear * 0.12 + precisionScore * 0.16 + (1 - branching) * 0.14 + (1 - memory) * 0.12 + 0.12;
  if (opticalInput) score += 0.06;
  score = Math.max(0, Math.min(1, score));
  const failureModes = [];
  if (precision > 24) failureModes.push('precision_mismatch');
  if (branching > 0.45) failureModes.push('branching_density_high');
  if (memory > 0.5) failureModes.push('memory_access_high');
  const decision = score >= 0.72 && failureModes.length === 0 ? 'PHOTONIC_NPU' : score >= 0.55 ? 'PHOTONIC_NPU_WITH_VERIFY' : 'GPU_OR_CPU';
  return {
    room: 'photonic-route-room',
    inputs: { matmul_fraction: matmul, nonlinear_op_fraction: nonlinear, precision_required_bits: precision, input_is_optical_signal: opticalInput, branching_density: branching, memory_access_density: memory },
    outputs: {
      fit_score: Number(score.toPrecision(6)),
      fit_class: score >= 0.72 ? 'strong' : score >= 0.55 ? 'conditional' : 'poor',
      decision,
      failure_modes: failureModes,
      hardware_claim: 'simulated',
    },
  };
}

function calculate(room, body, assumed) {
  if (room === 'interference-room') return interferenceCalc(body, assumed);
  if (room === 'refraction-room') return refractionCalc(body, assumed);
  if (room === 'optical-switch-room') return opticalSwitchCalc(body, assumed);
  if (room === 'photonic-route-room') return photonicRouteCalc(body, assumed);
  return fiberCalc(body, assumed);
}

function flags(calc, assumed) {
  const out = [];
  if (calc.room === 'fiber-room') {
    if (calc.outputs.total_loss_db > 20) out.push('Fiber loss is high; receiver sensitivity or amplification must be modeled.');
    if (calc.outputs.dispersion_broadening_ps > 1000) out.push('Dispersion broadening is large; add compensation or lower linewidth.');
  }
  if (calc.room === 'photonic-route-room' && calc.outputs.hardware_claim === 'simulated') {
    out.push('Photonic route is a simulator decision, not measured hardware performance.');
  }
  if (calc.room === 'optical-switch-room') {
    out.push('Optical switch mode is a screen; full fixed-point simulation lives in the Python optical transistor model.');
  }
  if (assumed.length) out.push(`Assumed/clamped ${assumed.length} input(s); see math.assumed.`);
  if (!out.length) out.push('Inputs are in range for a first-pass educational/engineering receipt.');
  return out;
}

module.exports = async function handler(req, res) {
  setCors(res);
  if (req.method === 'OPTIONS') return res.status(204).end();
  if (req.method !== 'POST') return res.status(405).json({ ok: false, error: 'POST required' });

  try {
    const body = await readBody(req);
    const concept = String(body.concept || 'fiber waveguide propagation receipt').trim();
    const room = inferRoom(body);
    const assumed = [];
    const calc = calculate(room, body, assumed);
    const receiptInput = { concept, room, inputs: calc.inputs, outputs: calc.outputs };
    const result = {
      ok: true,
      schema_version: 'aethermoore_ai_waves_lab_v1',
      product: 'AI Waves Lab',
      receipt_id: `waves_${sha(JSON.stringify(receiptInput)).slice(0, 16)}`,
      concept,
      room: calc.room,
      math: {
        source_basis: ['waves_optics.py formula port', 'photonic accelerator routing heuristic', 'materials/waves research packet'],
        assumed,
        inputs: calc.inputs,
        outputs: calc.outputs,
      },
      visual_stage: {
        panels: ['wave canvas', 'ray path', 'signal metrics', 'receipt'],
        draw_hints: calc.room === 'fiber-room'
          ? ['fiber core', 'wave train', 'attenuation fade', 'dispersion spread']
          : ['wavefronts', 'phase marker', 'output meter', 'validity label'],
      },
      risk_flags: flags(calc, assumed),
      sellable_output: {
        offer: 'Wave, fiber, optics, and photonic-route receipt with visuals, assumptions, and limits.',
        starter_price: '$49 wave concept report or $199 lab worksheet pack',
      },
    };
    return res.status(200).json(result);
  } catch (error) {
    return res.status(500).json({ ok: false, error: error && error.message ? error.message : String(error) });
  }
};
