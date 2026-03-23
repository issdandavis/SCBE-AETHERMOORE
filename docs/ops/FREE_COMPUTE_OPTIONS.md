# Free & Cheap Compute Options for Overnight Runs

## Truly Free (Zero Cost)

### 1. GitHub Actions (BEST for overnight test suites)
- **Cost**: $0 (2,000 minutes/month free for private repos, unlimited for public)
- **Max runtime**: 6 hours per job
- **CPU**: 2-core, 7GB RAM
- **Setup**: Already authenticated. Just push a workflow file.
- **Best for**: Running the adversarial attack suite, test runners, automated reviews
- **Limitation**: No persistent state between runs (use artifacts)

### 2. Google Cloud e2-micro (BEST for 24/7 services)
- **Cost**: $0/month (always-free tier)
- **Spec**: 2 shared vCPU, 1GB RAM, 30GB disk
- **Setup**: Need `gcloud` CLI. Script exists at `deploy/gcloud/deploy_free_vm.sh`
- **Best for**: Running the SCBE bridge, n8n workflows, persistent services
- **Limitation**: 1GB RAM is tight for ML tasks
- **Status**: Script ready, just need gcloud installed

### 3. Google Colab (BEST for GPU tasks)
- **Cost**: $0 (free tier T4 GPU, ~4hr sessions)
- **Spec**: T4 GPU, 12GB VRAM, 12GB RAM
- **Setup**: Playwright automation exists in `scbe-colab-compute` skill
- **Best for**: Model training, inference, batch processing
- **Limitation**: Sessions timeout, no persistent disk

### 4. Oracle Cloud Free Tier
- **Cost**: $0 forever (truly always-free)
- **Spec**: 2 AMD VMs (1 core, 1GB each) OR 1 ARM VM (4 cores, 24GB!)
- **Best for**: The ARM A1 instance is insanely powerful for free
- **Limitation**: Account approval can be slow. ARM means some Python packages need recompilation.
- **Status**: Not set up yet

### 5. Hetzner Cloud (cheapest paid)
- **Cost**: ~$4/month (CX22: 2 vCPU, 4GB RAM, 40GB SSD)
- **Best for**: Real persistent VM with actual resources
- **Status**: Deploy script exists at `deploy/` for Hetzner

## Quick Setup: GitHub Actions Overnight Runner

This is the fastest path to overnight compute with zero cost:

```yaml
# .github/workflows/overnight-run.yml
name: Overnight Task Runner
on:
  workflow_dispatch:
    inputs:
      task:
        description: 'Task to run'
        required: true
        default: 'test-suite'
        type: choice
        options:
          - test-suite
          - attack-suite
          - book-review
          - training-prep

jobs:
  run:
    runs-on: ubuntu-latest
    timeout-minutes: 360  # 6 hours max
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run overnight task
        env:
          HF_TOKEN: ${{ secrets.HF_TOKEN }}
        run: |
          case "${{ inputs.task }}" in
            test-suite)
              python -m pytest tests/ -v --tb=short
              ;;
            attack-suite)
              python -m pytest tests/adversarial/ -v --tb=short
              ;;
            book-review)
              python scripts/publish/roundtable_review.py --full
              ;;
            training-prep)
              python scripts/training/merge_and_validate.py
              ;;
          esac
      - uses: actions/upload-artifact@v4
        with:
          name: overnight-results
          path: artifacts/
```

## Quick Setup: Oracle Cloud ARM (best free power)

```bash
# Install OCI CLI
pip install oci-cli
oci setup config

# Create free ARM A1 instance (4 cores, 24GB RAM!)
oci compute instance launch \
  --availability-domain "AD-1" \
  --compartment-id $COMPARTMENT_ID \
  --shape "VM.Standard.A1.Flex" \
  --shape-config '{"ocpus":4,"memoryInGBs":24}' \
  --image-id $ORACLE_LINUX_IMAGE \
  --display-name "scbe-overnight-runner"
```

## Recommendation

For TONIGHT: GitHub Actions. Zero setup, zero cost, just push a workflow file.
For PERSISTENT: Oracle Cloud ARM free tier (4 cores, 24GB RAM, $0).
For GPU: Google Colab via Playwright automation (already built).
