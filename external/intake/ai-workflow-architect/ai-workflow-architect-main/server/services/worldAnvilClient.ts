// World Anvil Integration - API Key from Replit Secrets
// API Docs: https://www.worldanvil.com/api/external/boromir/documentation

const WORLD_ANVIL_API_BASE = 'https://www.worldanvil.com/api/external/boromir';

function getApiKey(): string {
  const apiKey = process.env.WORLD_ANVIL_API_KEY;
  if (!apiKey) {
    throw new Error('WORLD_ANVIL_API_KEY not set. Add it in Secrets tab.');
  }
  return apiKey;
}

async function worldAnvilRequest(endpoint: string, options: RequestInit = {}) {
  const apiKey = getApiKey();
  const url = `${WORLD_ANVIL_API_BASE}${endpoint}`;
  
  const response = await fetch(url, {
    ...options,
    headers: {
      'Authorization': `Bearer ${apiKey}`,
      'Accept': 'application/json',
      'Content-Type': 'application/json',
      'x-application-key': apiKey,
      ...options.headers,
    },
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`World Anvil API error: ${response.status} - ${error}`);
  }

  return response.json();
}

export async function isWorldAnvilConnected(): Promise<boolean> {
  try {
    getApiKey();
    return true;
  } catch {
    return false;
  }
}

export async function getWorldAnvilUser() {
  return worldAnvilRequest('/user');
}

export async function listWorldAnvilWorlds() {
  return worldAnvilRequest('/user/worlds');
}

export async function getWorld(worldId: string) {
  return worldAnvilRequest(`/world/${worldId}`);
}

export async function listWorldArticles(worldId: string, limit: number = 25, offset: number = 0) {
  return worldAnvilRequest(`/world/${worldId}/articles?limit=${limit}&offset=${offset}`);
}

export async function getArticle(articleId: string) {
  return worldAnvilRequest(`/article/${articleId}`);
}

export async function listWorldCategories(worldId: string) {
  return worldAnvilRequest(`/world/${worldId}/categories`);
}

export async function getCategory(categoryId: string) {
  return worldAnvilRequest(`/category/${categoryId}`);
}

export async function listWorldMaps(worldId: string) {
  return worldAnvilRequest(`/world/${worldId}/maps`);
}

export async function getMap(mapId: string) {
  return worldAnvilRequest(`/map/${mapId}`);
}

export async function listWorldTimelines(worldId: string) {
  return worldAnvilRequest(`/world/${worldId}/timelines`);
}

export async function getTimeline(timelineId: string) {
  return worldAnvilRequest(`/timeline/${timelineId}`);
}

export async function searchArticles(worldId: string, query: string) {
  return worldAnvilRequest(`/world/${worldId}/articles/search?term=${encodeURIComponent(query)}`);
}
