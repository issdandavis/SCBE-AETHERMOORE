
import { GoogleGenAI, Type } from "@google/genai";

export const getWorkflowSuggestions = async (currentNodes: any[], prompt: string) => {
  // Always use new GoogleGenAI({apiKey: process.env.API_KEY}) directly as per guidelines
  const ai = new GoogleGenAI({ apiKey: process.env.API_KEY });
  const response = await ai.models.generateContent({
    model: 'gemini-3-flash-preview',
    contents: `Current workflow state: ${JSON.stringify(currentNodes)}. User request: ${prompt}. Suggest 3 next logical steps or agents to add to this workflow.`,
    config: {
      responseMimeType: "application/json",
      responseSchema: {
        type: Type.ARRAY,
        items: {
          type: Type.OBJECT,
          properties: {
            title: { type: Type.STRING },
            description: { type: Type.STRING },
            nodeType: { type: Type.STRING }
          },
          required: ["title", "description", "nodeType"]
        }
      }
    }
  });
  return JSON.parse(response.text || '[]');
};

export const generateAgentCode = async (requirements: string) => {
  // Always use new GoogleGenAI({apiKey: process.env.API_KEY}) directly as per guidelines
  const ai = new GoogleGenAI({ apiKey: process.env.API_KEY });
  const response = await ai.models.generateContent({
    model: 'gemini-3-pro-preview',
    contents: `Write a TypeScript function for an AI agent that performs the following task: ${requirements}. Use modern async/await and robust error handling.`,
    config: {
      systemInstruction: "You are a senior lead architect for AI multi-agent systems. Write clean, modular, and well-documented TypeScript code.",
    }
  });
  return response.text;
};
