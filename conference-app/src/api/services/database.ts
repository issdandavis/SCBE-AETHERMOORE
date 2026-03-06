/**
 * @file database.ts
 * @module conference/api/services
 *
 * SQLite database layer. Replaces in-memory Maps with persistent storage.
 * Uses better-sqlite3 for synchronous, fast access (no ORM overhead).
 *
 * Tables: users, organizations, conferences, conference_slots, projects,
 *         ndas, soft_commits, deal_rooms, org_members
 *
 * Migrations run automatically on startup.
 */

import Database from 'better-sqlite3';
import { resolve } from 'path';

const DB_PATH = process.env.DATABASE_PATH ?? resolve(process.cwd(), 'data', 'conference.db');

let db: Database.Database;

export function getDb(): Database.Database {
  if (!db) {
    // Ensure data directory exists
    const dir = resolve(DB_PATH, '..');
    const fs = require('fs');
    if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });

    db = new Database(DB_PATH);
    db.pragma('journal_mode = WAL');
    db.pragma('foreign_keys = ON');
    runMigrations(db);
  }
  return db;
}

function runMigrations(db: Database.Database): void {
  db.exec(`
    CREATE TABLE IF NOT EXISTS migrations (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL UNIQUE,
      applied_at TEXT NOT NULL DEFAULT (datetime('now'))
    );
  `);

  const applied = new Set(
    db.prepare('SELECT name FROM migrations').all().map((r: any) => r.name)
  );

  for (const m of MIGRATIONS) {
    if (!applied.has(m.name)) {
      db.exec(m.sql);
      db.prepare('INSERT INTO migrations (name) VALUES (?)').run(m.name);
      console.log(`[db] Applied migration: ${m.name}`);
    }
  }
}

const MIGRATIONS = [
  {
    name: '001_users',
    sql: `
      CREATE TABLE users (
        id TEXT PRIMARY KEY,
        email TEXT NOT NULL UNIQUE,
        display_name TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('coder', 'investor', 'curator')),
        password_hash TEXT NOT NULL,
        avatar_url TEXT,
        kyc_status TEXT,
        wallet_address TEXT,
        stripe_customer_id TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
      );
      CREATE INDEX idx_users_email ON users(email);
    `,
  },
  {
    name: '002_organizations',
    sql: `
      CREATE TABLE organizations (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        slug TEXT NOT NULL UNIQUE,
        owner_id TEXT NOT NULL REFERENCES users(id),
        plan TEXT NOT NULL DEFAULT 'starter' CHECK(plan IN ('starter', 'growth', 'enterprise')),
        branding_json TEXT NOT NULL DEFAULT '{}',
        governance_json TEXT NOT NULL DEFAULT '{}',
        zoom_config_json TEXT,
        api_key TEXT NOT NULL UNIQUE,
        stripe_subscription_id TEXT,
        stripe_price_id TEXT,
        usage_conferences INTEGER NOT NULL DEFAULT 0,
        usage_projects INTEGER NOT NULL DEFAULT 0,
        usage_soft_commits INTEGER NOT NULL DEFAULT 0,
        usage_funding_volume INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
      );
      CREATE INDEX idx_orgs_slug ON organizations(slug);
      CREATE INDEX idx_orgs_api_key ON organizations(api_key);
      CREATE INDEX idx_orgs_owner ON organizations(owner_id);
    `,
  },
  {
    name: '003_org_members',
    sql: `
      CREATE TABLE org_members (
        id TEXT PRIMARY KEY,
        org_id TEXT NOT NULL REFERENCES organizations(id),
        user_id TEXT NOT NULL REFERENCES users(id),
        role TEXT NOT NULL CHECK(role IN ('owner', 'admin', 'curator', 'viewer')),
        added_at TEXT NOT NULL DEFAULT (datetime('now')),
        UNIQUE(org_id, user_id)
      );
      CREATE INDEX idx_org_members_org ON org_members(org_id);
      CREATE INDEX idx_org_members_user ON org_members(user_id);
    `,
  },
  {
    name: '004_projects',
    sql: `
      CREATE TABLE projects (
        id TEXT PRIMARY KEY,
        scbe_id TEXT NOT NULL,
        org_id TEXT REFERENCES organizations(id),
        creator_id TEXT NOT NULL REFERENCES users(id),
        title TEXT NOT NULL,
        tagline TEXT NOT NULL,
        description TEXT NOT NULL,
        tech_stack_json TEXT NOT NULL DEFAULT '[]',
        repo_url TEXT,
        demo_url TEXT,
        video_url TEXT,
        pitch_deck_url TEXT,
        funding_ask_json TEXT NOT NULL DEFAULT '{}',
        status TEXT NOT NULL DEFAULT 'draft',
        governance_json TEXT,
        hydra_audit_json TEXT,
        submitted_at TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at TEXT NOT NULL DEFAULT (datetime('now'))
      );
      CREATE INDEX idx_projects_creator ON projects(creator_id);
      CREATE INDEX idx_projects_org ON projects(org_id);
      CREATE INDEX idx_projects_status ON projects(status);
    `,
  },
  {
    name: '005_conferences',
    sql: `
      CREATE TABLE conferences (
        id TEXT PRIMARY KEY,
        org_id TEXT REFERENCES organizations(id),
        title TEXT NOT NULL,
        theme TEXT NOT NULL,
        description TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'scheduled',
        scheduled_at TEXT NOT NULL,
        duration INTEGER NOT NULL DEFAULT 120,
        stream_url TEXT,
        zoom_json TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
      );
      CREATE INDEX idx_conferences_org ON conferences(org_id);
      CREATE INDEX idx_conferences_status ON conferences(status);

      CREATE TABLE conference_slots (
        id TEXT PRIMARY KEY,
        conference_id TEXT NOT NULL REFERENCES conferences(id),
        project_id TEXT NOT NULL REFERENCES projects(id),
        slot_order INTEGER NOT NULL,
        duration_minutes INTEGER NOT NULL DEFAULT 15,
        pitch_minutes INTEGER NOT NULL DEFAULT 10,
        qa_minutes INTEGER NOT NULL DEFAULT 5,
        status TEXT NOT NULL DEFAULT 'upcoming'
      );
      CREATE INDEX idx_slots_conference ON conference_slots(conference_id);
    `,
  },
  {
    name: '006_ndas',
    sql: `
      CREATE TABLE ndas (
        id TEXT PRIMARY KEY,
        investor_id TEXT NOT NULL REFERENCES users(id),
        project_id TEXT,
        org_id TEXT REFERENCES organizations(id),
        template_id TEXT NOT NULL DEFAULT 'platform-v1',
        status TEXT NOT NULL DEFAULT 'pending',
        envelope_id TEXT,
        signed_at TEXT,
        expires_at TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
      );
      CREATE INDEX idx_ndas_investor ON ndas(investor_id);
      CREATE INDEX idx_ndas_project ON ndas(project_id);
    `,
  },
  {
    name: '007_funding',
    sql: `
      CREATE TABLE soft_commits (
        id TEXT PRIMARY KEY,
        investor_id TEXT NOT NULL REFERENCES users(id),
        project_id TEXT NOT NULL REFERENCES projects(id),
        conference_id TEXT NOT NULL REFERENCES conferences(id),
        amount INTEGER NOT NULL,
        tier TEXT NOT NULL,
        interest_level TEXT NOT NULL DEFAULT 'interested',
        note TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
      );
      CREATE INDEX idx_commits_conference ON soft_commits(conference_id);
      CREATE INDEX idx_commits_project ON soft_commits(project_id);
      CREATE INDEX idx_commits_investor ON soft_commits(investor_id);

      CREATE TABLE deal_rooms (
        id TEXT PRIMARY KEY,
        project_id TEXT NOT NULL REFERENCES projects(id),
        org_id TEXT REFERENCES organizations(id),
        investor_ids_json TEXT NOT NULL DEFAULT '[]',
        documents_json TEXT NOT NULL DEFAULT '[]',
        status TEXT NOT NULL DEFAULT 'open',
        total_soft_commits INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
      );
      CREATE INDEX idx_deal_rooms_project ON deal_rooms(project_id);
    `,
  },
  {
    name: '008_refresh_tokens',
    sql: `
      CREATE TABLE refresh_tokens (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL REFERENCES users(id),
        token_hash TEXT NOT NULL UNIQUE,
        expires_at TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
      );
      CREATE INDEX idx_refresh_user ON refresh_tokens(user_id);
      CREATE INDEX idx_refresh_hash ON refresh_tokens(token_hash);
    `,
  },
];

/** Close the database connection (for tests/graceful shutdown) */
export function closeDb(): void {
  if (db) {
    db.close();
    db = undefined!;
  }
}
