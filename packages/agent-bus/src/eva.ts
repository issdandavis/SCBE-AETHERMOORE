/**
 * @file eva.ts
 * @module agent-bus/eva
 * @deprecated Use polly-operator.ts. EVA remains as a compatibility alias.
 */

export {
  type PollyOperatorMode as EvaMode,
  type PollySeverity as EvaSeverity,
  type PollyOperatorAlert as EvaAlert,
  type PollyOperatorAction as EvaAction,
  type PollyOperatorBrief as EvaBrief,
  type PollyOperatorBriefOptions as EvaBriefOptions,
  buildPollyOperatorAlerts as buildEvaAlerts,
  buildPollyOperatorActions as buildEvaActions,
  buildPollyOperatorHeadline as buildEvaHeadline,
  renderPollyOperatorCliLines as renderEvaCliLines,
  buildPollyOperatorBrief as buildEvaBrief,
  renderPollyOperatorBrief as renderEvaBrief,
} from './polly-operator.js';
