// Unified Storage Hub - Aggregates files from multiple providers
import * as googleDrive from './googleDriveClient';
import * as oneDrive from './oneDriveClient';
import * as dropbox from './dropboxClient';

export type StorageProvider = 'google-drive' | 'onedrive' | 'dropbox' | 'github';

export interface UnifiedFile {
  id: string;
  name: string;
  path?: string;
  isFolder: boolean;
  size?: number;
  mimeType?: string;
  modifiedAt?: string;
  createdAt?: string;
  webViewLink?: string;
  thumbnailLink?: string;
  provider: StorageProvider;
}

export interface ProviderStatus {
  provider: StorageProvider;
  connected: boolean;
  name?: string;
  email?: string;
  spaceUsed?: number;
  spaceTotal?: number;
}

export async function getProviderStatuses(): Promise<ProviderStatus[]> {
  const statuses: ProviderStatus[] = [];

  // Check Google Drive
  try {
    const connected = await googleDrive.isGoogleDriveConnected();
    if (connected) {
      const quota = await googleDrive.getDriveStorageQuota();
      statuses.push({
        provider: 'google-drive',
        connected: true,
        spaceUsed: parseInt(quota?.usage || '0'),
        spaceTotal: parseInt(quota?.limit || '0'),
      });
    } else {
      statuses.push({ provider: 'google-drive', connected: false });
    }
  } catch {
    statuses.push({ provider: 'google-drive', connected: false });
  }

  // Check OneDrive
  try {
    const connected = await oneDrive.isOneDriveConnected();
    if (connected) {
      const quota = await oneDrive.getOneDriveStorageQuota();
      const user = await oneDrive.getOneDriveUser();
      statuses.push({
        provider: 'onedrive',
        connected: true,
        name: user.displayName,
        email: user.mail || user.userPrincipalName,
        spaceUsed: quota?.used || 0,
        spaceTotal: quota?.total || 0,
      });
    } else {
      statuses.push({ provider: 'onedrive', connected: false });
    }
  } catch {
    statuses.push({ provider: 'onedrive', connected: false });
  }

  // Check Dropbox
  try {
    const info = await dropbox.getDropboxAccountInfo();
    statuses.push({
      provider: 'dropbox',
      connected: true,
      name: info.name,
      email: info.email,
      spaceUsed: info.spaceUsed,
      spaceTotal: info.spaceTotal,
    });
  } catch {
    statuses.push({ provider: 'dropbox', connected: false });
  }

  return statuses;
}

export async function listFilesFromProvider(
  provider: StorageProvider,
  folderId?: string
): Promise<UnifiedFile[]> {
  switch (provider) {
    case 'google-drive': {
      const files = await googleDrive.listDriveFiles(folderId, 50);
      return files.map((f: any) => ({
        id: f.id,
        name: f.name,
        isFolder: f.mimeType === 'application/vnd.google-apps.folder',
        size: parseInt(f.size || '0'),
        mimeType: f.mimeType,
        modifiedAt: f.modifiedTime,
        createdAt: f.createdTime,
        webViewLink: f.webViewLink,
        thumbnailLink: f.thumbnailLink,
        provider: 'google-drive' as StorageProvider,
      }));
    }
    case 'onedrive': {
      const files = await oneDrive.listOneDriveFiles(folderId, 50);
      return files.map((f: any) => ({
        id: f.id,
        name: f.name,
        isFolder: !!f.folder,
        size: f.size || 0,
        mimeType: f.file?.mimeType,
        modifiedAt: f.lastModifiedDateTime,
        createdAt: f.createdDateTime,
        webViewLink: f.webUrl,
        provider: 'onedrive' as StorageProvider,
      }));
    }
    case 'dropbox': {
      const files = await dropbox.listDropboxFiles(folderId || '');
      return files.map((f) => ({
        id: f.id,
        name: f.name,
        path: f.path,
        isFolder: f.isFolder,
        size: f.size,
        modifiedAt: f.modifiedAt,
        provider: 'dropbox' as StorageProvider,
      }));
    }
    default:
      return [];
  }
}

export async function downloadFile(
  provider: StorageProvider,
  fileId: string
): Promise<{ data: Buffer; name: string; mimeType: string }> {
  switch (provider) {
    case 'google-drive': {
      const file = await googleDrive.getDriveFile(fileId);
      const data = await googleDrive.downloadDriveFile(fileId);
      return {
        data,
        name: file.name || 'download',
        mimeType: file.mimeType || 'application/octet-stream',
      };
    }
    case 'onedrive': {
      const file = await oneDrive.getOneDriveFile(fileId);
      const data = await oneDrive.downloadOneDriveFile(fileId);
      return {
        data: Buffer.from(data),
        name: file.name || 'download',
        mimeType: file.file?.mimeType || 'application/octet-stream',
      };
    }
    case 'dropbox': {
      return await dropbox.downloadDropboxFile(fileId);
    }
    default:
      throw new Error('Provider not supported');
  }
}

export async function uploadFile(
  provider: StorageProvider,
  folderId: string | undefined,
  fileName: string,
  content: Buffer,
  mimeType: string
): Promise<UnifiedFile> {
  switch (provider) {
    case 'google-drive': {
      const file = await googleDrive.uploadDriveFile(fileName, content, mimeType, folderId);
      return {
        id: file.id!,
        name: file.name!,
        isFolder: false,
        size: parseInt(file.size || '0'),
        mimeType: file.mimeType || mimeType,
        webViewLink: file.webViewLink || undefined,
        provider: 'google-drive',
      };
    }
    case 'onedrive': {
      const file = await oneDrive.uploadOneDriveFile(fileName, content, folderId);
      return {
        id: file.id,
        name: file.name,
        isFolder: false,
        size: file.size,
        mimeType: file.file?.mimeType,
        webViewLink: file.webUrl,
        provider: 'onedrive',
      };
    }
    case 'dropbox': {
      const file = await dropbox.uploadDropboxFile(folderId || '', content, fileName);
      return {
        id: file.id,
        name: file.name,
        path: file.path,
        isFolder: false,
        size: file.size,
        provider: 'dropbox',
      };
    }
    default:
      throw new Error('Provider not supported');
  }
}

export async function createFolder(
  provider: StorageProvider,
  parentFolderId: string | undefined,
  name: string
): Promise<UnifiedFile> {
  switch (provider) {
    case 'google-drive': {
      const folder = await googleDrive.createDriveFolder(name, parentFolderId);
      return {
        id: folder.id!,
        name: folder.name!,
        isFolder: true,
        mimeType: folder.mimeType || undefined,
        webViewLink: folder.webViewLink || undefined,
        provider: 'google-drive',
      };
    }
    case 'onedrive': {
      const folder = await oneDrive.createOneDriveFolder(name, parentFolderId);
      return {
        id: folder.id,
        name: folder.name,
        isFolder: true,
        webViewLink: folder.webUrl,
        provider: 'onedrive',
      };
    }
    case 'dropbox': {
      const folder = await dropbox.createDropboxFolder(parentFolderId || '', name);
      return {
        id: folder.id,
        name: folder.name,
        path: folder.path,
        isFolder: true,
        provider: 'dropbox',
      };
    }
    default:
      throw new Error('Provider not supported');
  }
}

export async function deleteItem(
  provider: StorageProvider,
  fileId: string
): Promise<void> {
  switch (provider) {
    case 'google-drive':
      await googleDrive.deleteDriveFile(fileId);
      break;
    case 'onedrive':
      await oneDrive.deleteOneDriveFile(fileId);
      break;
    case 'dropbox':
      await dropbox.deleteDropboxItem(fileId);
      break;
    default:
      throw new Error('Provider not supported');
  }
}
