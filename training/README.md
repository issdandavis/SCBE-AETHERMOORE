# training/ — moved

This directory was extracted from the monolith and now lives in its own repo:

**→ https://github.com/issdandavis/scbe-training-lab**

The `scbe-training-lab` repo contains the former `training/` tree — QLoRA configs, Vertex/HF training scripts, dataset ingest pipelines, SFT records, the 21D PHDM embedding training rig, and the federated orchestrator. This is the repo ML engineers should clone on HuggingFace / Colab without pulling the whole framework.

Install:
```bash
git clone https://github.com/issdandavis/scbe-training-lab.git
```

The full pre-split state of SCBE-AETHERMOORE is preserved at tag `v-monolith-final` in this repo — checkout with `git checkout v-monolith-final`.
