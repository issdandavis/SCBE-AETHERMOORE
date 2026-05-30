/**
 * @file polly-brief.ts
 * @module agent-bus/polly-brief
 * @layer Operator interface
 * @component Polly Brief — station status narrator and CLI brief renderer
 *
 * Polly is deliberately read-only. It does not repair, route, execute, or mutate
 * station state. It turns StationManifest, KeeperSweepResult/KeeperRunResult,
 * and DamageReport records into structured operator briefs plus stable CLI text.
 */

import { reportDamage, summarizeStation } from './station-manifest.js';
import type {
  DamageReport,
  HealthColor,
  KeeperSweepResult,
  StationManifest,
  StationSummary,
} from './station-manifest.js';
import type { KeeperRunResult, KeeperStatus } from './keeper-agent.js';

export type PollyBriefMode = 'status' | 'watch' | 'damage' | 'handoff';

export type PollyBriefSeverity = 'info' | 'notice' | 'warning' | 'critical';

export interface PollyAlert {
  id: string;
  severity: PollyBriefSeverity;
  source: 'station' | 'keeper' | 'damage';
  title: string;
  detail: string;
  zone_ids: string[];
}

export interface PollyAction {
  id: string;
  priority: PollyBriefSeverity;
  command: string;
  reason: string;
  requires_human: boolean;
}

export interface PollyBrief {
  schema_version: 'scbe_polly_brief_v1';
  station_id: string;
  generated_at: string;
  mode: PollyBriefMode;
  health: HealthColor;
  headline: string;
  summary: StationSummary;
  damage: DamageReport;
  keeper?: {
    keeper_id?: string;
    last_sweep?: string;
    zones_repaired: number;
    zones_escalated: number;
    open_escalations?: number;
    queued_repairs?: number;
  };
  alerts: PollyAlert[];
  actions: PollyAction[];
  cli_lines: string[];
}

export interface PollyBriefOptions {
  now?: string;
  mode?: PollyBriefMode;
  sweep?: KeeperSweepResult;
  keeperRun?: KeeperRunResult;
  keeperStatus?: KeeperStatus;
  damage?: DamageReport;
  maxAlerts?: number;
  maxActions?: number;
}

const SEVERITY_RANK: Record<PollyBriefSeverity, number> = {
  info: 0,
  notice: 1,
  warning: 2,
  critical: 3,
};

const HEALTH_TO_SEVERITY: Record<HealthColor, PollyBriefSeverity> = {
  green: 'info',
  amber: 'notice',
  red: 'warning',
  critical: 'critical',
};

function sortBySeverity<
  T extends { priority?: PollyBriefSeverity; severity?: PollyBriefSeverity; id: string },
>(items: T[]): T[] {
  return [...items].sort((a, b) => {
    const sa = a.priority ?? a.severity ?? 'info';
    const sb = b.priority ?? b.severity ?? 'info';
    const delta = SEVERITY_RANK[sb] - SEVERITY_RANK[sa];
    return delta === 0 ? a.id.localeCompare(b.id) : delta;
  });
}

function unique(values: string[]): string[] {
  return [...new Set(values.filter(Boolean))];
}

export function buildPollyAlerts(
  summary: StationSummary,
  damage: DamageReport,
  sweep?: KeeperSweepResult,
  keeperRun?: KeeperRunResult
): PollyAlert[] {
  const alerts: PollyAlert[] = [];

  if (damage.overall_health !== 'green') {
    alerts.push({
      id: 'damage.overall-health',
      severity: HEALTH_TO_SEVERITY[damage.overall_health],
      source: 'damage',
      title: `station health ${damage.overall_health}`,
      detail: `${damage.critical_zones.length} critical zone(s), ${damage.isolated_zones.length} isolated zone(s), ${damage.security_breaches.length} security breach(es)`,
      zone_ids: unique([...damage.critical_zones, ...damage.isolated_zones]),
    });
  }

  if (damage.security_breaches.length > 0) {
    alerts.push({
      id: 'damage.security-breaches',
      severity: 'critical',
      source: 'damage',
      title: 'security boundary conflict',
      detail: `${damage.security_breaches.length} clearance/boundary conflict(s) detected`,
      zone_ids: [],
    });
  }

  if (summary.fog_of_war_count > 0) {
    alerts.push({
      id: 'station.fog-of-war',
      severity: 'notice',
      source: 'station',
      title: 'fog of war remains',
      detail: `${summary.fog_of_war_count} zone(s) have not been observed`,
      zone_ids: [],
    });
  }

  const activeSweep = keeperRun?.sweep ?? sweep;
  if (activeSweep && activeSweep.escalations.length > 0) {
    alerts.push({
      id: 'keeper.escalations',
      severity: 'warning',
      source: 'keeper',
      title: 'keeper escalation required',
      detail: `${activeSweep.escalations.length} zone(s) need operator or governance review`,
      zone_ids: activeSweep.escalations,
    });
  }

  if (keeperRun && keeperRun.zones_repaired > 0) {
    alerts.push({
      id: 'keeper.repairs-applied',
      severity: 'info',
      source: 'keeper',
      title: 'keeper repairs applied',
      detail: `${keeperRun.zones_repaired} zone(s) repaired this sweep`,
      zone_ids: keeperRun.repairs.filter((r) => r.applied).map((r) => r.action.zone_id),
    });
  }

  return sortBySeverity(alerts);
}

export function buildPollyActions(
  summary: StationSummary,
  damage: DamageReport,
  sweep?: KeeperSweepResult,
  keeperRun?: KeeperRunResult
): PollyAction[] {
  const actions: PollyAction[] = [];
  const activeSweep = keeperRun?.sweep ?? sweep;

  if (damage.security_breaches.length > 0) {
    actions.push({
      id: 'action.security-review',
      priority: 'critical',
      command: 'scbe station damage --review-security',
      reason: 'security boundary conflicts require operator review before further execution',
      requires_human: true,
    });
  }

  if (damage.critical_zones.length > 0) {
    actions.push({
      id: 'action.inspect-critical-zones',
      priority: 'warning',
      command: `scbe station inspect --zones ${damage.critical_zones.join(',')}`,
      reason: 'critical zones are quarantined or offline',
      requires_human: true,
    });
  }

  if (activeSweep && activeSweep.repair_actions.length > 0) {
    actions.push({
      id: 'action.keeper-sweep',
      priority: activeSweep.escalations.length > 0 ? 'warning' : 'notice',
      command: 'scbe keeper sweep --dry-run',
      reason: `${activeSweep.repair_actions.length} keeper repair action(s) are available`,
      requires_human: false,
    });
  }

  if (damage.isolated_zones.length > 0) {
    actions.push({
      id: 'action.add-transit',
      priority: 'notice',
      command: `scbe station transit plan --repair ${damage.isolated_zones.join(',')}`,
      reason: 'isolated active zones reduce route reliability',
      requires_human: true,
    });
  }

  if (summary.fog_of_war_count > 0) {
    actions.push({
      id: 'action.observe-fog',
      priority: 'info',
      command: 'scbe station observe --fog',
      reason: 'unobserved zones reduce operator confidence',
      requires_human: false,
    });
  }

  if (actions.length === 0) {
    actions.push({
      id: 'action.hold-green',
      priority: 'info',
      command: 'scbe polly watch',
      reason: 'station is green; continue passive watch',
      requires_human: false,
    });
  }

  return sortBySeverity(actions);
}

export function buildPollyHeadline(
  summary: StationSummary,
  damage: DamageReport,
  alerts: PollyAlert[]
): string {
  if (damage.overall_health === 'critical') {
    return `Critical station damage: ${damage.critical_zones.length} critical zone(s)`;
  }
  if (damage.overall_health === 'red') {
    return `Station needs review: ${damage.critical_zones.length} critical zone(s), ${damage.security_breaches.length} security conflict(s)`;
  }
  if (alerts.some((a) => a.severity === 'warning')) {
    return `Station is operational with ${alerts.filter((a) => a.severity === 'warning').length} warning(s)`;
  }
  if (summary.fog_of_war_count > 0) {
    return `Station is operational; ${summary.fog_of_war_count} zone(s) remain unobserved`;
  }
  return `Station ${summary.station_id} is green`;
}

export function renderPollyCliLines(brief: Omit<PollyBrief, 'cli_lines'>): string[] {
  const lines = [
    `Polly ${brief.mode}: ${brief.headline}`,
    `health=${brief.health} zones=${brief.summary.total_zones} active=${brief.summary.active_zones} docked=${brief.summary.total_agents_docked} routes=${brief.summary.available_routes}`,
  ];

  if (brief.keeper) {
    lines.push(
      `keeper=${brief.keeper.keeper_id ?? 'unknown'} repaired=${brief.keeper.zones_repaired} escalated=${brief.keeper.zones_escalated} open=${brief.keeper.open_escalations ?? 0} queued=${brief.keeper.queued_repairs ?? 0}`
    );
  }

  if (brief.alerts.length > 0) {
    lines.push('alerts:');
    for (const alert of brief.alerts) {
      const zones = alert.zone_ids.length > 0 ? ` zones=${alert.zone_ids.join(',')}` : '';
      lines.push(`- [${alert.severity}] ${alert.title}: ${alert.detail}${zones}`);
    }
  }

  lines.push('next:');
  for (const action of brief.actions) {
    const gate = action.requires_human ? 'human' : 'auto';
    lines.push(`- [${action.priority}/${gate}] ${action.command} # ${action.reason}`);
  }

  return lines;
}

export function buildPollyBrief(
  manifest: StationManifest,
  opts: PollyBriefOptions = {}
): PollyBrief {
  const now = opts.now ?? new Date().toISOString();
  const mode = opts.mode ?? 'status';
  const sweep = opts.keeperRun?.sweep ?? opts.sweep;
  const summary = summarizeStation(manifest, sweep, { now });
  const damage = opts.damage ?? reportDamage(manifest, { now });
  const maxAlerts = opts.maxAlerts ?? 8;
  const maxActions = opts.maxActions ?? 6;

  const alerts = buildPollyAlerts(summary, damage, sweep, opts.keeperRun).slice(0, maxAlerts);
  const actions = buildPollyActions(summary, damage, sweep, opts.keeperRun).slice(0, maxActions);
  const headline = buildPollyHeadline(summary, damage, alerts);

  const keeper =
    opts.keeperRun || opts.keeperStatus
      ? {
          keeper_id: opts.keeperRun?.keeper_id ?? opts.keeperStatus?.keeper_id,
          last_sweep: opts.keeperRun?.run_at ?? opts.keeperStatus?.last_sweep,
          zones_repaired: opts.keeperRun?.zones_repaired ?? 0,
          zones_escalated: opts.keeperRun?.zones_escalated ?? 0,
          open_escalations: opts.keeperStatus?.open_escalations,
          queued_repairs: opts.keeperStatus?.queued_repairs,
        }
      : undefined;

  const partial: Omit<PollyBrief, 'cli_lines'> = {
    schema_version: 'scbe_polly_brief_v1',
    station_id: manifest.station_id,
    generated_at: now,
    mode,
    health: damage.overall_health,
    headline,
    summary,
    damage,
    keeper,
    alerts,
    actions,
  };

  return { ...partial, cli_lines: renderPollyCliLines(partial) };
}

export function renderPollyBrief(brief: PollyBrief): string {
  return brief.cli_lines.join('\n');
}

// ─── EVA compatibility aliases ────────────────────────────────────────────────

/** @deprecated Use PollyBriefMode */
export type EvaMode = PollyBriefMode;
/** @deprecated Use PollyBriefSeverity */
export type EvaSeverity = PollyBriefSeverity;
/** @deprecated Use PollyAlert */
export type EvaAlert = PollyAlert;
/** @deprecated Use PollyAction */
export type EvaAction = PollyAction;
/** @deprecated Use PollyBrief */
export type EvaBrief = PollyBrief;
/** @deprecated Use PollyBriefOptions */
export type EvaBriefOptions = PollyBriefOptions;

/** @deprecated Use buildPollyAlerts */
export const buildEvaAlerts = buildPollyAlerts;
/** @deprecated Use buildPollyActions */
export const buildEvaActions = buildPollyActions;
/** @deprecated Use buildPollyHeadline */
export const buildEvaHeadline = buildPollyHeadline;
/** @deprecated Use renderPollyCliLines */
export const renderEvaCliLines = renderPollyCliLines;
/** @deprecated Use buildPollyBrief */
export const buildEvaBrief = buildPollyBrief;
/** @deprecated Use renderPollyBrief */
export const renderEvaBrief = renderPollyBrief;
