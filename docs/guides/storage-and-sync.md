# Storage & Sync (Bring-Your-Own-Storage)

Learn how to synchronize your Netflix Narc configuration and Evidence Locker data across multiple devices using your own private storage backend.

## Overview

**netflix-narc** is built on a **Bring-Your-Own-Storage (BYOS)** architecture. Your viewing history analysis, custom weights, and manual Evidence Locker dossiers remain entirely under your control—stored either locally or on your personal cloud storage.

Supported storage and sync backends:

| Backend | Provider Options | Best For |
|---------|------------------|----------|
| **Disabled (`off`)** | None | Single machine, local privacy |
| **Local Folder (`local_folder`)** | iCloud Drive, Dropbox, OneDrive, local directory | Multi-Mac users with cloud desktop sync |
| **S3 Storage (`s3`)** | Cloudflare R2, AWS S3, MinIO, Wasabi | Power users, self-hosters, multi-platform |
| **WebDAV (`webdav`)** | Nextcloud, ownCloud, Fastmail | Self-hosted cloud storage users |

---

## 1. Local Folder / Cloud Drive (`local_folder`)

Ideal for synchronizing data across Macs using **iCloud Drive**, **Dropbox**, **OneDrive**, or a shared local network mount.

### Configuration

In the TUI, select **Local Folder** under storage options, or add the following variables to your config file (`~/.config/netflix-narc/.env`):

```ini
SYNC_BACKEND=local_folder
SYNC_LOCAL_PATH=/Users/username/Library/Mobile Documents/com~apple~CloudDocs/netflix-narc
```

> [!TIP]
> **iCloud Drive Path**: On macOS, iCloud Drive folders are located at `/Users/<username>/Library/Mobile Documents/com~apple~CloudDocs/`.

---

## 2. S3-Compatible Object Storage (`s3`)

Supports any standard S3-compatible service:

- **Cloudflare R2** (Recommended: 10GB free storage, 0 egress fees)
- **AWS S3**
- **MinIO** (Self-hosted)
- **Wasabi**

### Configuration

```ini
SYNC_BACKEND=s3
SYNC_S3_ENDPOINT_URL=https://<account_id>.r2.cloudflarestorage.com
SYNC_S3_BUCKET=netflix-narc-sync
SYNC_S3_ACCESS_KEY_ID=your_access_key_id
SYNC_S3_SECRET_ACCESS_KEY=your_secret_access_key
```

---

## 3. WebDAV / Nextcloud / ownCloud (`webdav`)

Ideal for users running **Nextcloud**, **ownCloud**, or standard WebDAV services.

### Configuration

```ini
SYNC_BACKEND=webdav
SYNC_WEBDAV_URL=https://nextcloud.example.com/remote.php/dav/files/username/netflix-narc/
SYNC_WEBDAV_USERNAME=your_username
SYNC_WEBDAV_PASSWORD=your_app_password
```

> [!IMPORTANT]
> When using Nextcloud or ownCloud, we recommend generating a dedicated **App Password** under Security Settings rather than using your primary account password.

---

## Configuring & Testing Sync in the TUI

You can set up and test your storage backend visually inside the application:

1. Press `s` to open **Preferences** (or launch `a` → **Advanced Options**).
2. Scroll to the **Storage & Sync** section.
3. Select your preferred **Backend Type**.
4. Fill in the required endpoint, credentials, or path fields.
5. Click **Test Connection**. **netflix-narc** will execute a test handshake to confirm read/write permissions.
6. Click **Save** to write the configuration to `~/.config/netflix-narc/.env`.

---

## How Syncing & Merging Works

When sync is enabled:

1. **Automatic Local-to-Remote Sync**: On application startup and after key edits (such as updating an Evidence Locker record), **netflix-narc** checks the remote manifest.
2. **Last-Write-Wins (LWW) Conflict Resolution**: Title dossiers and settings are merged granularly based on UTC timestamps. Modifying title *A* on machine 1 and title *B* on machine 2 merges cleanly without losing data.
3. **Offline Safety**: If network access is lost, **netflix-narc** continues operating against local storage and syncs when connectivity is restored.
