# Secret Source Bootstrapping (Wave 1)

- I confirmed API credentials are present in local repo env files: `.env` and `.env.gumroad`.
- GitHub secret values themselves are not readable via GitHub API, so we treat repo-local env as the source of truth for bootstrap.
- I imported available secrets into the local SCBE secret store (tokenized):
  - `HF_TOKEN`
  - `GUMROAD_API_TOKEN`
  - `GITHUB_TOKEN`

## Immediate state (last checked)
- `money_ops` status now shows:
  - `HF token: set`
  - `Gumroad token: set`
  - `Stripe token: missing`
- Ready providers changed from `2/20` to `4/20` after loading `HF_TOKEN` and `GUMROAD_API_TOKEN` into local store.

## How to refresh from local env files
```powershell
Set-Location C:/Users/issda/SCBE-AETHERMOORE
# Import supported secret names from .env and .env.gumroad into local secret store (tokenized)
python - <<'PY'
from pathlib import Path
from src.security.secret_store import set_secret

def parse_env(path: Path):
    data = {}
    if not path.exists():
        return data
    for raw in path.read_text(encoding='utf-8').splitlines():
        line = raw.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        k, v = [x.strip() for x in line.split('=', 1)]
        if k and v and not v.startswith('REPLACE_ME'):
            data[k] = v
    return data

keys = {
    'HF_TOKEN', 'GUMROAD_API_TOKEN', 'STRIPE_SECRET_KEY', 'STRIPE_API_KEY',
    'GITHUB_TOKEN', 'GH_TOKEN', 'GITHUB_PAT',
    'GROQ_API_KEY', 'CEREBRAS_API_KEY', 'MISTRAL_API_KEY', 'OPENROUTER_API_KEY',
    'GOOGLE_AI_API_KEY', 'COHERE_API_KEY', 'CLOUDFLARE_API_KEY', 'TOGETHER_API_KEY',
    'SAMBANOVA_API_KEY', 'DEEPINFRA_API_KEY', 'NVIDIA_API_KEY', 'NOVITA_API_KEY',
    'FIREWORKS_API_KEY', 'XAI_API_KEY', 'ANTHROPIC_API_KEY', 'OPENAI_API_KEY',
    'HUGGINGFACE_TOKEN'
}

found = []
for fp in [Path('.env'), Path('.env.gumroad')]:
    for k, v in parse_env(fp).items():
        if k in keys:
            set_secret(k, v, note=f'wave1-import:{fp}', tongue='ko')
            found.append(k)
print('Imported:', ','.join(sorted(set(found))))
PY
```

## Money ops commands
- Check status:
  - `python scripts/money_ops.py status`
- Run Wave 1 content + marketplace + probe:
  - `python scripts/money_ops.py run --spin --spin-topic ai_governance --spin-depth 2 --marketplace --probe`
- Set final Stripe key if available and rerun with:
  - `python scripts/money_ops.py run --push-hf`
