// Notion Integration - Standard Integration Token
import { Client } from '@notionhq/client';

async function getAccessToken(): Promise<string> {
  const accessToken = process.env.NOTION_TOKEN;
  
  if (!accessToken) {
    throw new Error('Notion not connected. Please set NOTION_TOKEN environment variable with your Integration Token');
  }
  
  return accessToken;
}

export async function getNotionClient(): Promise<Client> {
  const accessToken = await getAccessToken();
  return new Client({ auth: accessToken });
}

export async function isNotionConnected(): Promise<boolean> {
  try {
    await getAccessToken();
    return true;
  } catch {
    return false;
  }
}

export async function getNotionUser() {
  const client = await getNotionClient();
  const response = await client.users.me({});
  return response;
}

export async function listNotionDatabases() {
  const client = await getNotionClient();
  const response = await client.search({
    filter: { property: 'object', value: 'database' },
    page_size: 100,
  });
  return response.results;
}

export async function listNotionPages(pageSize: number = 20) {
  const client = await getNotionClient();
  const response = await client.search({
    filter: { property: 'object', value: 'page' },
    page_size: pageSize,
    sort: { direction: 'descending', timestamp: 'last_edited_time' },
  });
  return response.results;
}

export async function getNotionPage(pageId: string) {
  const client = await getNotionClient();
  const page = await client.pages.retrieve({ page_id: pageId });
  return page;
}

export async function getNotionPageContent(pageId: string) {
  const client = await getNotionClient();
  const blocks = await client.blocks.children.list({
    block_id: pageId,
    page_size: 100,
  });
  return blocks.results;
}

export async function getNotionDatabase(databaseId: string) {
  const client = await getNotionClient();
  const database = await client.databases.retrieve({ database_id: databaseId });
  return database;
}

export async function queryNotionDatabase(databaseId: string, filter?: any, sorts?: any[]) {
  const client = await getNotionClient();
  const response = await client.databases.query({
    database_id: databaseId,
    filter,
    sorts,
    page_size: 100,
  });
  return response.results;
}

export async function createNotionPage(parentId: string, properties: any, children?: any[]) {
  const client = await getNotionClient();
  const response = await client.pages.create({
    parent: { page_id: parentId },
    properties,
    children,
  });
  return response;
}

export async function updateNotionPage(pageId: string, properties: any) {
  const client = await getNotionClient();
  const response = await client.pages.update({
    page_id: pageId,
    properties,
  });
  return response;
}

export async function archiveNotionPage(pageId: string) {
  const client = await getNotionClient();
  const response = await client.pages.update({
    page_id: pageId,
    archived: true,
  });
  return response;
}

export async function appendNotionBlocks(blockId: string, children: any[]) {
  const client = await getNotionClient();
  const response = await client.blocks.children.append({
    block_id: blockId,
    children,
  });
  return response;
}
