import { Client } from '@microsoft/microsoft-graph-client';

async function getAccessToken(): Promise<string> {
  const accessToken = process.env.ONEDRIVE_ACCESS_TOKEN;
  
  if (!accessToken) {
    throw new Error('OneDrive not connected. Please set ONEDRIVE_ACCESS_TOKEN environment variable');
  }
  
  return accessToken;
}

export async function getOneDriveClient(): Promise<Client> {
  const accessToken = await getAccessToken();
  return Client.initWithMiddleware({
    authProvider: {
      getAccessToken: async () => accessToken
    }
  });
}

export async function isOneDriveConnected(): Promise<boolean> {
  try {
    await getAccessToken();
    return true;
  } catch {
    return false;
  }
}

export async function getOneDriveUser() {
  const client = await getOneDriveClient();
  return await client.api('/me').get();
}

export async function listOneDriveFiles(folderId?: string, pageSize: number = 20) {
  const client = await getOneDriveClient();
  const path = folderId 
    ? `/me/drive/items/${folderId}/children`
    : '/me/drive/root/children';
  
  const response = await client.api(path)
    .top(pageSize)
    .orderby('lastModifiedDateTime desc')
    .get();
  
  return response.value || [];
}

export async function getOneDriveFile(fileId: string) {
  const client = await getOneDriveClient();
  return await client.api(`/me/drive/items/${fileId}`).get();
}

export async function downloadOneDriveFile(fileId: string): Promise<ArrayBuffer> {
  const client = await getOneDriveClient();
  return await client.api(`/me/drive/items/${fileId}/content`).get();
}

export async function uploadOneDriveFile(
  name: string, 
  content: Buffer, 
  folderId?: string
) {
  const client = await getOneDriveClient();
  const path = folderId 
    ? `/me/drive/items/${folderId}:/${name}:/content`
    : `/me/drive/root:/${name}:/content`;
  
  return await client.api(path)
    .put(content);
}

export async function createOneDriveFolder(name: string, parentFolderId?: string) {
  const client = await getOneDriveClient();
  const path = parentFolderId 
    ? `/me/drive/items/${parentFolderId}/children`
    : '/me/drive/root/children';
  
  return await client.api(path)
    .post({
      name,
      folder: {},
      '@microsoft.graph.conflictBehavior': 'rename'
    });
}

export async function deleteOneDriveFile(fileId: string) {
  const client = await getOneDriveClient();
  await client.api(`/me/drive/items/${fileId}`).delete();
  return { success: true };
}

export async function getOneDriveStorageQuota() {
  const client = await getOneDriveClient();
  const drive = await client.api('/me/drive').get();
  return drive.quota;
}
