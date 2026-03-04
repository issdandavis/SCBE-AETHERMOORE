// Mock database for testing without real database connection
export const db = new Proxy({} as any, {
  get(_target, prop) {
    console.log(`Mock DB call: ${String(prop)}`);
    return () => Promise.resolve([]);
  }
});

export async function testDatabaseConnection(): Promise<boolean> {
  console.log('Using mock database - no real connection needed');
  return true;
}