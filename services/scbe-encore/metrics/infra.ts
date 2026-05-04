import { secret } from "encore.dev/config";
import { Topic, Subscription } from "encore.dev/pubsub";
import { CacheCluster, IntKeyspace, expireIn } from "encore.dev/storage/cache";
import { Bucket } from "encore.dev/storage/objects";
import { SQLDatabase } from "encore.dev/storage/sqldb";

export interface MetricEvent {
  eventId: string;
  name: string;
  value: number;
  source: string;
  ts: string;
  idempotencyKey: string | null;
}

export const db = new SQLDatabase("scbe-metrics", {
  migrations: "./migrations",
});

export const metricsTopic = new Topic<MetricEvent>("metrics-events", {
  deliveryGuarantee: "at-least-once",
});

const _eventSink = new Subscription(metricsTopic, "persist-metric-event", {
  handler: async (event) => {
    await db.exec`
      INSERT INTO metric_events (event_id, idempotency_key, name, value, source, ts)
      VALUES (
        ${event.eventId},
        ${event.idempotencyKey},
        ${event.name},
        ${event.value},
        ${event.source},
        ${event.ts}::timestamptz
      )
      ON CONFLICT (event_id) DO NOTHING
    `;
  },
});

const cache = new CacheCluster("scbe-metrics-cache", {
  evictionPolicy: "allkeys-lru",
});

export const metricCountBySource = new IntKeyspace<{ source: string }>(cache, {
  keyPattern: "metrics/source/:source/count",
  defaultExpiry: expireIn(24 * 60 * 60 * 1000),
});

export const metricsArchive = new Bucket("scbe-metrics-archive", {
  versioned: false,
});

export const thirdPartyApiKey = secret("SCBEThirdPartyApiKey");
