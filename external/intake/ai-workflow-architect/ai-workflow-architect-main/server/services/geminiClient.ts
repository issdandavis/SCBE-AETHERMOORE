import { GoogleGenAI, Modality } from "@google/genai";

const ai = new GoogleGenAI({
  apiKey: process.env.AI_INTEGRATIONS_GEMINI_API_KEY,
  httpOptions: {
    apiVersion: "",
    baseUrl: process.env.AI_INTEGRATIONS_GEMINI_BASE_URL,
  },
});

export async function generateText(prompt: string, model: string = "gemini-2.5-flash"): Promise<string> {
  const response = await ai.models.generateContent({
    model,
    contents: [{ role: "user", parts: [{ text: prompt }] }],
  });
  
  const text = response.candidates?.[0]?.content?.parts?.[0]?.text;
  return text || "";
}

export async function streamText(prompt: string, model: string = "gemini-2.5-flash"): Promise<AsyncGenerator<string>> {
  const stream = await ai.models.generateContentStream({
    model,
    contents: [{ role: "user", parts: [{ text: prompt }] }],
  });

  async function* textStream() {
    for await (const chunk of stream) {
      yield chunk.text || "";
    }
  }
  return textStream();
}

export async function generateImage(prompt: string): Promise<string> {
  const response = await ai.models.generateContent({
    model: "gemini-2.0-flash-exp",
    contents: [{ role: "user", parts: [{ text: `Generate an image: ${prompt}` }] }],
    config: {
      responseModalities: [Modality.TEXT, Modality.IMAGE],
    },
  });

  const candidate = response.candidates?.[0];
  const imagePart = candidate?.content?.parts?.find((part: any) => part.inlineData);
  
  if (!imagePart?.inlineData?.data) {
    throw new Error("No image data in response");
  }

  const mimeType = imagePart.inlineData.mimeType || "image/png";
  return `data:${mimeType};base64,${imagePart.inlineData.data}`;
}

export async function chat(messages: Array<{ role: string; content: string }>, model: string = "gemini-2.5-flash"): Promise<string> {
  const contents = messages.map(msg => ({
    role: msg.role === "assistant" ? "model" : "user",
    parts: [{ text: msg.content }]
  }));

  const response = await ai.models.generateContent({
    model,
    contents,
  });
  
  const text = response.candidates?.[0]?.content?.parts?.[0]?.text;
  return text || "";
}

export function isGeminiConfigured(): boolean {
  return !!(process.env.AI_INTEGRATIONS_GEMINI_API_KEY && process.env.AI_INTEGRATIONS_GEMINI_BASE_URL);
}
