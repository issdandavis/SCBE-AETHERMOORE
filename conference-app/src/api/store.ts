/**
 * @file store.ts
 * @module conference/api/store
 *
 * In-memory data store for MVP. Replace with Postgres in production.
 */

import type {
  User,
  ProjectCapsule,
  NDARecord,
  Conference,
  SoftCommit,
  DealRoom,
} from '../shared/types/index.js';

class Store {
  users: Map<string, User> = new Map();
  projects: Map<string, ProjectCapsule> = new Map();
  ndas: Map<string, NDARecord> = new Map();
  conferences: Map<string, Conference> = new Map();
  softCommits: Map<string, SoftCommit> = new Map();
  dealRooms: Map<string, DealRoom> = new Map();
  /** email -> userId for login lookups */
  emailIndex: Map<string, string> = new Map();
  /** investorId -> Set<projectId> for NDA lookups */
  investorNdaIndex: Map<string, Set<string>> = new Map();

  getUser(id: string): User | undefined {
    return this.users.get(id);
  }

  getUserByEmail(email: string): User | undefined {
    const id = this.emailIndex.get(email);
    return id ? this.users.get(id) : undefined;
  }

  setUser(user: User): void {
    this.users.set(user.id, user);
    this.emailIndex.set(user.email, user.id);
  }

  getProject(id: string): ProjectCapsule | undefined {
    return this.projects.get(id);
  }

  listProjects(filter?: { status?: string; creatorId?: string }): ProjectCapsule[] {
    let results = Array.from(this.projects.values());
    if (filter?.status) results = results.filter(p => p.status === filter.status);
    if (filter?.creatorId) results = results.filter(p => p.creatorId === filter.creatorId);
    return results.sort((a, b) => b.createdAt.localeCompare(a.createdAt));
  }

  setProject(project: ProjectCapsule): void {
    this.projects.set(project.id, project);
  }

  hasSignedNda(investorId: string, projectId: string | null): boolean {
    const key = projectId ?? '__platform__';
    return this.investorNdaIndex.get(investorId)?.has(key) ?? false;
  }

  setNda(nda: NDARecord): void {
    this.ndas.set(nda.id, nda);
    if (nda.status === 'signed') {
      const key = nda.projectId ?? '__platform__';
      if (!this.investorNdaIndex.has(nda.investorId)) {
        this.investorNdaIndex.set(nda.investorId, new Set());
      }
      this.investorNdaIndex.get(nda.investorId)!.add(key);
    }
  }

  listSoftCommits(filter?: { projectId?: string; conferenceId?: string; investorId?: string }): SoftCommit[] {
    let results = Array.from(this.softCommits.values());
    if (filter?.projectId) results = results.filter(c => c.projectId === filter.projectId);
    if (filter?.conferenceId) results = results.filter(c => c.conferenceId === filter.conferenceId);
    if (filter?.investorId) results = results.filter(c => c.investorId === filter.investorId);
    return results;
  }
}

export const store = new Store();
