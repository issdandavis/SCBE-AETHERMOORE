import crypto from "crypto";
import { storage } from "../storage";
import type { ZapierWebhook, InsertZapierWebhookLog } from "@shared/schema";

export type ZapierEventType = 
  | "user.created"
  | "project.created"
  | "agent_run.completed"
  | "roundtable.message"
  | "workflow.completed"
  | "integration.connected";

const MAX_RETRIES = 3;
const INITIAL_RETRY_DELAY_MS = 1000;

interface WebhookPayload {
  event: ZapierEventType;
  timestamp: string;
  data: Record<string, unknown>;
}

function signPayload(payload: string, secretKey: string): string {
  return crypto.createHmac("sha256", secretKey).update(payload).digest("hex");
}

async function deliverWebhook(
  webhook: ZapierWebhook,
  payload: WebhookPayload,
  retryCount: number = 0
): Promise<{ success: boolean; statusCode?: number; body?: string; error?: string }> {
  const payloadString = JSON.stringify(payload);
  const signature = signPayload(payloadString, webhook.secretKey);

  try {
    const response = await fetch(webhook.targetUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Zapier-Signature": signature,
        "X-Zapier-Event": payload.event,
        "X-Zapier-Timestamp": payload.timestamp,
      },
      body: payloadString,
    });

    const bodyText = await response.text().catch(() => "");

    if (response.ok) {
      return { success: true, statusCode: response.status, body: bodyText };
    }

    if (response.status >= 500 && retryCount < MAX_RETRIES) {
      const delay = INITIAL_RETRY_DELAY_MS * Math.pow(2, retryCount);
      await new Promise((resolve) => setTimeout(resolve, delay));
      return deliverWebhook(webhook, payload, retryCount + 1);
    }

    return { success: false, statusCode: response.status, body: bodyText };
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    
    if (retryCount < MAX_RETRIES) {
      const delay = INITIAL_RETRY_DELAY_MS * Math.pow(2, retryCount);
      await new Promise((resolve) => setTimeout(resolve, delay));
      return deliverWebhook(webhook, payload, retryCount + 1);
    }

    return { success: false, error: errorMessage };
  }
}

async function logDelivery(
  webhookId: string,
  event: string,
  payload: WebhookPayload,
  result: { success: boolean; statusCode?: number; body?: string; error?: string }
): Promise<void> {
  try {
    const logData: InsertZapierWebhookLog = {
      webhookId,
      event,
      payload,
      responseStatus: result.statusCode ?? null,
      responseBody: result.body ?? null,
      success: result.success,
      errorMessage: result.error ?? null,
    };
    await storage.createZapierWebhookLog(logData);
  } catch (err) {
    console.error("[ZapierService] Failed to log webhook delivery:", err);
  }
}

export async function dispatchEvent(
  orgId: string,
  event: ZapierEventType,
  data: Record<string, unknown>
): Promise<{ dispatched: number; succeeded: number; failed: number }> {
  const webhooks = await storage.getZapierWebhooksByEvent(orgId, event);
  const activeWebhooks = webhooks.filter((w) => w.isActive);

  if (activeWebhooks.length === 0) {
    return { dispatched: 0, succeeded: 0, failed: 0 };
  }

  const payload: WebhookPayload = {
    event,
    timestamp: new Date().toISOString(),
    data,
  };

  let succeeded = 0;
  let failed = 0;

  const deliveryPromises = activeWebhooks.map(async (webhook) => {
    const result = await deliverWebhook(webhook, payload);
    await logDelivery(webhook.id, event, payload, result);

    if (result.success) {
      succeeded++;
      await storage.updateZapierWebhook(webhook.id, {
        lastTriggeredAt: new Date(),
        triggerCount: webhook.triggerCount + 1,
      });
    } else {
      failed++;
    }
  });

  await Promise.allSettled(deliveryPromises);

  return { dispatched: activeWebhooks.length, succeeded, failed };
}

export function generateSecretKey(): string {
  return crypto.randomBytes(32).toString("hex");
}

export function verifySignature(payload: string, signature: string, secretKey: string): boolean {
  const expectedSignature = signPayload(payload, secretKey);
  return crypto.timingSafeEqual(
    Buffer.from(signature, "hex"),
    Buffer.from(expectedSignature, "hex")
  );
}

export const SUPPORTED_EVENTS: ZapierEventType[] = [
  "user.created",
  "project.created",
  "agent_run.completed",
  "roundtable.message",
  "workflow.completed",
  "integration.connected",
];

export function getSampleData(event: ZapierEventType): Record<string, unknown> {
  const samples: Record<ZapierEventType, Record<string, unknown>> = {
    "user.created": {
      id: "usr_sample123",
      email: "user@example.com",
      role: "member",
      createdAt: new Date().toISOString(),
    },
    "project.created": {
      id: "prj_sample123",
      name: "Sample Project",
      orgId: "org_sample123",
      createdAt: new Date().toISOString(),
    },
    "agent_run.completed": {
      id: "run_sample123",
      projectId: "prj_sample123",
      status: "completed",
      provider: "openai",
      model: "gpt-4o",
      costEstimate: "0.0250",
      createdAt: new Date().toISOString(),
    },
    "roundtable.message": {
      id: "msg_sample123",
      sessionId: "ses_sample123",
      senderType: "ai",
      provider: "openai",
      model: "gpt-4o",
      content: "This is a sample AI response in the roundtable discussion.",
      sequenceNumber: 1,
      createdAt: new Date().toISOString(),
    },
    "workflow.completed": {
      id: "wf_sample123",
      workflowId: "wfl_sample123",
      name: "Sample Workflow",
      status: "completed",
      startedAt: new Date().toISOString(),
      completedAt: new Date().toISOString(),
    },
    "integration.connected": {
      id: "int_sample123",
      orgId: "org_sample123",
      provider: "github",
      status: "connected",
      createdAt: new Date().toISOString(),
    },
  };

  return samples[event] || {};
}
