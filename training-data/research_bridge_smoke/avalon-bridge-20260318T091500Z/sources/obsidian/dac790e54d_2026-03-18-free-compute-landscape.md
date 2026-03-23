# Free Compute Landscape (March 2026)

> Research brief for SCBE multi-agent worker-node deployment.
> Compiled 2026-03-18.

---

## Executive Summary

There are **10+ free compute surfaces** available in 2026 that can serve as worker nodes in a multi-agent system. The strongest options for GPU work are **Google Colab** (T4, 12 hr sessions), **Kaggle** (T4/P100, 30 hr/week with background execution), and **Lightning AI** (free GPU credits with persistent storage). For always-on CPU workers, **Oracle Cloud** (4 OCPU ARM, 24 GB RAM, truly free forever) is the clear winner. Browser automation via Playwright works on Colab and Lightning AI in headless mode.

---

## Tier 1: Free GPU Compute (Training & Inference)

### 1. Google Colab (Free Tier)

| Attribute | Value |
|-----------|-------|
| **GPU** | NVIDIA T4 (15 GB VRAM) -- not guaranteed |
| **RAM** | ~12.7 GB system RAM |
| **Disk** | ~78 GB ephemeral |
| **Session limit** | 12 hours max runtime |
| **Idle timeout** | 90 minutes of inactivity = disconnect |
| **Daily quota** | ~12 hours GPU time (unpublished, varies by load) |
| **Background exec** | No -- tab must stay open |
| **Playwright** | YES -- headless Chromium works. Install with `!pip install playwright && !playwright install chromium` |
| **API access** | Full Python environment, pip install anything |
| **Best for** | Prototyping, short training runs, browser agent tasks |

**Key gotcha**: GPU availability is not guaranteed. During peak hours you may get CPU-only. Usage is throttled if you consume too much in recent sessions.

**References**:
- [Google Colab FAQ](https://research.google.com/colaboratory/faq.html)
- [Colab GPU Guide (Hivenet)](https://compute.hivenet.com/post/google-colaboratory-gpu-complete-guide-to-free-cloud-gpu-access-and-limitations)
- [Running Playwright on Colab (DataGuru)](https://dataguru.cc/blog/how-to-run-playwright-on-google-colab/)
- [Browser-Driven AI in Colab with Playwright (MarkTechPost)](https://www.marktechpost.com/2025/04/20/an-advanced-coding-implementation-mastering-browser%E2%80%91driven-ai-in-google-colab-with-playwright-browser_use-agent-browsercontext-langchain-and-gemini/)

---

### 2. Kaggle Notebooks

| Attribute | Value |
|-----------|-------|
| **GPU** | NVIDIA T4 x2 or P100 (16 GB VRAM) |
| **RAM** | ~13 GB system RAM |
| **Disk** | 20 GB persistent storage |
| **Weekly quota** | 30 hours/week GPU time |
| **Session limit** | 9 hours max per session |
| **Background exec** | YES -- can close browser, notebook keeps running |
| **Playwright** | Likely works (headless), but untested officially |
| **API access** | Full Python, pip install, Kaggle Datasets API |
| **Best for** | Longer training runs, background execution, dataset access |

**Key advantage**: Background execution is the killer feature. Start a 9-hour training job, close browser, come back later. Combined with 30 hr/week quota, this is the best free GPU for sustained work.

**Key gotcha**: Notebooks are public by default on free tier. Use Kaggle Secrets for API keys.

**References**:
- [Kaggle Efficient GPU Usage](https://www.kaggle.com/docs/efficient-gpu-usage)
- [Free Cloud GPUs for Students 2026](https://freerdps.com/blog/free-cloud-gpus-for-students/)
- [GMI Cloud Free GPU Guide 2026](https://www.gmicloud.ai/blog/where-can-i-get-free-gpu-cloud-trials-in-2026-a-complete-guide)

---

### 3. Lightning AI Studios

| Attribute | Value |
|-----------|-------|
| **GPU** | Available (type varies, typically T4) |
| **Credits** | 15 Lightning credits/month free |
| **GPU hours** | ~7 free GPU hours (after phone verification) |
| **CPU** | 32-core CPU Studio free |
| **Storage** | 100 GB persistent (10 GB Drive free) |
| **Session limit** | 4-hour restarts on free plan |
| **Background exec** | YES -- unlimited background execution |
| **Playwright** | YES -- full Linux environment, install anything |
| **API access** | Full environment, SSH, VS Code integration |
| **Best for** | Development environment, IDE-like workflow, persistent projects |

**Key advantage**: Persistent storage (100 GB) and background execution make this excellent for iterative work. Connects to local IDE.

**References**:
- [Lightning AI Studios](https://lightning.ai/studio)
- [Lightning AI Billing FAQ](https://lightning.ai/docs/overview/faq/billing)
- [Using Lightning AI Studio For Free (KDnuggets)](https://www.kdnuggets.com/using-lightning-ai-studio-for-free)
- [Free Lightning AI CI/CD GPU Runners (Medium)](https://medium.com/@jakub.drzymala.blog/use-free-lightning-ai-ci-cd-gpu-runners-for-your-ml-project-mlops-chronicles-1-3-e69617d6b954)

---

### 4. Hugging Face Spaces (ZeroGPU)

| Attribute | Value |
|-----------|-------|
| **GPU** | NVIDIA H200 slice (~70 GB VRAM) -- dynamic allocation |
| **Cost** | Free for all users (ZeroGPU) |
| **Session model** | On-demand: GPU allocated when request arrives, released when idle |
| **Storage** | Ephemeral per Space |
| **Background exec** | No -- request-driven |
| **Playwright** | Not practical (Spaces are containerized apps) |
| **API access** | Gradio/Streamlit app interface, HF Inference API |
| **Best for** | Inference demos, model serving, on-demand GPU bursts |

**Key advantage**: H200 hardware with 70 GB VRAM is extraordinarily powerful for free. Perfect for inference tasks. PRO plan ($9/month) gives 8x quota.

**Key limitation**: Not designed for long training runs. Best for inference and short GPU bursts.

**References**:
- [Spaces ZeroGPU Documentation](https://huggingface.co/docs/hub/en/spaces-zerogpu)
- [Hugging Face Pricing](https://huggingface.co/pricing)
- [ZeroGPU on Hugging Face (Medium)](https://thamizhelango.medium.com/zerogpu-on-hugging-face-run-open-models-for-almost-free-2a3c9d87fcdf)

---

### 5. Paperspace Gradient (Community Notebooks)

| Attribute | Value |
|-----------|-------|
| **GPU** | NVIDIA M4000 (8 GB VRAM) or T4 (availability varies) |
| **RAM** | ~30 GB system RAM |
| **Session limit** | 6 hours per session (unlimited restarts) |
| **Storage** | Persistent across sessions |
| **Background exec** | Limited |
| **Playwright** | Possible in headless mode |
| **API access** | Full Jupyter environment |
| **Best for** | ML experimentation, Jupyter workflows |

**Key gotcha**: Limited GPU pool. Sessions may queue during peak hours. Now owned by DigitalOcean.

**References**:
- [Paperspace Gradient Community Notebooks](https://blog.paperspace.com/paperspace-launches-gradient-community-notebooks/)
- [Paperspace Pricing](https://www.paperspace.com/pricing)
- [Gradient vs Kaggle Comparison](https://blog.paperspace.com/gradient-kaggle-notebook-comparison/)

---

### 6. Saturn Cloud

| Attribute | Value |
|-----------|-------|
| **GPU** | Up to 16 GB GPU instances |
| **Free hours** | 10-30 hours/month (GPU Jupyter) + 3 hours Dask |
| **CPU** | Up to 64 GB CPU instances |
| **Storage** | Persistent |
| **Background exec** | Yes |
| **Playwright** | Possible |
| **Best for** | Dask parallel computing, data science workflows |

**References**:
- [Saturn Cloud Free Compute](https://saturncloud.io/blog/saturn-cloud-offers-free-compute-time/)
- [Saturn Cloud 150 Free Hours Announcement](https://saturncloud.io/blog/150-free-hours/)
- [Saturn Cloud Plans](https://saturncloud.io/plans/saturn_cloud_plans/)

---

## Tier 2: Free CPU Compute (Always-On Workers)

### 7. Oracle Cloud (Always-Free ARM)

| Attribute | Value |
|-----------|-------|
| **CPU** | 4 OCPUs (Ampere A1 ARM) |
| **RAM** | 24 GB total |
| **Instances** | Up to 4 VMs (split resources flexibly) |
| **Storage** | 200 GB block volume |
| **GPU** | None on free tier |
| **Duration** | FOREVER -- truly always-free, no 12-month expiry |
| **Playwright** | YES -- full Linux VM, install anything |
| **API access** | Full SSH, any software |
| **Best for** | Always-on agent workers, relay nodes, API servers, browser automation fleet |

**This is the crown jewel for multi-agent systems.** 4 OCPUs + 24 GB RAM running 24/7 forever for free. Can run Playwright, Node.js, Python, Docker, anything. Split into 4 separate VMs for 4 independent agent workers.

**Setup tip**: Use `VM.Standard.A1.Flex` shape. Select Ampere processor. Availability can be limited in popular regions -- try less popular regions or keep retrying.

**References**:
- [Oracle Cloud Free Tier](https://www.oracle.com/cloud/free/)
- [Oracle Cloud Free Tier FAQ](https://www.oracle.com/cloud/free/faq/)
- [Always Free Resources Documentation](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm)
- [How to Get 3 Free Lifetime Servers (Orendra)](https://orendra.com/blog/how-to-get-free-lifetime-servers-4-core-arm-24gb-ram-more/)

---

### 8. Google Cloud (e2-micro)

| Attribute | Value |
|-----------|-------|
| **CPU** | 2 shared vCPU (e2-micro) |
| **RAM** | 1 GB |
| **Instances** | 1 non-preemptible instance |
| **Storage** | 30 GB standard persistent disk |
| **GPU** | None |
| **Duration** | Always-free (no expiry) |
| **Regions** | US only: Oregon (us-west1), Iowa (us-central1), South Carolina (us-east1) |
| **Playwright** | Tight with 1 GB RAM -- possible but fragile |
| **Best for** | Lightweight relay, health checks, coordination API |

**References**:
- [Google Cloud Free Features](https://docs.cloud.google.com/free/docs/free-cloud-features)
- [GCP Compute Getting Started](https://cloud.google.com/free/docs/compute-getting-started)

---

### 9. AWS Free Tier

| Attribute | Value |
|-----------|-------|
| **CPU** | t2.micro or t3.micro (1 vCPU, 1 GB RAM) |
| **Hours** | 750 hours/month (enough for 1 instance 24/7) |
| **Duration** | 12 months from signup (NOT always-free) |
| **Storage** | 30 GB EBS |
| **GPU** | None on free tier |
| **Data transfer** | 100 GB/month outbound (always-free across all services) |
| **Playwright** | Possible with t3.micro |
| **Best for** | Temporary worker nodes, integration testing |

**Key gotcha**: Expires after 12 months. After that, you pay. Create new accounts periodically (with different email) to extend, but this violates ToS.

**Also notable**: AWS also offers Lambda (1M free requests/month, always-free) and SageMaker Studio Lab (free, no AWS account needed, 4hr GPU sessions).

**References**:
- [AWS Free Tier](https://aws.amazon.com/free/)
- [AWS Free Tier FAQ](https://aws.amazon.com/free/free-tier-faqs/)
- [How to Use AWS Free Tier Effectively](https://oneuptime.com/blog/post/2026-02-12-use-aws-free-tier-effectively/view)

---

### 10. GitHub Codespaces

| Attribute | Value |
|-----------|-------|
| **CPU** | 2-core (smallest), up to 32-core |
| **Hours** | 120 core-hours/month = 60 clock hours on 2-core |
| **RAM** | 8 GB (on 2-core) |
| **Storage** | 15 GB |
| **GPU** | None |
| **Playwright** | YES -- Docker-based, full Linux |
| **Best for** | Development, CI/CD, short-lived agent tasks |

**References**:
- [GitHub Codespaces Billing](https://docs.github.com/billing/managing-billing-for-github-codespaces/about-billing-for-github-codespaces)
- [GitHub Codespaces Features](https://github.com/features/codespaces)

---

### 11. Replit (Starter Plan)

| Attribute | Value |
|-----------|-------|
| **CPU** | 1 vCPU shared |
| **RAM** | 512 MB - 2 GB |
| **Storage** | ~2 GB |
| **Sleep** | After 5 minutes of inactivity |
| **Always-on** | NOT available on free tier (Core plan, $20/month) |
| **Playwright** | Tight -- RAM too low for reliable browser automation |
| **Deployment** | 1 free published app, expires after 30 days |
| **Best for** | Quick prototyping, NOT production workers |

**References**:
- [Replit Free Tier Limits](https://www.p0stman.com/guides/replit-limitations/)
- [Replit Pricing 2026](https://www.wearefounders.uk/replit-pricing-what-you-actually-pay-to-build-apps/)

---

## Tier 3: Free GPU Credits (One-Time / Trial)

| Platform | Credits | GPU | Duration | Notes |
|----------|---------|-----|----------|-------|
| **Google Cloud** | $300 | Any (T4, V100, A100) | 90 days | New accounts only |
| **Microsoft Azure** | $200 | Any | 30 days | New accounts only |
| **RunPod** | $5-10 | Any available | Until spent | New accounts |
| **Vast.ai** | None free | Marketplace from $0.15/hr | Pay-as-go | Cheapest spot GPUs |
| **Modal Labs** | $30/month free | Serverless GPU | Monthly | Great DX, Python SDK |
| **Beam Cloud** | Free tier available | Serverless GPU | Monthly | Hot-reloading containers |

**References**:
- [Free Cloud GPU Credits Worth $250k+ (Thunder Compute)](https://www.thundercompute.com/blog/free-cloud-gpu-credits)
- [GMI Cloud Free GPU Guide 2026](https://www.gmicloud.ai/blog/where-can-i-get-free-gpu-cloud-trials-in-2026-a-complete-guide)
- [Top Serverless GPU Clouds 2026 (RunPod)](https://www.runpod.io/articles/guides/top-serverless-gpu-clouds)

---

## Multi-Agent Deployment Strategy

### Recommended Stack (All Free)

```
ALWAYS-ON WORKERS (CPU):
  Oracle Cloud ARM x4 VMs    --> 4 agent workers, 24/7, Playwright capable
  Google Cloud e2-micro x1   --> coordination API / health monitor

GPU BURST (Training):
  Kaggle Notebooks            --> 30 hr/week, background exec, P100/T4
  Google Colab                --> 12 hr sessions, T4, Playwright OK
  Lightning AI                --> 7 hr GPU + persistent 100 GB storage

INFERENCE:
  HuggingFace ZeroGPU         --> H200 slices, on-demand, free
  Modal Labs ($30/mo free)    --> Serverless GPU, great for API endpoints

DEVELOPMENT:
  GitHub Codespaces           --> 60 hours/month, full IDE
  Lightning AI Studios        --> Persistent dev environment
```

### Total Free Compute Budget (Monthly)

| Resource | Amount |
|----------|--------|
| Always-on CPU (Oracle) | 4 OCPU + 24 GB RAM, 24/7/365 |
| GPU training (Kaggle) | ~120 hrs/month (30 hr/week x 4) |
| GPU training (Colab) | ~360 hrs/month (12 hr/day x 30) |
| GPU inference (HF ZeroGPU) | Unlimited short bursts |
| GPU dev (Lightning AI) | ~7 hrs/month |
| CPU dev (Codespaces) | 60 hrs/month |
| Ephemeral CPU (GCP e2-micro) | 24/7 |

### Playwright / Browser Automation Compatibility

| Platform | Playwright Works? | Notes |
|----------|-------------------|-------|
| Oracle Cloud ARM | YES | Full Linux VM, install anything |
| Google Colab | YES | `!pip install playwright && !playwright install chromium` |
| Lightning AI | YES | Full Linux environment |
| GitHub Codespaces | YES | Docker-based, full control |
| Kaggle | LIKELY | Untested officially, but full Linux kernel |
| GCP e2-micro | FRAGILE | Only 1 GB RAM, headless only |
| Replit | NO | Too little RAM |
| HF Spaces | NO | Containerized app model |

---

## Stacking Strategy for SCBE Multi-Agent Fleet

1. **Provision Oracle Cloud ARM** -- 4 VMs as permanent agent relay nodes
2. **Deploy coordination API** on GCP e2-micro (always-free)
3. **Schedule GPU training** on Kaggle (background exec, 30 hr/week)
4. **Use Colab** for interactive prototyping and Playwright browser tasks
5. **Serve inference** through HuggingFace ZeroGPU Spaces
6. **Develop** in Lightning AI Studios or GitHub Codespaces
7. **Stack trial credits** (GCP $300 + Azure $200 + RunPod $10) for burst capacity

This gives you a 24/7 multi-agent fleet with periodic GPU training bursts, all at zero cost.
