import { drizzle } from 'drizzle-orm/better-sqlite3';
import Database from 'better-sqlite3';
import * as schema from "@shared/schema";

let dbInstance: ReturnType<typeof drizzle> | null = null;

function getDatabase() {
  if (!dbInstance) {
    const sqlite = new Database('ai_workflow.db');
    dbInstance = drizzle(sqlite, { schema });
  }
  return dbInstance;
}

export const db = new Proxy({} as ReturnType<typeof drizzle>, {
  get(_target, prop) {
    const database = getDatabase();
    return (database as any)[prop];
  }
});

export async function testDatabaseConnection(): Promise<boolean> {
  try {
    const database = getDatabase();
    // Simple test query
    database.run('SELECT 1');
    return true;
  } catch (error) {
    console.error('Database connection test failed:', error);
    return false;
  }
}