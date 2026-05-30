import { describe, expect, it } from 'vitest';
import {
  classifyHermesTask,
  classifyScbeCompassTask,
  hermesModelLanes,
  planHermesRoute,
  planScbeCompassRoute,
  scbeCompassBoardRules,
  scbeCompassCommandTree,
  scbeCompassRollCards,
} from '../src/hermes.js';

describe('Hermes agentic CLI planner', () => {
  it('classifies compiler, writing, youtube, and model tasks', () => {
    expect(classifyHermesTask('cross-language compile with binary hex interpolation')).toBe(
      'compiler'
    );
    expect(classifyHermesTask('write a chapter draft')).toBe('writing');
    expect(classifyHermesTask('review YouTube upload metadata')).toBe('youtube');
    expect(classifyHermesTask('check ollama and huggingface model APIs')).toBe('model');
  });

  it('plans native SCBE Compass formations with adapter slots', () => {
    const plan = planScbeCompassRoute('cross-language compile with binary hex interpolation');

    expect(plan.schema_version).toBe('scbe.agent_bus.compass_route_plan.v1');
    expect(plan.command_surface).toBe('scbe-compass');
    expect(plan.mode).toBe('compiler');
    expect(plan.formation).toBe('forge');
    expect(plan.command_path).toBe('CA.forge.compiler');
    expect(plan.domain).toBe('CA');
    expect(plan.octree_context.octree_retrieval.surfaces).toContain(
      'octree spatial / structural retrieval'
    );
    expect(plan.formation_steps.map((step) => step.stage)).toContain('lift');
    expect(plan.adapter_slots).toContain(
      'IR adapter for MLIR-style dialect lowering into LatticeOp'
    );
    expect(plan.board_rules.flatMap((rule) => rule.source_paths)).toContain(
      'scripts/system/agentic_pazaak_board.py'
    );
    expect(plan.board_rules.flatMap((rule) => rule.source_paths)).toContain(
      'src/coding_board/pipeline.py'
    );
    expect(plan.cli_examples[0]).toContain('scbe-agent-bus compass plan');
  });

  it('anchors board mechanics to the real Pazaak, coding-board, octree, and chessboard files', () => {
    const rules = scbeCompassBoardRules('compiler');
    const sourcePaths = rules.flatMap((rule) => rule.source_paths);
    const schemas = rules.flatMap((rule) => rule.schemas);

    expect(rules.map((rule) => rule.mechanic)).toContain('pazaak-hand');
    expect(rules.map((rule) => rule.mechanic)).toContain('go-board-territory');
    expect(rules.map((rule) => rule.mechanic)).toContain('octree-sector');
    expect(rules.map((rule) => rule.mechanic)).toContain('chessboard-stack');
    expect(sourcePaths).toContain('scripts/system/agentic_pazaak_board.py');
    expect(sourcePaths).toContain('config/eval/agentic_pazaak_cards.v1.json');
    expect(sourcePaths).toContain('src/coding_board/probe.py');
    expect(sourcePaths).toContain('scripts/system/chessboard_dev_stack.py');
    expect(schemas).toContain('scbe_agentic_pazaak_board_report_v1');
    expect(schemas).toContain('scbe-coding-trial-v1');
  });

  it('exposes the Obsidian sphere-grid command hierarchy', () => {
    const tree = scbeCompassCommandTree();

    expect(tree.map((node) => node.path)).toContain('AV.broadcast.youtube');
    expect(tree.map((node) => node.path)).toContain('CA+UM.secure-computation');
    expect(tree.find((node) => node.path === 'DR.scribe.structure')?.formation).toBe('scribe');
  });

  it('keeps Hermes as a compatibility alias over the native compass classifier', () => {
    expect(classifyHermesTask('review YouTube upload metadata')).toBe(
      classifyScbeCompassTask('review YouTube upload metadata')
    );

    const aliasPlan = planHermesRoute('write a chapter draft');
    expect(aliasPlan.schema_version).toBe('scbe.agent_bus.hermes_route_plan.v1');
    expect(aliasPlan.cli_examples[0]).toContain('scbe-agent-bus hermes plan');
  });

  it('plans a local-first YouTube route with public-publish blocked', () => {
    const plan = planHermesRoute('make a YouTube upload from an article');

    expect(plan.schema_version).toBe('scbe.agent_bus.hermes_route_plan.v1');
    expect(plan.mode).toBe('youtube');
    expect(plan.primary_tools).toContain('youtube-video-review');
    expect(plan.governance.privacy).toBe('local_only');
    expect(plan.governance.budget_cents).toBe(0);
    expect(plan.governance.blocked_actions).toContain(
      'public YouTube publish without explicit approval'
    );
  });

  it('adds roll cards so weak/free models can follow governed automations', () => {
    const plan = planScbeCompassRoute('make a YouTube upload from an article');
    const cards = plan.roll_cards;
    const uploadCard = cards.find((card) => card.id === 'roll.youtube-upload-prep');

    expect(cards.map((card) => card.id)).toContain('roll.collect-human-input');
    expect(cards.map((card) => card.id)).toContain('roll.verify-output-contract');
    expect(uploadCard?.model_policy.free_first).toBe(true);
    expect(uploadCard?.model_policy.allowed_lanes).toContain('ollama');
    expect(uploadCard?.model_policy.allowed_lanes).toContain('huggingface');
    expect(uploadCard?.human_gate).toMatch(/Approve/);
    expect(uploadCard?.expected_output.required_fields).toContain('visibility');
    expect(uploadCard?.expected_output.acceptance).toContain('visibility is unlisted or draft');
  });

  it('exposes roll cards as a standalone API by mode', () => {
    const modelCards = scbeCompassRollCards('model');
    const dispatchCard = modelCards.find((card) => card.id === 'roll.free-model-dispatch');

    expect(dispatchCard?.kind).toBe('api-call');
    expect(dispatchCard?.model_policy.allowed_lanes).toEqual(['offline', 'ollama', 'huggingface']);
    expect(dispatchCard?.expected_output.acceptance).toContain(
      'No paid provider when budget_cents is 0'
    );
  });

  it('labels model lanes with real cost boundaries instead of unlimited-free claims', () => {
    const lanes = hermesModelLanes();

    expect(lanes.map((lane) => lane.costTier)).toContain('local-free-after-install');
    expect(lanes.map((lane) => lane.costTier)).toContain('remote-free-tier-limited');
    expect(lanes.find((lane) => lane.id === 'huggingface')?.notes).toMatch(/quota/i);
    expect(lanes.find((lane) => lane.id === 'ollama')?.notes).toMatch(/hardware/i);
  });
});
