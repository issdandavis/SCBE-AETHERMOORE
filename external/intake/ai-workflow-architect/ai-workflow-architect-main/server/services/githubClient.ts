/**
 * GitHub Client - Uses GitHub Personal Access Token
 * Provides authenticated access to GitHub API via Octokit
 */
import { Octokit } from '@octokit/rest';

async function getAccessToken(): Promise<string> {
  const accessToken = process.env.GITHUB_TOKEN;
  
  if (!accessToken) {
    throw new Error('GitHub not connected. Please set GITHUB_TOKEN environment variable with your Personal Access Token');
  }
  
  return accessToken;
}

// WARNING: Never cache this client.
// Access tokens expire, so a new client must be created each time.
// Always call this function again to get a fresh client.
export async function getGitHubClient(): Promise<Octokit> {
  const accessToken = await getAccessToken();
  return new Octokit({ auth: accessToken });
}

// Get the authenticated user's info
export async function getAuthenticatedUser() {
  const octokit = await getGitHubClient();
  const { data } = await octokit.users.getAuthenticated();
  return data;
}

// Create a new repository
export async function createRepository(name: string, options: {
  description?: string;
  private?: boolean;
  autoInit?: boolean;
} = {}) {
  const octokit = await getGitHubClient();
  const { data } = await octokit.repos.createForAuthenticatedUser({
    name,
    description: options.description,
    private: options.private ?? false,
    auto_init: options.autoInit ?? true,
  });
  return data;
}

// Get repository info
export async function getRepository(owner: string, repo: string) {
  const octokit = await getGitHubClient();
  const { data } = await octokit.repos.get({ owner, repo });
  return data;
}

// Create or update a file in a repository
export async function createOrUpdateFile(
  owner: string,
  repo: string,
  path: string,
  content: string,
  message: string,
  branch: string = 'main',
  sha?: string
) {
  const octokit = await getGitHubClient();
  const { data } = await octokit.repos.createOrUpdateFileContents({
    owner,
    repo,
    path,
    message,
    content: Buffer.from(content).toString('base64'),
    branch,
    sha,
  });
  return data;
}

// Get file content from repository
export async function getFileContent(owner: string, repo: string, path: string, ref?: string) {
  const octokit = await getGitHubClient();
  try {
    const { data } = await octokit.repos.getContent({
      owner,
      repo,
      path,
      ref,
    });
    return data;
  } catch (error: any) {
    if (error.status === 404) {
      return null;
    }
    throw error;
  }
}

// Create a new branch
export async function createBranch(owner: string, repo: string, branchName: string, fromRef: string = 'main') {
  const octokit = await getGitHubClient();
  
  // Get the SHA of the source branch
  const { data: refData } = await octokit.git.getRef({
    owner,
    repo,
    ref: `heads/${fromRef}`,
  });
  
  // Create new branch
  const { data } = await octokit.git.createRef({
    owner,
    repo,
    ref: `refs/heads/${branchName}`,
    sha: refData.object.sha,
  });
  return data;
}

// Create a pull request
export async function createPullRequest(
  owner: string,
  repo: string,
  title: string,
  body: string,
  head: string,
  base: string = 'main'
) {
  const octokit = await getGitHubClient();
  const { data } = await octokit.pulls.create({
    owner,
    repo,
    title,
    body,
    head,
    base,
  });
  return data;
}

// List repositories for authenticated user
export async function listRepositories() {
  const octokit = await getGitHubClient();
  const { data } = await octokit.repos.listForAuthenticatedUser({
    sort: 'updated',
    per_page: 100,
  });
  return data;
}
