/**
 * @file zoom.ts
 * @module conference/api/services
 *
 * Zoom Meeting SDK integration for live conference sessions.
 *
 * Uses Zoom's REST API to create/manage meetings for each demo day.
 * Curators get host privileges; investors and coders join as attendees.
 * NDA-gated: only NDA-signed investors receive the join link.
 *
 * Requires env vars: ZOOM_ACCOUNT_ID, ZOOM_CLIENT_ID, ZOOM_CLIENT_SECRET
 * Uses Server-to-Server OAuth (no user login needed).
 *
 * @see https://developers.zoom.us/docs/meeting-sdk/
 */

// ═══════════════════════════════════════════════════════════════
// Types
// ═══════════════════════════════════════════════════════════════

export interface ZoomConfig {
  accountId: string;
  clientId: string;
  clientSecret: string;
}

export interface ZoomMeeting {
  id: number;
  joinUrl: string;
  startUrl: string;
  password: string;
  topic: string;
  /** Zoom host user email (curator) */
  hostEmail: string;
  createdAt: string;
}

export interface ZoomTokenCache {
  accessToken: string;
  expiresAt: number;
}

// ═══════════════════════════════════════════════════════════════
// Zoom Service
// ═══════════════════════════════════════════════════════════════

export class ZoomService {
  private config: ZoomConfig | null;
  private tokenCache: ZoomTokenCache | null = null;
  /** In-memory meeting store: conferenceId -> ZoomMeeting */
  meetings: Map<string, ZoomMeeting> = new Map();

  constructor() {
    const accountId = process.env.ZOOM_ACCOUNT_ID;
    const clientId = process.env.ZOOM_CLIENT_ID;
    const clientSecret = process.env.ZOOM_CLIENT_SECRET;

    if (accountId && clientId && clientSecret) {
      this.config = { accountId, clientId, clientSecret };
    } else {
      this.config = null;
    }
  }

  /** Whether Zoom credentials are configured */
  isConfigured(): boolean {
    return this.config !== null;
  }

  /**
   * Get an OAuth access token via Server-to-Server OAuth.
   * Tokens are cached until expiry.
   */
  private async getAccessToken(): Promise<string> {
    if (!this.config) throw new Error('Zoom not configured');

    if (this.tokenCache && Date.now() < this.tokenCache.expiresAt - 60_000) {
      return this.tokenCache.accessToken;
    }

    const credentials = Buffer.from(
      `${this.config.clientId}:${this.config.clientSecret}`
    ).toString('base64');

    const res = await fetch('https://zoom.us/oauth/token', {
      method: 'POST',
      headers: {
        Authorization: `Basic ${credentials}`,
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: new URLSearchParams({
        grant_type: 'account_credentials',
        account_id: this.config.accountId,
      }),
    });

    if (!res.ok) {
      const text = await res.text();
      throw new Error(`Zoom OAuth failed: ${res.status} ${text}`);
    }

    const data = (await res.json()) as { access_token: string; expires_in: number };
    this.tokenCache = {
      accessToken: data.access_token,
      expiresAt: Date.now() + data.expires_in * 1000,
    };

    return data.access_token;
  }

  /**
   * Create a Zoom meeting for a conference/demo day.
   *
   * @param conferenceId - Internal conference ID
   * @param topic - Meeting title
   * @param startTime - ISO 8601 start time
   * @param durationMinutes - Meeting duration
   * @param hostEmail - Zoom user email for the host (curator)
   */
  async createMeeting(
    conferenceId: string,
    topic: string,
    startTime: string,
    durationMinutes: number,
    hostEmail: string
  ): Promise<ZoomMeeting> {
    // If Zoom isn't configured, return a simulated meeting for dev/demo
    if (!this.config) {
      const simulated: ZoomMeeting = {
        id: Math.floor(Math.random() * 9_000_000_000) + 1_000_000_000,
        joinUrl: `https://zoom.us/j/simulated-${conferenceId.slice(0, 8)}`,
        startUrl: `https://zoom.us/s/simulated-${conferenceId.slice(0, 8)}`,
        password: Math.random().toString(36).slice(2, 8),
        topic,
        hostEmail,
        createdAt: new Date().toISOString(),
      };
      this.meetings.set(conferenceId, simulated);
      return simulated;
    }

    const token = await this.getAccessToken();
    const res = await fetch(`https://api.zoom.us/v2/users/${hostEmail}/meetings`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        topic,
        type: 2, // Scheduled meeting
        start_time: startTime,
        duration: durationMinutes,
        timezone: 'UTC',
        settings: {
          join_before_host: false,
          mute_upon_entry: true,
          waiting_room: true,
          meeting_authentication: false,
          auto_recording: 'cloud',
        },
      }),
    });

    if (!res.ok) {
      const text = await res.text();
      throw new Error(`Zoom create meeting failed: ${res.status} ${text}`);
    }

    const data = (await res.json()) as {
      id: number;
      join_url: string;
      start_url: string;
      password: string;
    };

    const meeting: ZoomMeeting = {
      id: data.id,
      joinUrl: data.join_url,
      startUrl: data.start_url,
      password: data.password,
      topic,
      hostEmail,
      createdAt: new Date().toISOString(),
    };

    this.meetings.set(conferenceId, meeting);
    return meeting;
  }

  /**
   * Get the Zoom meeting for a conference.
   * Returns null if no meeting has been created.
   */
  getMeeting(conferenceId: string): ZoomMeeting | null {
    return this.meetings.get(conferenceId) ?? null;
  }

  /**
   * Get the join URL for an investor (NDA-gated).
   * The join URL includes the password so investors don't need to enter it manually.
   */
  getJoinUrl(conferenceId: string): string | null {
    const meeting = this.meetings.get(conferenceId);
    return meeting?.joinUrl ?? null;
  }

  /**
   * Get the host/start URL for curators.
   */
  getStartUrl(conferenceId: string): string | null {
    const meeting = this.meetings.get(conferenceId);
    return meeting?.startUrl ?? null;
  }
}

/** Singleton Zoom service instance */
export const zoomService = new ZoomService();
