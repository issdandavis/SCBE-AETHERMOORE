import { storage } from "../storage";
import { getProviderAdapter } from "./providerAdapters";
import { getUserCredential } from "./vault";
import type { AgentAnalysis, AgentSuggestion, AgentProposal } from "@shared/schema";

interface CodeImprovementOptions {
  orgId: string;
  userId: string;
  projectId?: string;
  filePath: string;
  content: string;
  provider?: string;
  model?: string;
  improvementType?: "refactor" | "optimize" | "security" | "documentation" | "all";
}

interface ImprovementSuggestion {
  title: string;
  description: string;
  priority: "low" | "medium" | "high";
  category: string;
  lineStart?: number;
  lineEnd?: number;
  suggestedCode?: string;
}

interface AnalysisResult {
  summary: string;
  issues: string[];
  suggestions: ImprovementSuggestion[];
  metrics?: {
    complexity?: number;
    maintainability?: number;
    linesOfCode?: number;
  };
}

const ANALYSIS_PROMPT = (filePath: string, content: string, improvementType: string) => `You are an expert code reviewer and software architect. Analyze the following code file and provide improvement suggestions.

FILE: ${filePath}
IMPROVEMENT FOCUS: ${improvementType}

CODE:
\`\`\`
${content}
\`\`\`

Analyze this code and respond with a JSON object containing:
{
  "summary": "Brief summary of the code and its purpose",
  "issues": ["List of identified issues or anti-patterns"],
  "suggestions": [
    {
      "title": "Short title for the suggestion",
      "description": "Detailed explanation of the improvement",
      "priority": "low" | "medium" | "high",
      "category": "refactor" | "performance" | "security" | "readability" | "documentation",
      "lineStart": optional line number where issue starts,
      "lineEnd": optional line number where issue ends,
      "suggestedCode": "Optional improved code snippet"
    }
  ],
  "metrics": {
    "complexity": 1-10 score,
    "maintainability": 1-10 score,
    "linesOfCode": number
  }
}

Focus on actionable, specific improvements. Be concise but thorough.`;

const IMPROVEMENT_PROMPT = (filePath: string, originalContent: string, suggestion: ImprovementSuggestion) => `You are an expert programmer. Apply the following improvement to the code file.

FILE: ${filePath}

ORIGINAL CODE:
\`\`\`
${originalContent}
\`\`\`

IMPROVEMENT TO APPLY:
Title: ${suggestion.title}
Description: ${suggestion.description}
Category: ${suggestion.category}
${suggestion.lineStart ? `Lines: ${suggestion.lineStart}-${suggestion.lineEnd || suggestion.lineStart}` : ""}
${suggestion.suggestedCode ? `Suggested approach:\n${suggestion.suggestedCode}` : ""}

Apply this improvement to the code. Return ONLY the complete improved code, no explanations or markdown code blocks. The output should be the full file content with the improvement applied.`;

export async function analyzeCode(options: CodeImprovementOptions): Promise<{
  analysis: AgentAnalysis;
  result: AnalysisResult;
}> {
  const { orgId, userId, projectId, filePath, content, provider = "anthropic", model, improvementType = "all" } = options;

  console.log(`[CodeImprovement] Analyzing ${filePath} using ${provider}`);

  const apiKey = await getUserCredential(userId, provider);
  const adapter = getProviderAdapter(provider, apiKey || undefined);

  const prompt = ANALYSIS_PROMPT(filePath, content, improvementType);
  const defaultModel = provider === "anthropic" ? "claude-sonnet-4-20250514" : 
                       provider === "openai" ? "gpt-4o" :
                       provider === "google" ? "gemini-2.0-flash" : "gpt-4o";

  const response = await adapter.call(prompt, model || defaultModel);

  if (!response.success) {
    throw new Error(`Analysis failed: ${response.error}`);
  }

  let analysisResult: AnalysisResult;
  try {
    const jsonMatch = response.content?.match(/\{[\s\S]*\}/);
    if (jsonMatch) {
      analysisResult = JSON.parse(jsonMatch[0]);
    } else {
      throw new Error("No JSON found in response");
    }
  } catch (parseError) {
    console.error("[CodeImprovement] Failed to parse analysis result:", parseError);
    analysisResult = {
      summary: response.content || "Analysis completed",
      issues: [],
      suggestions: [],
    };
  }

  const analysis = await storage.createAgentAnalysis({
    orgId,
    projectId: projectId || null,
    userId,
    filePath,
    content,
    analysisResult,
  });

  // Track usage for cost analytics
  try {
    await storage.createUsageRecord({
      orgId,
      userId,
      provider,
      model: model || defaultModel,
      inputTokens: response.usage?.inputTokens || 0,
      outputTokens: response.usage?.outputTokens || 0,
      estimatedCostUsd: response.usage?.costEstimate || "0",
      metadata: { requestType: "code_analysis", filePath },
    });
  } catch (err) {
    console.error(`[CodeImprovement] Failed to record usage:`, err);
  }

  console.log(`[CodeImprovement] Analysis complete: ${analysisResult.suggestions.length} suggestions`);

  return { analysis, result: analysisResult };
}

export async function generateImprovement(
  userId: string,
  orgId: string,
  analysisId: number,
  suggestionIndex: number,
  provider: string = "anthropic",
  model?: string
): Promise<{
  suggestion: AgentSuggestion;
  proposal: AgentProposal;
}> {
  const analysis = await storage.getAgentAnalysis(analysisId);
  if (!analysis) {
    throw new Error("Analysis not found");
  }

  if (analysis.orgId !== orgId) {
    throw new Error("Analysis does not belong to this organization");
  }

  const result = analysis.analysisResult as AnalysisResult;
  if (!result.suggestions || suggestionIndex >= result.suggestions.length) {
    throw new Error("Invalid suggestion index");
  }

  const targetSuggestion = result.suggestions[suggestionIndex];

  console.log(`[CodeImprovement] Generating improvement for: ${targetSuggestion.title}`);

  const apiKey = await getUserCredential(userId, provider);
  const adapter = getProviderAdapter(provider, apiKey || undefined);

  const prompt = IMPROVEMENT_PROMPT(analysis.filePath, analysis.content, targetSuggestion);
  const defaultModel = provider === "anthropic" ? "claude-sonnet-4-20250514" : 
                       provider === "openai" ? "gpt-4o" :
                       provider === "google" ? "gemini-2.0-flash" : "gpt-4o";

  const response = await adapter.call(prompt, model || defaultModel);

  if (!response.success) {
    throw new Error(`Improvement generation failed: ${response.error}`);
  }

  const improvedContent = response.content?.trim() || "";

  const diffPreview = generateUnifiedDiff(
    analysis.filePath,
    analysis.content,
    improvedContent
  );

  const suggestion = await storage.createAgentSuggestion({
    analysisId,
    provider,
    model: model || defaultModel,
    prompt,
    suggestions: targetSuggestion,
    diffPreview,
  });

  const proposal = await storage.createAgentProposal({
    orgId,
    suggestionId: suggestion.id,
    filePath: analysis.filePath,
    originalContent: analysis.content,
    proposedContent: improvedContent,
    status: "pending",
    approvedBy: null,
  });

  console.log(`[CodeImprovement] Created proposal #${proposal.id}`);

  return { suggestion, proposal };
}

export async function approveProposal(proposalId: number, orgId: string, userId: string): Promise<AgentProposal> {
  const proposal = await storage.getAgentProposal(proposalId);
  if (!proposal) {
    throw new Error("Proposal not found");
  }

  if (proposal.orgId !== orgId) {
    throw new Error("Proposal does not belong to this organization");
  }

  if (proposal.status !== "pending") {
    throw new Error(`Proposal is already ${proposal.status}`);
  }

  const updated = await storage.updateAgentProposalStatus(proposalId, "approved", userId);
  if (!updated) {
    throw new Error("Failed to approve proposal");
  }

  console.log(`[CodeImprovement] Proposal #${proposalId} approved by ${userId}`);
  return updated;
}

export async function rejectProposal(proposalId: number, orgId: string, userId: string): Promise<AgentProposal> {
  const proposal = await storage.getAgentProposal(proposalId);
  if (!proposal) {
    throw new Error("Proposal not found");
  }

  if (proposal.orgId !== orgId) {
    throw new Error("Proposal does not belong to this organization");
  }

  if (proposal.status !== "pending") {
    throw new Error(`Proposal is already ${proposal.status}`);
  }

  const updated = await storage.updateAgentProposalStatus(proposalId, "rejected", userId);
  if (!updated) {
    throw new Error("Failed to reject proposal");
  }

  console.log(`[CodeImprovement] Proposal #${proposalId} rejected by ${userId}`);
  return updated;
}

export async function applyProposal(proposalId: number, orgId: string): Promise<AgentProposal> {
  const proposal = await storage.getAgentProposal(proposalId);
  if (!proposal) {
    throw new Error("Proposal not found");
  }

  if (proposal.orgId !== orgId) {
    throw new Error("Proposal does not belong to this organization");
  }

  if (proposal.status !== "approved") {
    throw new Error("Proposal must be approved before applying");
  }

  const updated = await storage.updateAgentProposalStatus(proposalId, "applied");
  if (!updated) {
    throw new Error("Failed to mark proposal as applied");
  }

  console.log(`[CodeImprovement] Proposal #${proposalId} applied`);
  return updated;
}

function generateUnifiedDiff(filePath: string, original: string, modified: string): string {
  const originalLines = original.split("\n");
  const modifiedLines = modified.split("\n");

  let diff = `--- a/${filePath}\n+++ b/${filePath}\n`;

  const maxLines = Math.max(originalLines.length, modifiedLines.length);
  let currentHunk = "";
  let hunkStart = -1;
  let hunkOrigCount = 0;
  let hunkModCount = 0;

  for (let i = 0; i < maxLines; i++) {
    const origLine = originalLines[i];
    const modLine = modifiedLines[i];

    if (origLine === modLine) {
      if (currentHunk) {
        currentHunk += ` ${origLine || ""}\n`;
        hunkOrigCount++;
        hunkModCount++;
      }
    } else {
      if (hunkStart === -1) {
        hunkStart = i + 1;
        const contextStart = Math.max(0, i - 3);
        for (let j = contextStart; j < i; j++) {
          currentHunk += ` ${originalLines[j] || ""}\n`;
          hunkOrigCount++;
          hunkModCount++;
        }
      }

      if (origLine !== undefined) {
        currentHunk += `-${origLine}\n`;
        hunkOrigCount++;
      }
      if (modLine !== undefined) {
        currentHunk += `+${modLine}\n`;
        hunkModCount++;
      }
    }
  }

  if (currentHunk) {
    diff += `@@ -${hunkStart},${hunkOrigCount} +${hunkStart},${hunkModCount} @@\n`;
    diff += currentHunk;
  }

  return diff || "(No changes)";
}
