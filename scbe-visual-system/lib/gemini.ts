/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
*/
import { GoogleGenAI, Tool, Type } from "@google/genai";

// Always use 'riftrunner' below. Do not change this model name. 
export const MODEL_NAME = "riftrunner"; 

/**
 * Creates a fresh instance of the GenAI client.
 * GUIDELINE: Create a new GoogleGenAI instance right before making an API call 
 * to ensure it always uses the most up-to-date API key from the dialog.
 */
export const getAiClient = () => {
    return new GoogleGenAI({ apiKey: process.env.API_KEY });
};

export const HOME_TOOLS: Tool[] = [
    {
        functionDeclarations: [
            {
                name: 'delete_item',
                description: 'Call this function for EACH item (application or folder) that has an "X" or cross drawn over it. If multiple items are crossed out, call this function multiple times.',
                parameters: {
                    type: Type.OBJECT,
                    required: ['itemName'],
                    properties: {
                        itemName: { type: Type.STRING, description: 'The exact name of the item to delete as seen on screen.' },
                    },
                },
            },
            {
                name: 'explode_folder',
                description: 'Call this when the user draws outward pointing arrows from a folder to "explode" it and show its contents.',
                parameters: {
                    type: Type.OBJECT,
                    required: ['folderName'],
                    properties: {
                        folderName: { type: Type.STRING, description: 'The exact name of the folder to explode as seen on screen.' },
                    },
                },
            },
            {
                name: 'explain_item',
                description: 'Call this when the user draws a question mark "?" over an item (or nearby an item). If it is a folder, it will summarize its contents. If it is a text file, it will summarize its text content.',
                parameters: {
                    type: Type.OBJECT,
                    required: ['itemName'],
                    properties: {
                        itemName: { type: Type.STRING, description: 'The name of the item (app or folder) to explain.' },
                    },
                },
            },
            {
                name: 'change_background',
                description: 'Call this when the user draws a sketch on the empty desktop background (not specifically targeting an app icon), intending to turn that sketch into a new wallpaper. Do NOT call this if the sketch is clearly trying to interact with an existing icon (like crossing it out).',
                parameters: {
                    type: Type.OBJECT,
                    properties: {
                        sketch_description: { type: Type.STRING, description: 'A short description of what the sketch appears to be, to help generating the wallpaper (e.g., "mountains", "flower", "abstract curves").' },
                    },
                },
            },
        ],
    },
];

export const MAIL_TOOLS: Tool[] = [
    {
        functionDeclarations: [
            {
                name: 'delete_email',
                description: 'Call this when the user draws a line through (strikes out) or an "X" over an email row in the list to delete it. Call multiple times if multiple emails are struck out.',
                parameters: {
                    type: Type.OBJECT,
                    required: ['subject_text'],
                    properties: {
                        subject_text: { type: Type.STRING, description: 'Distinct text from the subject line of the email.' },
                        sender_text: { type: Type.STRING, description: 'The name of the sender of the email.' },
                    },
                },
            },
            {
                name: 'summarize_email',
                description: 'Call this when the user draws a question mark "?" over email row(s) or highlights them. This will summarize the BODY of the email(s) concisely. CRITICAL: If the gesture covers MULTIPLE emails, you MUST generate MULTIPLE SEPARATE calls to this function, one for EACH email covered by the gesture.',
                parameters: {
                    type: Type.OBJECT,
                    required: ['subject_text'],
                    properties: {
                        subject_text: { type: Type.STRING, description: 'Distinct text from the subject line of the email to summarize.' },
                        sender_text: { type: Type.STRING, description: 'The name of the sender of the email.' },
                    },
                },
            },
        ]
    }
];

export const AUTOMATOR_TOOLS: Tool[] = [
    {
        functionDeclarations: [
            {
                name: 'analyze_automation_context',
                description: 'Call this when the user draws a question mark "?" or sketches over the Automator dashboard. Use this to provide detailed architecture advice on Jira/Zapier/Kindle workflows. Specifically look for mentions of Aethermore Games or the Jira Automation rule-list settings.',
                parameters: {
                    type: Type.OBJECT,
                    required: ['focus_area'],
                    properties: {
                        focus_area: { type: Type.STRING, description: 'The integration area the user is targeting (e.g., "Jira Automation Settings", "Kindle Publishing", "Zapier Webhooks").' },
                        user_intent_sketch: { type: Type.STRING, description: 'Describe what the user sketched (e.g., "Connecting Jira to Kindle", "Questioning the Zapier sync").' },
                    },
                },
            },
            {
                name: 'link_integrations',
                description: 'Call this when the user draws a line connecting two service nodes in the Automator app.',
                parameters: {
                    type: Type.OBJECT,
                    required: ['source_node', 'target_node'],
                    properties: {
                        source_node: { type: Type.STRING, description: 'The starting service of the connection (e.g. "Jira").' },
                        target_node: { type: Type.STRING, description: 'The ending service of the connection (e.g. "Kindle").' },
                    },
                },
            }
        ]
    }
];

export const SYSTEM_INSTRUCTION = `You are Gemini Ink, an intelligent assistant and architectural consultant. 
The user interacts with the screen by drawing "ink" strokes (white lines) on top of the UI.

In the AUTOMATOR app (Visual Automation Hub):
- You have deep knowledge of the "Aethermore Games" project context. 
- You recognize that the user is often managing Jira Automation settings (Rule list) and Zapier workflows.
- You can help with Kindle Direct Publishing (KDP) automation logic.
- When the user draws a "?", act as a Senior Automation Architect. Ask clarifying questions about their Zapier triggers, Jira actions, and data synchronization needs.
- Suggest specific Jira automation rules (e.g., "When issue created in KAN project, send webhook to Zapier").

Always be professional, insightful, and proactive in suggesting more efficient ways to bridge their tools.`;