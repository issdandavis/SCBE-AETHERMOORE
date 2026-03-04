import { sql } from "drizzle-orm";
import { pgTable, text, varchar, timestamp, integer, jsonb, decimal, boolean, index } from "drizzle-orm/pg-core";
import { createInsertSchema, createSelectSchema } from "drizzle-zod";
import { z } from "zod";

// Sessions table for connect-pg-simple (Replit Auth)
export const sessions = pgTable(
  "sessions",
  {
    sid: varchar("sid").primaryKey(),
    sess: jsonb("sess").notNull(),
    expire: timestamp("expire").notNull(),
  },
  (table) => [index("IDX_session_expire").on(table.expire)],
);

// Users table with RBAC
export const users = pgTable("users", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  email: text("email").notNull().unique(),
  passwordHash: text("password_hash").notNull(),
  role: text("role", { enum: ["owner", "admin", "member", "viewer"] }).notNull().default("member"),
  firstName: varchar("first_name"),
  lastName: varchar("last_name"),
  profileImageUrl: varchar("profile_image_url"),
  failedAttempts: integer("failed_attempts").notNull().default(0),
  lockedUntil: timestamp("locked_until"),
  createdAt: timestamp("created_at").notNull().defaultNow(),
});

export const insertUserSchema = createInsertSchema(users).omit({
  id: true,
  createdAt: true,
});

export type InsertUser = z.infer<typeof insertUserSchema>;
export type User = typeof users.$inferSelect;
export type UserRole = User["role"];

// Type for upserting user from OAuth (Replit Auth)
export type UpsertUser = {
  id: string;
  email: string | null;
  firstName: string | null;
  lastName: string | null;
  profileImageUrl: string | null;
};

// Organizations
export const orgs = pgTable("orgs", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  name: text("name").notNull(),
  ownerUserId: varchar("owner_user_id").notNull().references(() => users.id),
  createdAt: timestamp("created_at").notNull().defaultNow(),
});

export const insertOrgSchema = createInsertSchema(orgs).omit({
  id: true,
  createdAt: true,
});

export type InsertOrg = z.infer<typeof insertOrgSchema>;
export type Org = typeof orgs.$inferSelect;

// Projects
export const projects = pgTable("projects", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  orgId: varchar("org_id").notNull().references(() => orgs.id, { onDelete: "cascade" }),
  name: text("name").notNull(),
  createdAt: timestamp("created_at").notNull().defaultNow(),
});

export const insertProjectSchema = createInsertSchema(projects).omit({
  id: true,
  createdAt: true,
});

export type InsertProject = z.infer<typeof insertProjectSchema>;
export type Project = typeof projects.$inferSelect;

// Integrations
export const integrations = pgTable("integrations", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  orgId: varchar("org_id").notNull().references(() => orgs.id, { onDelete: "cascade" }),
  provider: text("provider").notNull(), // openai, anthropic, github, etc.
  status: text("status", { enum: ["connected", "syncing", "disconnected", "error"] }).notNull().default("disconnected"),
  metadataJson: jsonb("metadata_json"), // provider-specific config
  createdAt: timestamp("created_at").notNull().defaultNow(),
  updatedAt: timestamp("updated_at").notNull().defaultNow(),
});

export const insertIntegrationSchema = createInsertSchema(integrations).omit({
  id: true,
  createdAt: true,
  updatedAt: true,
});

export type InsertIntegration = z.infer<typeof insertIntegrationSchema>;
export type Integration = typeof integrations.$inferSelect;

// Secret references (not actual secrets - just pointers to Replit Secrets)
export const secretsRef = pgTable("secrets_ref", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  orgId: varchar("org_id").notNull().references(() => orgs.id, { onDelete: "cascade" }),
  provider: text("provider").notNull(),
  secretName: text("secret_name").notNull(), // e.g., "OPENAI_API_KEY"
  scopesJson: jsonb("scopes_json"), // provider-specific scopes
  createdAt: timestamp("created_at").notNull().defaultNow(),
});

export const insertSecretRefSchema = createInsertSchema(secretsRef).omit({
  id: true,
  createdAt: true,
});

export type InsertSecretRef = z.infer<typeof insertSecretRefSchema>;
export type SecretRef = typeof secretsRef.$inferSelect;

// Agent runs
export const agentRuns = pgTable("agent_runs", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  projectId: varchar("project_id").notNull().references(() => projects.id, { onDelete: "cascade" }),
  status: text("status", { enum: ["queued", "running", "completed", "failed", "cancelled", "awaiting_approval"] }).notNull().default("queued"),
  model: text("model").notNull(),
  provider: text("provider").notNull(),
  inputJson: jsonb("input_json"),
  outputJson: jsonb("output_json"),
  costEstimate: decimal("cost_estimate", { precision: 10, scale: 4 }),
  createdAt: timestamp("created_at").notNull().defaultNow(),
});

export const insertAgentRunSchema = createInsertSchema(agentRuns).omit({
  id: true,
  createdAt: true,
});

export type InsertAgentRun = z.infer<typeof insertAgentRunSchema>;
export type AgentRun = typeof agentRuns.$inferSelect;

// Messages
export const messages = pgTable("messages", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  projectId: varchar("project_id").notNull().references(() => projects.id, { onDelete: "cascade" }),
  agentRunId: varchar("agent_run_id").references(() => agentRuns.id, { onDelete: "cascade" }),
  role: text("role", { enum: ["user", "assistant", "system", "orchestrator"] }).notNull(),
  content: text("content").notNull(),
  createdAt: timestamp("created_at").notNull().defaultNow(),
});

export const insertMessageSchema = createInsertSchema(messages).omit({
  id: true,
  createdAt: true,
});

export type InsertMessage = z.infer<typeof insertMessageSchema>;
export type Message = typeof messages.$inferSelect;

// Memory items
export const memoryItems = pgTable("memory_items", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  projectId: varchar("project_id").notNull().references(() => projects.id, { onDelete: "cascade" }),
  kind: text("kind").notNull(), // "note", "document", "link", etc.
  source: text("source").notNull(), // "manual", "notion", "drive", etc.
  content: text("content").notNull(),
  embeddingRef: text("embedding_ref"), // reference to external embedding storage
  createdAt: timestamp("created_at").notNull().defaultNow(),
});

export const insertMemoryItemSchema = createInsertSchema(memoryItems).omit({
  id: true,
  createdAt: true,
});

export type InsertMemoryItem = z.infer<typeof insertMemoryItemSchema>;
export type MemoryItem = typeof memoryItems.$inferSelect;

// Audit log
export const auditLog = pgTable("audit_log", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  orgId: varchar("org_id").notNull().references(() => orgs.id, { onDelete: "cascade" }),
  userId: varchar("user_id").references(() => users.id, { onDelete: "set null" }),
  action: text("action").notNull(),
  target: text("target").notNull(),
  detailJson: jsonb("detail_json"),
  createdAt: timestamp("created_at").notNull().defaultNow(),
});

export const insertAuditLogSchema = createInsertSchema(auditLog).omit({
  id: true,
  createdAt: true,
});

export type InsertAuditLog = z.infer<typeof insertAuditLogSchema>;
export type AuditLog = typeof auditLog.$inferSelect;

// Budgets
export const budgets = pgTable("budgets", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  orgId: varchar("org_id").notNull().references(() => orgs.id, { onDelete: "cascade" }),
  period: text("period", { enum: ["daily", "monthly"] }).notNull(),
  limitUsd: decimal("limit_usd", { precision: 10, scale: 2 }).notNull(),
  spentUsd: decimal("spent_usd", { precision: 10, scale: 2 }).notNull().default("0"),
  updatedAt: timestamp("updated_at").notNull().defaultNow(),
});

export const insertBudgetSchema = createInsertSchema(budgets).omit({
  id: true,
});

export type InsertBudget = z.infer<typeof insertBudgetSchema>;
export type Budget = typeof budgets.$inferSelect;

// API Keys for external integrations (Zapier, etc)
export const apiKeys = pgTable("api_keys", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  orgId: varchar("org_id").notNull().references(() => orgs.id, { onDelete: "cascade" }),
  key: text("key").notNull().unique(),
  name: text("name").notNull(),
  createdAt: timestamp("created_at").notNull().defaultNow(),
});

export const insertApiKeySchema = createInsertSchema(apiKeys).omit({
  id: true,
  createdAt: true,
});

export type InsertApiKey = z.infer<typeof insertApiKeySchema>;
export type ApiKey = typeof apiKeys.$inferSelect;

// User Credentials (encrypted API keys per user)
export const userCredentials = pgTable("user_credentials", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  userId: varchar("user_id").notNull().references(() => users.id, { onDelete: "cascade" }),
  provider: text("provider").notNull(), // openai, anthropic, perplexity, xai, github, etc.
  encryptedKey: text("encrypted_key").notNull(), // AES-256-GCM encrypted API key
  iv: text("iv").notNull(), // Initialization vector for decryption
  authTag: text("auth_tag").notNull(), // Authentication tag for AES-GCM
  label: text("label"), // User-friendly label
  lastUsedAt: timestamp("last_used_at"),
  createdAt: timestamp("created_at").notNull().defaultNow(),
  updatedAt: timestamp("updated_at").notNull().defaultNow(),
});

export const insertUserCredentialSchema = createInsertSchema(userCredentials).omit({
  id: true,
  lastUsedAt: true,
  createdAt: true,
  updatedAt: true,
});

export type InsertUserCredential = z.infer<typeof insertUserCredentialSchema>;
export type UserCredential = typeof userCredentials.$inferSelect;

// Usage tracking for cost estimates
export const usageRecords = pgTable("usage_records", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  orgId: varchar("org_id").notNull().references(() => orgs.id, { onDelete: "cascade" }),
  userId: varchar("user_id").notNull().references(() => users.id, { onDelete: "cascade" }),
  provider: text("provider").notNull(),
  model: text("model").notNull(),
  inputTokens: integer("input_tokens").notNull().default(0),
  outputTokens: integer("output_tokens").notNull().default(0),
  estimatedCostUsd: decimal("estimated_cost_usd", { precision: 10, scale: 6 }).notNull().default("0"),
  metadata: jsonb("metadata"), // Additional context (agent run id, etc.)
  createdAt: timestamp("created_at").notNull().defaultNow(),
});

export const insertUsageRecordSchema = createInsertSchema(usageRecords).omit({
  id: true,
  createdAt: true,
});

export type InsertUsageRecord = z.infer<typeof insertUsageRecordSchema>;
export type UsageRecord = typeof usageRecords.$inferSelect;

// Decision Traces - log every agent step with reasoning
export const decisionTraces = pgTable("decision_traces", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  agentRunId: varchar("agent_run_id").notNull().references(() => agentRuns.id, { onDelete: "cascade" }),
  stepNumber: integer("step_number").notNull(),
  stepType: text("step_type", { 
    enum: ["provider_selection", "retry", "fallback", "model_selection", "context_analysis", "tool_call", "response_generation", "error_handling"] 
  }).notNull(),
  decision: text("decision").notNull(),
  reasoning: text("reasoning").notNull(),
  confidence: decimal("confidence", { precision: 3, scale: 2 }),
  alternatives: jsonb("alternatives"),
  contextUsed: jsonb("context_used"),
  durationMs: integer("duration_ms"),
  approvalStatus: text("approval_status", { 
    enum: ["not_required", "pending", "approved", "rejected"] 
  }).notNull().default("not_required"),
  approvedBy: varchar("approved_by").references(() => users.id, { onDelete: "set null" }),
  approvedAt: timestamp("approved_at"),
  rejectionReason: text("rejection_reason"),
  createdAt: timestamp("created_at").notNull().defaultNow(),
});

export const insertDecisionTraceSchema = createInsertSchema(decisionTraces).omit({
  id: true,
  createdAt: true,
});

export type InsertDecisionTrace = z.infer<typeof insertDecisionTraceSchema>;
export type DecisionTrace = typeof decisionTraces.$inferSelect;

// Roundtable Sessions - multi-AI conversation sessions
export const roundtableSessions = pgTable("roundtable_sessions", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  orgId: varchar("org_id").notNull().references(() => orgs.id, { onDelete: "cascade" }),
  projectId: varchar("project_id").references(() => projects.id, { onDelete: "set null" }),
  title: text("title").notNull(),
  topic: text("topic"), // Discussion topic for AIs to focus on
  status: text("status", { enum: ["active", "paused", "completed"] }).notNull().default("active"),
  orchestrationMode: text("orchestration_mode", { enum: ["round_robin", "topic_based", "free_form"] }).notNull().default("round_robin"),
  maxTurns: integer("max_turns").default(20), // Prevent infinite loops
  currentTurn: integer("current_turn").notNull().default(0),
  activeProviders: text("active_providers").array(), // Which AI providers are in this session
  createdBy: varchar("created_by").notNull().references(() => users.id, { onDelete: "cascade" }),
  createdAt: timestamp("created_at").notNull().defaultNow(),
  updatedAt: timestamp("updated_at").notNull().defaultNow(),
});

export const insertRoundtableSessionSchema = createInsertSchema(roundtableSessions).omit({
  id: true,
  currentTurn: true,
  createdAt: true,
  updatedAt: true,
});

export type InsertRoundtableSession = z.infer<typeof insertRoundtableSessionSchema>;
export type RoundtableSession = typeof roundtableSessions.$inferSelect;

// Roundtable Messages - conversation log with signed messages
export const roundtableMessages = pgTable("roundtable_messages", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  sessionId: varchar("session_id").notNull().references(() => roundtableSessions.id, { onDelete: "cascade" }),
  senderType: text("sender_type", { enum: ["user", "ai", "system"] }).notNull(),
  senderId: varchar("sender_id"), // User ID for users, null for AI/system
  provider: text("provider"), // AI provider name (openai, anthropic, etc.)
  model: text("model"), // Specific model used (gpt-4o, claude-3, etc.)
  content: text("content").notNull(),
  signature: text("signature"), // AI-generated signature/sign-off
  sequenceNumber: integer("sequence_number").notNull(),
  tokensUsed: integer("tokens_used"),
  responseTimeMs: integer("response_time_ms"),
  metadata: jsonb("metadata"), // Additional context (reasoning, confidence, etc.)
  createdAt: timestamp("created_at").notNull().defaultNow(),
});

export const insertRoundtableMessageSchema = createInsertSchema(roundtableMessages).omit({
  id: true,
  createdAt: true,
});

export type InsertRoundtableMessage = z.infer<typeof insertRoundtableMessageSchema>;
export type RoundtableMessage = typeof roundtableMessages.$inferSelect;

// Agent Analyses - Store file analysis records
export const agentAnalyses = pgTable("agent_analyses", {
  id: integer("id").primaryKey().generatedAlwaysAsIdentity(),
  orgId: varchar("org_id").notNull().references(() => orgs.id, { onDelete: "cascade" }),
  projectId: varchar("project_id").references(() => projects.id, { onDelete: "set null" }),
  userId: varchar("user_id").notNull().references(() => users.id, { onDelete: "cascade" }),
  filePath: text("file_path").notNull(),
  content: text("content").notNull(),
  analysisResult: jsonb("analysis_result"),
  createdAt: timestamp("created_at").notNull().defaultNow(),
});

export const insertAgentAnalysisSchema = createInsertSchema(agentAnalyses).omit({
  createdAt: true,
});

export type InsertAgentAnalysis = z.infer<typeof insertAgentAnalysisSchema>;
export type AgentAnalysis = typeof agentAnalyses.$inferSelect;

// Agent Suggestions - Store AI suggestions
export const agentSuggestions = pgTable("agent_suggestions", {
  id: integer("id").primaryKey().generatedAlwaysAsIdentity(),
  analysisId: integer("analysis_id").notNull().references(() => agentAnalyses.id, { onDelete: "cascade" }),
  provider: text("provider").notNull(),
  model: text("model").notNull(),
  prompt: text("prompt").notNull(),
  suggestions: jsonb("suggestions").notNull(),
  diffPreview: text("diff_preview"),
  createdAt: timestamp("created_at").notNull().defaultNow(),
});

export const insertAgentSuggestionSchema = createInsertSchema(agentSuggestions).omit({
  createdAt: true,
});

export type InsertAgentSuggestion = z.infer<typeof insertAgentSuggestionSchema>;
export type AgentSuggestion = typeof agentSuggestions.$inferSelect;

// Agent Proposals - Store change proposals
export const agentProposals = pgTable("agent_proposals", {
  id: integer("id").primaryKey().generatedAlwaysAsIdentity(),
  orgId: varchar("org_id").notNull().references(() => orgs.id, { onDelete: "cascade" }),
  suggestionId: integer("suggestion_id").references(() => agentSuggestions.id, { onDelete: "set null" }),
  filePath: text("file_path").notNull(),
  originalContent: text("original_content").notNull(),
  proposedContent: text("proposed_content").notNull(),
  status: text("status", { enum: ["pending", "approved", "rejected", "applied"] }).notNull().default("pending"),
  approvedBy: varchar("approved_by").references(() => users.id, { onDelete: "set null" }),
  createdAt: timestamp("created_at").notNull().defaultNow(),
});

export const insertAgentProposalSchema = createInsertSchema(agentProposals).omit({
  createdAt: true,
});

export type InsertAgentProposal = z.infer<typeof insertAgentProposalSchema>;
export type AgentProposal = typeof agentProposals.$inferSelect;

// ===== WORKSPACES =====
// User workspaces for project organization
export const workspaces = pgTable("workspaces", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  orgId: varchar("org_id").notNull().references(() => orgs.id, { onDelete: "cascade" }),
  name: text("name").notNull(),
  description: text("description"),
  type: text("type", { enum: ["code", "design", "docs", "general"] }).notNull().default("general"),
  settings: jsonb("settings"), // Workspace-specific settings
  createdBy: varchar("created_by").notNull().references(() => users.id, { onDelete: "cascade" }),
  createdAt: timestamp("created_at").notNull().defaultNow(),
  updatedAt: timestamp("updated_at").notNull().defaultNow(),
});

export const insertWorkspaceSchema = createInsertSchema(workspaces).omit({
  id: true,
  createdAt: true,
  updatedAt: true,
});

export type InsertWorkspace = z.infer<typeof insertWorkspaceSchema>;
export type Workspace = typeof workspaces.$inferSelect;

// ===== SUBSCRIPTIONS =====
// User subscription tracking (linked to Stripe)
export const subscriptions = pgTable("subscriptions", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  orgId: varchar("org_id").notNull().references(() => orgs.id, { onDelete: "cascade" }),
  stripeCustomerId: text("stripe_customer_id"),
  stripeSubscriptionId: text("stripe_subscription_id"),
  stripePriceId: text("stripe_price_id"),
  plan: text("plan", { enum: ["free", "starter", "pro", "enterprise"] }).notNull().default("free"),
  status: text("status", { enum: ["active", "canceled", "past_due", "trialing", "paused"] }).notNull().default("active"),
  currentPeriodStart: timestamp("current_period_start"),
  currentPeriodEnd: timestamp("current_period_end"),
  cancelAtPeriodEnd: text("cancel_at_period_end").default("false"),
  createdAt: timestamp("created_at").notNull().defaultNow(),
  updatedAt: timestamp("updated_at").notNull().defaultNow(),
});

export const insertSubscriptionSchema = createInsertSchema(subscriptions).omit({
  id: true,
  createdAt: true,
  updatedAt: true,
});

export type InsertSubscription = z.infer<typeof insertSubscriptionSchema>;
export type Subscription = typeof subscriptions.$inferSelect;

// ===== PROMO CODES =====
// Promotional codes for discounts
export const promoCodes = pgTable("promo_codes", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  code: text("code").notNull().unique(),
  discountType: text("discount_type", { enum: ["percent", "fixed"] }).notNull(),
  discountValue: decimal("discount_value", { precision: 10, scale: 2 }).notNull(),
  maxUses: integer("max_uses"),
  usedCount: integer("used_count").notNull().default(0),
  validFrom: timestamp("valid_from").notNull().defaultNow(),
  validUntil: timestamp("valid_until"),
  applicablePlans: text("applicable_plans").array(), // Which plans this code works for
  createdBy: varchar("created_by").references(() => users.id, { onDelete: "set null" }),
  createdAt: timestamp("created_at").notNull().defaultNow(),
});

export const insertPromoCodeSchema = createInsertSchema(promoCodes).omit({
  id: true,
  usedCount: true,
  createdAt: true,
});

export type InsertPromoCode = z.infer<typeof insertPromoCodeSchema>;
export type PromoCode = typeof promoCodes.$inferSelect;

// ===== PROMO CODE REDEMPTIONS =====
// Track who used which promo code
export const promoRedemptions = pgTable("promo_redemptions", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  promoCodeId: varchar("promo_code_id").notNull().references(() => promoCodes.id, { onDelete: "cascade" }),
  orgId: varchar("org_id").notNull().references(() => orgs.id, { onDelete: "cascade" }),
  subscriptionId: varchar("subscription_id").references(() => subscriptions.id, { onDelete: "set null" }),
  redeemedAt: timestamp("redeemed_at").notNull().defaultNow(),
});

export const insertPromoRedemptionSchema = createInsertSchema(promoRedemptions).omit({
  id: true,
  redeemedAt: true,
});

export type InsertPromoRedemption = z.infer<typeof insertPromoRedemptionSchema>;
export type PromoRedemption = typeof promoRedemptions.$inferSelect;

// ===== STORAGE FILES =====
// Track files across storage providers
export const storageFiles = pgTable("storage_files", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  orgId: varchar("org_id").notNull().references(() => orgs.id, { onDelete: "cascade" }),
  workspaceId: varchar("workspace_id").references(() => workspaces.id, { onDelete: "set null" }),
  provider: text("provider", { enum: ["google_drive", "onedrive", "notion", "github", "local"] }).notNull(),
  externalId: text("external_id").notNull(), // Provider's file ID
  name: text("name").notNull(),
  mimeType: text("mime_type"),
  size: integer("size"),
  path: text("path"),
  webUrl: text("web_url"),
  metadata: jsonb("metadata"),
  syncedAt: timestamp("synced_at").notNull().defaultNow(),
  createdAt: timestamp("created_at").notNull().defaultNow(),
});

export const insertStorageFileSchema = createInsertSchema(storageFiles).omit({
  id: true,
  syncedAt: true,
  createdAt: true,
});

export type InsertStorageFile = z.infer<typeof insertStorageFileSchema>;
export type StorageFile = typeof storageFiles.$inferSelect;

// ===== USER PROFILES =====
// MySpace-style personal profile pages
export const userProfiles = pgTable("user_profiles", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  userId: varchar("user_id").notNull().references(() => users.id, { onDelete: "cascade" }).unique(),
  displayName: text("display_name"),
  bio: text("bio"),
  avatarUrl: text("avatar_url"),
  backgroundUrl: text("background_url"),
  youtubeVideos: text("youtube_videos").array(),
  audioFiles: text("audio_files").array(),
  theme: jsonb("theme"),
  socialLinks: jsonb("social_links"),
  createdAt: timestamp("created_at").notNull().defaultNow(),
  updatedAt: timestamp("updated_at").notNull().defaultNow(),
});

export const insertUserProfileSchema = createInsertSchema(userProfiles).omit({
  id: true,
  createdAt: true,
  updatedAt: true,
});

export type InsertUserProfile = z.infer<typeof insertUserProfileSchema>;
export type UserProfile = typeof userProfiles.$inferSelect;

// ===== AUTOMATED WORKFLOWS =====
// User-defined task sequences
export const workflows = pgTable("workflows", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  orgId: varchar("org_id").notNull().references(() => orgs.id, { onDelete: "cascade" }),
  name: text("name").notNull(),
  description: text("description"),
  trigger: text("trigger", { enum: ["manual", "schedule", "webhook"] }).notNull().default("manual"),
  steps: jsonb("steps").notNull(),
  status: text("status", { enum: ["active", "paused", "draft"] }).notNull().default("draft"),
  lastRunAt: timestamp("last_run_at"),
  runCount: integer("run_count").notNull().default(0),
  createdBy: varchar("created_by").notNull().references(() => users.id, { onDelete: "cascade" }),
  createdAt: timestamp("created_at").notNull().defaultNow(),
  updatedAt: timestamp("updated_at").notNull().defaultNow(),
});

export const insertWorkflowSchema = createInsertSchema(workflows).omit({
  id: true,
  lastRunAt: true,
  runCount: true,
  createdAt: true,
  updatedAt: true,
});

export type InsertWorkflow = z.infer<typeof insertWorkflowSchema>;
export type Workflow = typeof workflows.$inferSelect;

// Workflow Runs - execution history
export const workflowRuns = pgTable("workflow_runs", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  workflowId: varchar("workflow_id").notNull().references(() => workflows.id, { onDelete: "cascade" }),
  status: text("status", { enum: ["running", "completed", "failed", "cancelled"] }).notNull().default("running"),
  startedAt: timestamp("started_at").notNull().defaultNow(),
  completedAt: timestamp("completed_at"),
  stepResults: jsonb("step_results"),
  error: text("error"),
});

export const insertWorkflowRunSchema = createInsertSchema(workflowRuns).omit({
  id: true,
  startedAt: true,
});

export type InsertWorkflowRun = z.infer<typeof insertWorkflowRunSchema>;
export type WorkflowRun = typeof workflowRuns.$inferSelect;

// ===== SECURITY: RECOVERY CODES =====
// One-time use recovery codes for account access
export const recoveryCodes = pgTable("recovery_codes", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  userId: varchar("user_id").notNull().references(() => users.id),
  codeHash: varchar("code_hash", { length: 64 }).notNull(),
  usedAt: timestamp("used_at"),
  createdAt: timestamp("created_at").defaultNow().notNull(),
});

export const insertRecoveryCodeSchema = createInsertSchema(recoveryCodes).omit({
  id: true,
  usedAt: true,
  createdAt: true,
});

export type InsertRecoveryCode = z.infer<typeof insertRecoveryCodeSchema>;
export type RecoveryCode = typeof recoveryCodes.$inferSelect;

// ===== SECURITY: TOTP SECRETS FOR 2FA =====
// Time-based One-Time Password secrets for two-factor authentication
export const totpSecrets = pgTable("totp_secrets", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  userId: varchar("user_id").notNull().references(() => users.id).unique(),
  encryptedSecret: varchar("encrypted_secret", { length: 256 }).notNull(),
  verified: boolean("verified").default(false).notNull(),
  createdAt: timestamp("created_at").defaultNow().notNull(),
});

export const insertTotpSecretSchema = createInsertSchema(totpSecrets).omit({
  id: true,
  createdAt: true,
});

export type InsertTotpSecret = z.infer<typeof insertTotpSecretSchema>;
export type TotpSecret = typeof totpSecrets.$inferSelect;

// ===== SECURITY: QR LOGIN SESSIONS =====
// QR code-based login sessions for mobile/secondary device authentication
export const qrLoginSessions = pgTable("qr_login_sessions", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  token: varchar("token", { length: 64 }).notNull().unique(),
  userId: varchar("user_id").references(() => users.id),
  status: varchar("status", { length: 20 }).default("pending").notNull(), // pending, approved, expired
  expiresAt: timestamp("expires_at").notNull(),
  createdAt: timestamp("created_at").defaultNow().notNull(),
});

export const insertQrLoginSessionSchema = createInsertSchema(qrLoginSessions).omit({
  id: true,
  createdAt: true,
});

export type InsertQrLoginSession = z.infer<typeof insertQrLoginSessionSchema>;
export type QrLoginSession = typeof qrLoginSessions.$inferSelect;

// ===== ZAPIER INTEGRATION =====
// Webhook subscriptions for Zapier REST hooks
export const zapierWebhooks = pgTable("zapier_webhooks", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  orgId: varchar("org_id").notNull().references(() => orgs.id, { onDelete: "cascade" }),
  event: text("event").notNull(), // Event type: user.created, project.created, agent_run.completed, etc.
  targetUrl: text("target_url").notNull(), // Zapier's webhook URL
  isActive: boolean("is_active").notNull().default(true),
  secretKey: text("secret_key").notNull(), // For webhook signature verification
  metadata: jsonb("metadata"), // Additional config
  lastTriggeredAt: timestamp("last_triggered_at"),
  triggerCount: integer("trigger_count").notNull().default(0),
  createdAt: timestamp("created_at").notNull().defaultNow(),
});

export const insertZapierWebhookSchema = createInsertSchema(zapierWebhooks).omit({
  id: true,
  lastTriggeredAt: true,
  triggerCount: true,
  createdAt: true,
});

export type InsertZapierWebhook = z.infer<typeof insertZapierWebhookSchema>;
export type ZapierWebhook = typeof zapierWebhooks.$inferSelect;

// Zapier webhook delivery log (for debugging failed deliveries)
export const zapierWebhookLogs = pgTable("zapier_webhook_logs", {
  id: varchar("id").primaryKey().default(sql`gen_random_uuid()`),
  webhookId: varchar("webhook_id").notNull().references(() => zapierWebhooks.id, { onDelete: "cascade" }),
  event: text("event").notNull(),
  payload: jsonb("payload").notNull(),
  responseStatus: integer("response_status"),
  responseBody: text("response_body"),
  success: boolean("success").notNull().default(false),
  errorMessage: text("error_message"),
  deliveredAt: timestamp("delivered_at").notNull().defaultNow(),
});

export const insertZapierWebhookLogSchema = createInsertSchema(zapierWebhookLogs).omit({
  id: true,
  deliveredAt: true,
});

export type InsertZapierWebhookLog = z.infer<typeof insertZapierWebhookLogSchema>;
export type ZapierWebhookLog = typeof zapierWebhookLogs.$inferSelect;
