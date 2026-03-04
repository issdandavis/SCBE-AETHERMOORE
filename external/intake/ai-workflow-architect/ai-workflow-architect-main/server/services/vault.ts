import crypto from "crypto";
import { storage } from "../storage";

const ALGORITHM = "aes-256-gcm";
const KEY_LENGTH = 32;
const IV_LENGTH = 16;
const SALT = "ai-orchestration-vault-v1";

function getEncryptionKey(): Buffer {
  const masterSecret = process.env.SESSION_SECRET;
  if (!masterSecret) {
    throw new Error("SESSION_SECRET is required for credential encryption");
  }
  return crypto.pbkdf2Sync(masterSecret, SALT, 100000, KEY_LENGTH, "sha512");
}

export function encryptCredential(plaintext: string): {
  encryptedKey: string;
  iv: string;
  authTag: string;
} {
  const key = getEncryptionKey();
  const iv = crypto.randomBytes(IV_LENGTH);
  const cipher = crypto.createCipheriv(ALGORITHM, key, iv);

  let encrypted = cipher.update(plaintext, "utf8", "base64");
  encrypted += cipher.final("base64");

  const authTag = cipher.getAuthTag();

  return {
    encryptedKey: encrypted,
    iv: iv.toString("base64"),
    authTag: authTag.toString("base64"),
  };
}

export function decryptCredential(
  encryptedKey: string,
  iv: string,
  authTag: string
): string {
  const key = getEncryptionKey();
  const decipher = crypto.createDecipheriv(
    ALGORITHM,
    key,
    Buffer.from(iv, "base64")
  );
  decipher.setAuthTag(Buffer.from(authTag, "base64"));

  let decrypted = decipher.update(encryptedKey, "base64", "utf8");
  decrypted += decipher.final("utf8");

  return decrypted;
}

export interface ProviderConfig {
  name: string;
  label: string;
  keyPrefix: string;
  testEndpoint?: string;
}

export const SUPPORTED_PROVIDERS: ProviderConfig[] = [
  { name: "openai", label: "OpenAI", keyPrefix: "sk-" },
  { name: "anthropic", label: "Anthropic", keyPrefix: "sk-ant-" },
  { name: "perplexity", label: "Perplexity", keyPrefix: "pplx-" },
  { name: "xai", label: "xAI / Grok", keyPrefix: "xai-" },
  { name: "github", label: "GitHub", keyPrefix: "ghp_" },
  { name: "google", label: "Google AI", keyPrefix: "AI" },
];

export async function storeUserCredential(
  userId: string,
  provider: string,
  apiKey: string,
  label?: string
): Promise<{ id: string; provider: string; label: string | null }> {
  const { encryptedKey, iv, authTag } = encryptCredential(apiKey);

  const existingCreds = await storage.getUserCredentialsByProvider(userId, provider);
  if (existingCreds) {
    const updated = await storage.updateUserCredential(existingCreds.id, {
      encryptedKey,
      iv,
      authTag,
      label: label || existingCreds.label,
    });
    return { id: updated.id, provider: updated.provider, label: updated.label };
  }

  const credential = await storage.createUserCredential({
    userId,
    provider,
    encryptedKey,
    iv,
    authTag,
    label: label || null,
  });

  return { id: credential.id, provider: credential.provider, label: credential.label };
}

export async function getUserCredential(
  userId: string,
  provider: string
): Promise<string | null> {
  const credential = await storage.getUserCredentialsByProvider(userId, provider);
  if (!credential) {
    return null;
  }

  const decrypted = decryptCredential(
    credential.encryptedKey,
    credential.iv,
    credential.authTag
  );

  await storage.updateCredentialLastUsed(credential.id);

  return decrypted;
}

export async function listUserCredentials(
  userId: string
): Promise<Array<{ id: string; provider: string; label: string | null; lastUsedAt: Date | null; createdAt: Date }>> {
  const credentials = await storage.getUserCredentials(userId);
  return credentials.map((c) => ({
    id: c.id,
    provider: c.provider,
    label: c.label,
    lastUsedAt: c.lastUsedAt,
    createdAt: c.createdAt,
  }));
}

export async function deleteUserCredential(
  userId: string,
  credentialId: string
): Promise<boolean> {
  const credential = await storage.getUserCredentialById(credentialId);
  if (!credential || credential.userId !== userId) {
    return false;
  }
  await storage.deleteUserCredential(credentialId);
  return true;
}

export function maskApiKey(apiKey: string): string {
  if (apiKey.length <= 8) {
    return "****";
  }
  return apiKey.slice(0, 4) + "****" + apiKey.slice(-4);
}

export function validateApiKeyFormat(provider: string, apiKey: string): boolean {
  const config = SUPPORTED_PROVIDERS.find((p) => p.name === provider);
  if (!config) {
    return apiKey.length >= 10;
  }
  return apiKey.startsWith(config.keyPrefix) && apiKey.length >= 10;
}

export async function testApiKey(
  provider: string,
  apiKey: string
): Promise<{ valid: boolean; error?: string; models?: string[] }> {
  try {
    switch (provider.toLowerCase()) {
      case "openai": {
        const response = await fetch("https://api.openai.com/v1/models", {
          headers: { Authorization: `Bearer ${apiKey}` },
        });
        if (response.ok) {
          const data = await response.json();
          const models = data.data?.slice(0, 5).map((m: any) => m.id) || [];
          return { valid: true, models };
        }
        const error = await response.json().catch(() => ({}));
        return { valid: false, error: error.error?.message || `HTTP ${response.status}` };
      }

      case "anthropic": {
        const response = await fetch("https://api.anthropic.com/v1/messages", {
          method: "POST",
          headers: {
            "x-api-key": apiKey,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            model: "claude-3-haiku-20240307",
            max_tokens: 1,
            messages: [{ role: "user", content: "Hi" }],
          }),
        });
        if (response.ok) {
          return { valid: true, models: ["claude-3-opus", "claude-3-sonnet", "claude-3-haiku"] };
        }
        const errorData = await response.json().catch(() => ({}));
        if (response.status === 401) {
          return { valid: false, error: "Invalid API key" };
        }
        if (response.status === 429) {
          return { valid: false, error: "Rate limited - please try again" };
        }
        return { valid: false, error: errorData.error?.message || `HTTP ${response.status}` };
      }

      case "perplexity": {
        const response = await fetch("https://api.perplexity.ai/chat/completions", {
          method: "POST",
          headers: {
            Authorization: `Bearer ${apiKey}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            model: "llama-3.1-sonar-small-128k-online",
            messages: [{ role: "user", content: "test" }],
            max_tokens: 1,
          }),
        });
        if (response.ok) {
          return { valid: true, models: ["llama-3.1-sonar-small", "llama-3.1-sonar-large"] };
        }
        const errorData = await response.json().catch(() => ({}));
        if (response.status === 401) {
          return { valid: false, error: "Invalid API key" };
        }
        if (response.status === 429) {
          return { valid: false, error: "Rate limited - please try again" };
        }
        return { valid: false, error: errorData.error?.message || `HTTP ${response.status}` };
      }

      case "xai": {
        const response = await fetch("https://api.x.ai/v1/models", {
          headers: { Authorization: `Bearer ${apiKey}` },
        });
        if (response.ok) {
          return { valid: true, models: ["grok-beta", "grok-2"] };
        }
        const errorData = await response.json().catch(() => ({}));
        if (response.status === 401) {
          return { valid: false, error: "Invalid API key" };
        }
        if (response.status === 429) {
          return { valid: false, error: "Rate limited - please try again" };
        }
        return { valid: false, error: errorData.error?.message || `HTTP ${response.status}` };
      }

      case "google": {
        const response = await fetch(
          `https://generativelanguage.googleapis.com/v1beta/models?key=${apiKey}`
        );
        if (response.ok) {
          const data = await response.json();
          const models = data.models?.slice(0, 5).map((m: any) => m.name.split("/").pop()) || [];
          return { valid: true, models };
        }
        const errorData = await response.json().catch(() => ({}));
        if (response.status === 400 || response.status === 401) {
          return { valid: false, error: "Invalid API key" };
        }
        if (response.status === 429) {
          return { valid: false, error: "Rate limited - please try again" };
        }
        return { valid: false, error: errorData.error?.message || `HTTP ${response.status}` };
      }

      default:
        return { valid: false, error: "Unknown provider" };
    }
  } catch (error) {
    return { valid: false, error: error instanceof Error ? error.message : "Connection failed" };
  }
}
