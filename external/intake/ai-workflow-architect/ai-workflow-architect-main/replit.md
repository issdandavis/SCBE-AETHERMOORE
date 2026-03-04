# AI Orchestration Hub

## Overview
AI Orchestration Hub is a full-stack, multi-agent AI orchestration platform designed to coordinate various AI providers (e.g., OpenAI, Anthropic, xAI, Perplexity) while offering cost controls, secure integrations, and centralized memory. It empowers teams to manage AI workflows across a suite of connected services such as GitHub, Google Drive, OneDrive, Notion, and Stripe, enhancing productivity and streamlining operations. The platform offers a comprehensive solution for AI-powered website building, workflow automation, and an integrated development environment with features like a YouTube/coding split view and Figma design previews.

## User Preferences
Preferred communication style: Simple, everyday language.

## System Architecture
The platform follows a modern full-stack architecture.

### Frontend
- **Framework**: React 18 with TypeScript
- **Routing**: Wouter for client-side navigation
- **State Management**: TanStack Query (React Query)
- **Styling**: Tailwind CSS v4 with shadcn/ui components (New York style)
- **Animations**: Framer Motion for UI animations
- **Build Tool**: Vite

### Backend
- **Framework**: Express.js with TypeScript
- **Database**: PostgreSQL with Drizzle ORM
- **Session Management**: express-session with connect-pg-simple
- **Security**: Helmet, bcrypt, CORS, rate limiting
- **AI Priority System**: Manages AI provider selection based on cost-effectiveness (HuggingFace, Gemini, Anthropic, xAI, Perplexity).

### UI/UX Decisions
- **Design System**: Shadcn/ui (New York style)
- **Visuals**: Glassmorphism effects, gradient overlays (primary to purple theme), Framer Motion entrance animations, micro-interactions, and resizable split panels.
- **Components**: Includes a comprehensive dashboard (Command Deck), Coding Studio (Monaco editor with YouTube/Figma integration), Agents page, Storage Hub, Integrations page, Settings, Roundtable (multi-AI discussions), Usage tracking, Admin dashboard, System status page, Flight recorder/Audit log viewer, Data export, Workflow builder, Website builder wizard, Shop page with 3-tier pricing, and an AI Art Gallery.

### Feature Specifications
- **Multi-AI Orchestration**: Adapters for Claude, GPT, Grok, Perplexity; Roundtable discussions; Usage tracking and cost estimation; Decision traces with approval workflows.
- **Authentication & Authorization**: Session-based authentication with bcrypt, Role-Based Access Control (owner, admin, member, viewer), 2FA, Recovery Codes, QR Sign-In.
- **Workflows**: Full CRUD for automated workflows with step builders, trigger types (Manual, Schedule, Webhook), and status tracking.
- **Storage Hub**: Unified interface for Google Drive, OneDrive, Dropbox with file browsing, upload/download/delete, and AI-powered search.
- **Website Builder**: A 4-step wizard for planning, designing, building (AI-generated code), and deploying websites.
- **Subscription Management**: Integration with Stripe for 3-tier pricing (Starter, Pro, Team), promo code redemption, and customer portal access.
- **Admin Tools**: Super Admin Dashboard with user management, global stats, and audit log viewer.

## External Dependencies

- **AI Providers**:
  - Anthropic (Claude AI)
  - xAI (Grok)
  - Perplexity AI
  - Google AI (Optional)
  - OpenAI (Implicitly via Replit credits, removed from direct options in cost-optimization)
  - HuggingFace (for free/low-cost AI prioritization)
  - Gemini (for free/low-cost AI prioritization and AI-powered file search)

- **Cloud Storage/Collaboration**:
  - Google Drive
  - OneDrive
  - Notion
  - GitHub
  - Dropbox
  - World Anvil (via API Key)

- **Payment Processing**:
  - Stripe

- **Development Tools/Services**:
  - Figma (for design preview integration)

- **Database**:
  - PostgreSQL

## Future Enhancements (Backlog)

### Priority Tasks
1. **Test All Features** - Run comprehensive e2e tests across all pages and API endpoints
2. **AI Roundtable Self-Review** - Have the AI agents review and provide feedback on the platform
3. **Button Audit** - Ensure all buttons across the app have proper functionality
4. **Music Player** - Add a Pandora-style music player for background productivity music
5. **Practice Codespace** - Create a dedicated code practice area with execution sandbox

### Implementation Notes
- Music player: Consider Spotify Web API, SoundCloud embed, or custom audio player
- Codespace: Leverage existing Monaco editor (@monaco-editor/react) for code editing
- Roundtable: Use the /roundtable page to initiate AI discussions about the platform