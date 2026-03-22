# SCBE App Store & Cross-Platform Strategy

## 1. Product Vision
Transform the "Aether Browser" and "SCBE Security" into a unified, downloadable application for iOS, Android, and Desktop (macOS/Windows/Linux).

### Similar Products
- **Kimi / Grok:** AI-powered research assistants.
- **Comet Browser:** Privacy-focused browsing.

## 2. Technology Stack (Free Tier Optimized)

### Frontend (The App)
- **Framework:** **Flutter** (Dart).
  - *Why?* Single codebase for Mobile + Desktop. High performance.
  - *UI Library:* Material 3 or Cupertino (iOS style).

### Backend (The Brain)
- **Compute:** **Google Cloud Run** (2M requests/month free) or **Oracle Cloud** (4 ARM Cores, 24GB RAM free).
  - *Why?* Zero cost for high performance.
- **Database:** **Supabase** (PostgreSQL).
  - *Why?* Free tier includes Auth, Database, and Realtime.
- **AI Models:** **Hugging Face Inference API** (Free Tier) or Local LLMs (Ollama) if running on user's device.

## 3. Monetization Strategy (Beyond Gumroad)

### In-App Purchases (IAP)
To be allowed on the App Store, you **must** use Apple/Google billing for digital goods.
- **Solution:** **RevenueCat**.
  - *Cost:* Free up to $10k/month revenue.
  - *Features:* Handles subscriptions, trials, and cross-platform syncing.

### Tiers
- **Free:** Basic browsing + SCBE Layer 1-5 security.
- **Pro ($9.99/mo):** **Hydra Swarm Mode**.
  - Access to the 6-agent "Sacred Tongues" swarm.
  - Deep research with Byzantine Fault Tolerance (self-correcting AI).
  - Full 14-Layer Security.
- **Enterprise:** Custom deployment (High Ticket).

## 4. Implementation Plan

### Step 1: The Wrapper
Create a Flutter app that wraps the existing `aether-browser` logic (running on a server) or reimplements the UI.

### Step 2: The Gateway
Deploy the SCBE Python backend (`src/api/main.py`) to Google Cloud Run.
- *Action:* Use `deploy-gke.yml` as a template for Cloud Run.

### Step 3: The Payment
Integrate RevenueCat SDK into the Flutter app.

## 5. Deployment Pipeline
1.  **Code:** `feat/app-store-flutter` branch.
2.  **Build:** GitHub Actions (`flutter-build.yml`).
3.  **Deploy:**
    - **Android:** Google Play Console (via Fastlane).
    - **iOS:** TestFlight (via Fastlane).
    - **Desktop:** GitHub Releases.
