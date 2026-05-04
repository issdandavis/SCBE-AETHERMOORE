import { api } from "encore.dev/api";
import { CronJob } from "encore.dev/cron";
import { createHash, randomUUID } from "node:crypto";
import {
  db,
  metricCountBySource,
  metricsArchive,
  metricsTopic,
  thirdPartyApiKey,
} from "./infra";

interface IngestMetricRequest {
  name: string;
  value: number;
  source: string;
  idempotencyKey?: string;
}

interface IngestMetricResponse {
  accepted: true;
  secretConfigured: boolean;
}

interface CleanupResponse {
  deletedRows: number;
}

export const ingestMetric = api(
  { expose: true, method: "POST", path: "/metrics/ingest" },
  async (req: IngestMetricRequest): Promise<IngestMetricResponse> => {
    if (!req.name.trim()) {
      throw new Error("name is required");
    }
    if (!req.source.trim()) {
      throw new Error("source is required");
    }

    const ts = new Date().toISOString();
    const source = req.source.trim().toLowerCase();
    const idempotencyKey = req.idempotencyKey?.trim() || null;
    const eventId = idempotencyKey
      ? createHash("sha256")
          .update(`${source}:${req.name}:${idempotencyKey}`)
          .digest("hex")
      : randomUUID();

    await metricsTopic.publish({
      eventId,
      name: req.name,
      value: req.value,
      source,
      ts,
      idempotencyKey,
    });

    await metricCountBySource.increment({ source }, 1);

    await metricsArchive.upload(
      `ingest/${source}/${Date.now()}.json`,
      Buffer.from(JSON.stringify({ ...req, source, ts })),
      { contentType: "application/json" },
    );

    const secretAccessorReady = typeof thirdPartyApiKey === "function";

    return {
      accepted: true,
      secretConfigured: secretAccessorReady,
    };
  },
);

export const cleanupStaleMetrics = api(
  { expose: false, method: "POST", path: "/internal/metrics/cleanup" },
  async (): Promise<CleanupResponse> => {
    const res = await db.queryRow<{ count: number }>`
      SELECT COUNT(*)::int AS count
      FROM metric_events
      WHERE ts < NOW() - INTERVAL '30 days'
    `;
    const deletedRows = res?.count ?? 0;

    await db.exec`
      DELETE FROM metric_events
      WHERE ts < NOW() - INTERVAL '30 days'
    `;

    return { deletedRows };
  },
);

const _cleanupCron = new CronJob("metrics-cleanup-hourly", {
  title: "Clean stale metric rows every hour",
  every: "1h",
  endpoint: cleanupStaleMetrics,
});
