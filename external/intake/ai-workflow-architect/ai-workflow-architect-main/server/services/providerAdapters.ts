// Provider adapters for multi-agent orchestration
// Returns safe stub responses when keys not configured

export interface ProviderResponse {
  success: boolean;
  content?: string;
  error?: string;
  usage?: {
    inputTokens: number;
    outputTokens: number;
    costEstimate: string;
  };
}

export interface ProviderAdapter {
  name: string;
  call(prompt: string, model: string): Promise<ProviderResponse>;
}

// Helper to detect invalid/placeholder API keys
function isValidApiKey(key: string | undefined): boolean {
  if (!key) return false;
  // Detect common placeholder patterns
  if (key.includes('DUMMY') || key.includes('dummy') || key.includes('placeholder')) return false;
  if (key.includes('YOUR_API_KEY') || key.includes('your_api_key')) return false;
  if (key.includes('xxx') || key.includes('XXX')) return false;
  if (key.length < 10) return false; // Most real API keys are longer
  if (key.startsWith('sk-test') && key.includes('DUMMY')) return false;
  return true;
}

// Demo mode flag - when true, return stub responses instead of calling real APIs
const DEMO_MODE = process.env.AI_DEMO_MODE === 'true' || process.env.NODE_ENV === 'development';

// Generate realistic demo response based on provider and prompt
function generateDemoResponse(provider: string, prompt: string): ProviderResponse {
  const shortPrompt = prompt.substring(0, 100);
  const responseMap: Record<string, (p: string) => string> = {
    openai: (p) => `**GPT Analysis:**\n\nBased on your query about "${p.substring(0, 50)}...", here are my key insights:\n\n1. **Core Understanding**: This topic requires examining multiple perspectives and considering both short-term and long-term implications.\n\n2. **Practical Applications**: I recommend focusing on actionable steps that can be implemented immediately while building toward larger goals.\n\n3. **Key Considerations**: Always evaluate trade-offs between different approaches and remain flexible as new information emerges.\n\n*This is a demo response - configure valid API keys for production use.*`,
    anthropic: (p) => `I'll analyze this thoughtfully.\n\n**Claude's Perspective:**\n\nRegarding "${p.substring(0, 50)}...", I see several important dimensions to consider:\n\n• **Analytical View**: Breaking this down systematically reveals interconnected factors that influence outcomes.\n\n• **Ethical Considerations**: It's important to weigh the impact on all stakeholders involved.\n\n• **Recommendation**: A balanced approach that combines careful analysis with decisive action typically yields the best results.\n\n*This is a demo response - configure valid API keys for production use.*`,
    google: (p) => `**Gemini Insights:**\n\nExploring "${p.substring(0, 50)}...":\n\n1. **Research Perspective**: Drawing from diverse knowledge sources, this topic intersects with several fields.\n\n2. **Data-Driven Approach**: Evidence suggests that systematic methodologies tend to produce more reliable outcomes.\n\n3. **Future Outlook**: Emerging trends indicate continued evolution in this space with new opportunities arising.\n\n*This is a demo response - configure valid API keys for production use.*`,
    perplexity: (p) => `**Perplexity Research Summary:**\n\nAnalyzing "${p.substring(0, 50)}...":\n\n• **Key Findings**: Current research and real-time data indicate significant developments in this area.\n\n• **Sources**: Multiple authoritative references support these conclusions.\n\n• **Actionable Insights**: Based on the latest information, consider these priority actions.\n\n*This is a demo response - configure valid API keys for production use.*`,
    xai: (p) => `**Grok Analysis:**\n\nLet me break down "${p.substring(0, 50)}...":\n\n• Direct and candid assessment of the situation\n• Practical recommendations without unnecessary complexity\n• Clear next steps for implementation\n\n*This is a demo response - configure valid API keys for production use.*`,
  };
  
  const generator = responseMap[provider.toLowerCase()] || responseMap.openai;
  
  return {
    success: true,
    content: generator(shortPrompt),
    usage: {
      inputTokens: Math.floor(prompt.length / 4),
      outputTokens: 150 + Math.floor(Math.random() * 100),
      costEstimate: "0.0000",
    },
  };
}

// Base adapter with fallback behavior
class BaseProviderAdapter implements ProviderAdapter {
  constructor(
    public name: string,
    protected apiKey: string | undefined,
  ) {}

  async call(prompt: string, model: string): Promise<ProviderResponse> {
    if (!this.apiKey || !isValidApiKey(this.apiKey)) {
      return {
        success: false,
        error: `${this.name} API key not configured or invalid. Please add a valid API key in Settings > API Keys.`,
      };
    }

    // Stub implementation - override in subclasses for real providers
    return {
      success: true,
      content: `[STUB] ${this.name} response to: ${prompt.substring(0, 50)}...`,
      usage: {
        inputTokens: 100,
        outputTokens: 50,
        costEstimate: "0.0001",
      },
    };
  }
}

export class OpenAIAdapter extends BaseProviderAdapter {
  constructor(apiKey: string | undefined) {
    super("OpenAI", apiKey);
  }

  async call(prompt: string, model: string): Promise<ProviderResponse> {
    if (!this.apiKey || !isValidApiKey(this.apiKey)) {
      // Return demo response in development mode
      if (DEMO_MODE) {
        return generateDemoResponse("openai", prompt);
      }
      return {
        success: false,
        error: "OpenAI API key not configured or invalid. Please add a valid API key in Settings > API Keys.",
      };
    }

    try {
      const response = await fetch("https://api.openai.com/v1/chat/completions", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${this.apiKey}`,
        },
        body: JSON.stringify({
          model: model || "gpt-4o",
          messages: [{ role: "user", content: prompt }],
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        return {
          success: false,
          error: data.error?.message || "OpenAI API error",
        };
      }

      const content = data.choices?.[0]?.message?.content || "";

      return {
        success: true,
        content,
        usage: {
          inputTokens: data.usage?.prompt_tokens || 0,
          outputTokens: data.usage?.completion_tokens || 0,
          costEstimate: "0.0003",
        },
      };
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : "Unknown error",
      };
    }
  }
}

export class AnthropicAdapter extends BaseProviderAdapter {
  constructor(apiKey: string | undefined) {
    super("Anthropic", apiKey);
  }

  async call(prompt: string, model: string): Promise<ProviderResponse> {
    if (!this.apiKey || !isValidApiKey(this.apiKey)) {
      // Return demo response in development mode
      if (DEMO_MODE) {
        return generateDemoResponse("anthropic", prompt);
      }
      return {
        success: false,
        error: "Anthropic API key not configured or invalid. Please add a valid API key in Settings > API Keys.",
      };
    }

    try {
      const response = await fetch("https://api.anthropic.com/v1/messages", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "x-api-key": this.apiKey,
          "anthropic-version": "2023-06-01",
        },
        body: JSON.stringify({
          model: model || "claude-sonnet-4-20250514",
          max_tokens: 4096,
          messages: [{ role: "user", content: prompt }],
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        return {
          success: false,
          error: data.error?.message || "Anthropic API error",
        };
      }

      const content = data.content?.[0]?.text || "";

      return {
        success: true,
        content,
        usage: {
          inputTokens: data.usage?.input_tokens || 0,
          outputTokens: data.usage?.output_tokens || 0,
          costEstimate: "0.0004",
        },
      };
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : "Unknown error",
      };
    }
  }
}

export class XAIAdapter extends BaseProviderAdapter {
  constructor(apiKey: string | undefined) {
    super("xAI", apiKey);
  }

  async call(prompt: string, model: string): Promise<ProviderResponse> {
    if (!this.apiKey || !isValidApiKey(this.apiKey)) {
      // Return demo response in development mode
      if (DEMO_MODE) {
        return generateDemoResponse("xai", prompt);
      }
      return {
        success: false,
        error: "xAI API key not configured or invalid. Please add a valid API key in Settings > API Keys.",
      };
    }

    try {
      const response = await fetch("https://api.x.ai/v1/chat/completions", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${this.apiKey}`,
        },
        body: JSON.stringify({
          model: model || "grok-2",
          messages: [{ role: "user", content: prompt }],
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        return {
          success: false,
          error: data.error?.message || "xAI API error",
        };
      }

      const content = data.choices?.[0]?.message?.content || "";

      return {
        success: true,
        content,
        usage: {
          inputTokens: data.usage?.prompt_tokens || 0,
          outputTokens: data.usage?.completion_tokens || 0,
          costEstimate: "0.0003",
        },
      };
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : "Unknown error",
      };
    }
  }
}

export class PerplexityAdapter extends BaseProviderAdapter {
  constructor(apiKey: string | undefined) {
    super("Perplexity", apiKey);
  }

  async call(prompt: string, model: string): Promise<ProviderResponse> {
    if (!this.apiKey || !isValidApiKey(this.apiKey)) {
      // Return demo response in development mode
      if (DEMO_MODE) {
        return generateDemoResponse("perplexity", prompt);
      }
      return {
        success: false,
        error: "Perplexity API key not configured or invalid. Please add a valid API key in Settings > API Keys.",
      };
    }

    try {
      const response = await fetch("https://api.perplexity.ai/chat/completions", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${this.apiKey}`,
        },
        body: JSON.stringify({
          model: model || "sonar",
          messages: [{ role: "user", content: prompt }],
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        return {
          success: false,
          error: data.error?.message || "Perplexity API error",
        };
      }

      const content = data.choices?.[0]?.message?.content || "";

      return {
        success: true,
        content,
        usage: {
          inputTokens: data.usage?.prompt_tokens || 0,
          outputTokens: data.usage?.completion_tokens || 0,
          costEstimate: "0.0002",
        },
      };
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : "Unknown error",
      };
    }
  }
}

export class GeminiAdapter extends BaseProviderAdapter {
  constructor(apiKey: string | undefined) {
    super("Google Gemini", apiKey);
  }

  async call(prompt: string, model: string): Promise<ProviderResponse> {
    if (!this.apiKey || !isValidApiKey(this.apiKey)) {
      // Return demo response in development mode
      if (DEMO_MODE) {
        return generateDemoResponse("google", prompt);
      }
      return {
        success: false,
        error: "Google Gemini API key not configured or invalid. Please add a valid API key in Settings > API Keys.",
      };
    }

    try {
      const response = await fetch(
        `https://generativelanguage.googleapis.com/v1beta/models/${model || "gemini-2.0-flash"}:generateContent?key=${this.apiKey}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            contents: [{ parts: [{ text: prompt }] }],
          }),
        }
      );

      const data = await response.json();
      
      if (!response.ok) {
        return {
          success: false,
          error: data.error?.message || "Gemini API error",
        };
      }

      const content = data.candidates?.[0]?.content?.parts?.[0]?.text || "";
      
      return {
        success: true,
        content,
        usage: {
          inputTokens: data.usageMetadata?.promptTokenCount || 0,
          outputTokens: data.usageMetadata?.candidatesTokenCount || 0,
          costEstimate: "0.0001",
        },
      };
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : "Unknown error",
      };
    }
  }
}

export class HuggingFaceAdapter extends BaseProviderAdapter {
  constructor() {
    super("HuggingFace", "free");
  }

  async call(prompt: string, model: string): Promise<ProviderResponse> {
    const { generateWithHuggingFace } = await import("./huggingfaceClient");
    return generateWithHuggingFace(prompt, model || "meta-llama/Meta-Llama-3-8B-Instruct");
  }
}

export class OllamaAdapter extends BaseProviderAdapter {
  constructor() {
    super("Ollama", "local");
  }

  async call(prompt: string, model: string): Promise<ProviderResponse> {
    const { generateWithOllama } = await import("./ollamaClient");
    return generateWithOllama(prompt, model || "llama3.1:8b");
  }
}

export class GroqAdapter extends BaseProviderAdapter {
  constructor(apiKey: string | undefined) {
    super("Groq", apiKey);
  }

  async call(prompt: string, model: string): Promise<ProviderResponse> {
    const { generateWithGroq } = await import("./groqClient");
    return generateWithGroq(prompt, model || "llama3-8b-8192");
  }
}

// Factory to get the right adapter
// If apiKey is provided, use it; otherwise fall back to process.env
// Check for AI_INTEGRATIONS_ prefix first (Replit integrations), then standard names
export function getProviderAdapter(provider: string, apiKey?: string): ProviderAdapter {
  const envApiKeys = {
    openai: process.env.AI_INTEGRATIONS_OPENAI_API_KEY || process.env.OPENAI_API_KEY,
    anthropic: process.env.AI_INTEGRATIONS_ANTHROPIC_API_KEY || process.env.ANTHROPIC_API_KEY,
    xai: process.env.XAI_API_KEY,
    perplexity: process.env.PERPLEXITY_API_KEY,
    google: process.env.AI_INTEGRATIONS_GEMINI_API_KEY || process.env.GOOGLE_API_KEY,
  };

  switch (provider.toLowerCase()) {
    case "openai":
      return new OpenAIAdapter(apiKey || envApiKeys.openai);
    case "anthropic":
      return new AnthropicAdapter(apiKey || envApiKeys.anthropic);
    case "xai":
      return new XAIAdapter(apiKey || envApiKeys.xai);
    case "perplexity":
      return new PerplexityAdapter(apiKey || envApiKeys.perplexity);
    case "google":
    case "gemini":
      return new GeminiAdapter(apiKey || envApiKeys.google);
    case "huggingface":
      return new HuggingFaceAdapter();
    case "ollama":
      return new OllamaAdapter();
    case "groq":
      return new GroqAdapter(apiKey || process.env.GROQ_API_KEY);
    default:
      throw new Error(`Unknown provider: ${provider}`);
  }
}
