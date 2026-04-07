# How Claude Remembers Your Project

> Source: https://code.claude.com/docs/en/memory

Give Claude persistent instructions with CLAUDE.md files, and let Claude accumulate learnings automatically with auto memory.

Each Claude Code session begins with a fresh context window. Two mechanisms carry knowledge across sessions:

* **CLAUDE.md files**: instructions you write to give Claude persistent context
* **Auto memory**: notes Claude writes itself based on your corrections and preferences

## CLAUDE.md vs auto memory

|                      | CLAUDE.md files                                   | Auto memory                                                      |
| :------------------- | :------------------------------------------------ | :--------------------------------------------------------------- |
| **Who writes it**    | You                                               | Claude                                                           |
| **What it contains** | Instructions and rules                            | Learnings and patterns                                           |
| **Scope**            | Project, user, or org                             | Per working tree                                                 |
| **Loaded into**      | Every session                                     | Every session (first 200 lines or 25KB)                          |
| **Use for**          | Coding standards, workflows, project architecture | Build commands, debugging insights, preferences Claude discovers |

## CLAUDE.md files

CLAUDE.md files are markdown files that give Claude persistent instructions for a project, your personal workflow, or your entire organization.

### Choose where to put CLAUDE.md files

| Scope                    | Location                                                                                                | Purpose                                                    | Shared with                     |
| ------------------------ | ------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------- | ------------------------------- |
| **Managed policy**       | macOS: `/Library/Application Support/ClaudeCode/CLAUDE.md`, Linux/WSL: `/etc/claude-code/CLAUDE.md`, Windows: `C:\Program Files\ClaudeCode\CLAUDE.md` | Organization-wide instructions managed by IT/DevOps        | All users in organization       |
| **Project instructions** | `./CLAUDE.md` or `./.claude/CLAUDE.md`                                                                  | Team-shared instructions for the project                   | Team members via source control |
| **User instructions**    | `~/.claude/CLAUDE.md`                                                                                   | Personal preferences for all projects                      | Just you (all projects)         |
| **Local instructions**   | `./CLAUDE.local.md`                                                                                     | Personal project-specific preferences; add to `.gitignore` | Just you (current project)      |

### Set up a project CLAUDE.md

Run `/init` to generate a starting CLAUDE.md automatically. Claude analyzes your codebase and creates a file with build commands, test instructions, and project conventions it discovers.

Set `CLAUDE_CODE_NEW_INIT=1` to enable an interactive multi-phase flow.

### Write effective instructions

**Size**: target under 200 lines per CLAUDE.md file.

**Structure**: use markdown headers and bullets to group related instructions.

**Specificity**: write instructions that are concrete enough to verify:
* "Use 2-space indentation" instead of "Format code properly"
* "Run `npm test` before committing" instead of "Test your changes"
* "API handlers live in `src/api/handlers/`" instead of "Keep files organized"

**Consistency**: if two rules contradict each other, Claude may pick one arbitrarily.

### Import additional files

CLAUDE.md files can import additional files using `@path/to/import` syntax. Both relative and absolute paths are allowed. Maximum depth of five hops.

```text
See @README for project overview and @package.json for available npm commands.

# Additional Instructions
- git workflow @docs/git-instructions.md
```

For private per-project preferences, create a `CLAUDE.local.md` at the project root and add it to `.gitignore`.

### AGENTS.md

Claude Code reads `CLAUDE.md`, not `AGENTS.md`. If your repository already uses `AGENTS.md`, create a `CLAUDE.md` that imports it:

```markdown
@AGENTS.md

## Claude Code
Use plan mode for changes under `src/billing/`.
```

### How CLAUDE.md files load

Claude Code reads CLAUDE.md files by walking up the directory tree from your current working directory. All discovered files are concatenated into context. Within each directory, `CLAUDE.local.md` is appended after `CLAUDE.md`.

Claude also discovers `CLAUDE.md` and `CLAUDE.local.md` files in subdirectories under your current working directory on demand.

Block-level HTML comments (`<!-- maintainer notes -->`) are stripped before injection into context.

#### Load from additional directories

```bash
CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD=1 claude --add-dir ../shared-config
```

### Organize rules with `.claude/rules/`

Place markdown files in your project's `.claude/rules/` directory. Each file should cover one topic:

```text
your-project/
├── .claude/
│   ├── CLAUDE.md
│   └── rules/
│       ├── code-style.md
│       ├── testing.md
│       └── security.md
```

#### Path-specific rules

Rules can be scoped to specific files using YAML frontmatter:

```markdown
---
paths:
  - "src/api/**/*.ts"
---

# API Development Rules
- All API endpoints must include input validation
- Use the standard error response format
```

| Pattern                | Matches                                  |
| ---------------------- | ---------------------------------------- |
| `**/*.ts`              | All TypeScript files in any directory    |
| `src/**/*`             | All files under `src/` directory         |
| `*.md`                 | Markdown files in the project root       |
| `src/components/*.tsx` | React components in a specific directory |

#### Share rules across projects with symlinks

```bash
ln -s ~/shared-claude-rules .claude/rules/shared
ln -s ~/company-standards/security.md .claude/rules/security.md
```

#### User-level rules

Personal rules in `~/.claude/rules/` apply to every project on your machine.

### Manage CLAUDE.md for large teams

#### Deploy organization-wide CLAUDE.md

Deploy at the managed policy location using MDM, Group Policy, Ansible, or similar tools.

#### Exclude specific CLAUDE.md files

```json
{
  "claudeMdExcludes": [
    "**/monorepo/CLAUDE.md",
    "/home/user/monorepo/other-team/.claude/rules/**"
  ]
}
```

Managed policy CLAUDE.md files cannot be excluded.

## Auto memory

Auto memory lets Claude accumulate knowledge across sessions without you writing anything. Claude saves notes for itself as it works.

### Enable or disable auto memory

Auto memory is on by default. Toggle with `/memory` or set in project settings:

```json
{
  "autoMemoryEnabled": false
}
```

Or set `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`.

### Storage location

Each project gets its own memory directory at `~/.claude/projects/<project>/memory/`.

```text
~/.claude/projects/<project>/memory/
├── MEMORY.md          # Concise index, loaded into every session
├── debugging.md       # Detailed notes on debugging patterns
├── api-conventions.md # API design decisions
└── ...
```

### How it works

The first 200 lines of `MEMORY.md`, or the first 25KB, whichever comes first, are loaded at the start of every conversation. Topic files are read on demand.

### Audit and edit your memory

Auto memory files are plain markdown you can edit or delete at any time. Run `/memory` to browse.

## View and edit with `/memory`

The `/memory` command lists all CLAUDE.md, CLAUDE.local.md, and rules files loaded in your current session.

## Troubleshoot memory issues

### Claude isn't following my CLAUDE.md

* Run `/memory` to verify files are being loaded
* Check file location
* Make instructions more specific
* Look for conflicting instructions

### I don't know what auto memory saved

Run `/memory` and select the auto memory folder.

### My CLAUDE.md is too large

Move detailed content into separate files with `@path` imports or split across `.claude/rules/` files.

### Instructions seem lost after `/compact`

CLAUDE.md fully survives compaction. If an instruction disappeared, it was given only in conversation. Add it to CLAUDE.md to persist.
