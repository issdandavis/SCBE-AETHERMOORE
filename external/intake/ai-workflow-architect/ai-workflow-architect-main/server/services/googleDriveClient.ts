import { google } from 'googleapis';

let oauth2Client: any = null;

async function getAccessToken(): Promise<string> {
  // Use standard Google OAuth2 with environment variables
  const clientId = process.env.GOOGLE_DRIVE_CLIENT_ID;
  const clientSecret = process.env.GOOGLE_DRIVE_CLIENT_SECRET;
  const refreshToken = process.env.GOOGLE_DRIVE_REFRESH_TOKEN;
  const accessToken = process.env.GOOGLE_DRIVE_ACCESS_TOKEN;

  if (!clientId || !clientSecret) {
    throw new Error('Google Drive credentials not configured. Please set GOOGLE_DRIVE_CLIENT_ID and GOOGLE_DRIVE_CLIENT_SECRET');
  }

  // If we have a direct access token, use it
  if (accessToken) {
    return accessToken;
  }

  // Otherwise, use refresh token to get new access token
  if (!refreshToken) {
    throw new Error('Google Drive not connected. Please set GOOGLE_DRIVE_REFRESH_TOKEN or GOOGLE_DRIVE_ACCESS_TOKEN');
  }

  if (!oauth2Client) {
    oauth2Client = new google.auth.OAuth2(clientId, clientSecret);
    oauth2Client.setCredentials({ refresh_token: refreshToken });
  }

  const { credentials } = await oauth2Client.refreshAccessToken();
  return credentials.access_token;
}

export async function getGoogleDriveClient() {
  const accessToken = await getAccessToken();
  const oauth2Client = new google.auth.OAuth2();
  oauth2Client.setCredentials({ access_token: accessToken });
  return google.drive({ version: 'v3', auth: oauth2Client });
}

export async function isGoogleDriveConnected(): Promise<boolean> {
  try {
    await getAccessToken();
    return true;
  } catch {
    return false;
  }
}

export async function listDriveFiles(folderId?: string, pageSize: number = 20) {
  const drive = await getGoogleDriveClient();
  const response = await drive.files.list({
    pageSize,
    q: folderId ? `'${folderId}' in parents and trashed = false` : "trashed = false",
    fields: 'nextPageToken, files(id, name, mimeType, size, createdTime, modifiedTime, webViewLink, iconLink, thumbnailLink)',
    orderBy: 'modifiedTime desc',
  });
  return response.data.files || [];
}

export async function getDriveFile(fileId: string) {
  const drive = await getGoogleDriveClient();
  const response = await drive.files.get({
    fileId,
    fields: 'id, name, mimeType, size, createdTime, modifiedTime, webViewLink, iconLink, parents',
  });
  return response.data;
}

export async function downloadDriveFile(fileId: string): Promise<Buffer> {
  const drive = await getGoogleDriveClient();
  const response = await drive.files.get(
    { fileId, alt: 'media' },
    { responseType: 'arraybuffer' }
  );
  return Buffer.from(response.data as ArrayBuffer);
}

export async function uploadDriveFile(name: string, content: Buffer, mimeType: string, folderId?: string) {
  const drive = await getGoogleDriveClient();
  const { Readable } = await import('stream');
  const readable = new Readable();
  readable.push(content);
  readable.push(null);
  
  const requestBody: any = { name };
  if (folderId) {
    requestBody.parents = [folderId];
  }

  const response = await drive.files.create({
    requestBody,
    media: {
      mimeType,
      body: readable,
    },
    fields: 'id, name, mimeType, size, webViewLink',
  });
  return response.data;
}

export async function createDriveFolder(name: string, parentFolderId?: string) {
  const drive = await getGoogleDriveClient();
  const requestBody: any = {
    name,
    mimeType: 'application/vnd.google-apps.folder',
  };
  if (parentFolderId) {
    requestBody.parents = [parentFolderId];
  }
  
  const response = await drive.files.create({
    requestBody,
    fields: 'id, name, mimeType, webViewLink',
  });
  return response.data;
}

export async function deleteDriveFile(fileId: string) {
  const drive = await getGoogleDriveClient();
  await drive.files.delete({ fileId });
  return { success: true };
}

export async function getDriveStorageQuota() {
  const drive = await getGoogleDriveClient();
  const response = await drive.about.get({
    fields: 'storageQuota',
  });
  return response.data.storageQuota;
}
