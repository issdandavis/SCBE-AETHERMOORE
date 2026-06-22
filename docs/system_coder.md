# System Coder Runner

`system_coder` is the repeatable runner for the deterministic-first code-agent stack.

```powershell
python -m python.helm.system_coder `
  --task tests\fixtures\system_coder_tasks.jsonl `
  --spec configs\system_coder.spec.yaml `
  --run-id smoke `
  --out C:\tmp\system_coder\report.json `
  --sft-out C:\tmp\system_coder\train.jsonl
```

Each task closes through one of the verified rungs:

- `deterministic`: direct tool dispatch or calculator.
- `reference`: verified reference bank fallback.
- `model`: first model attempt verified by tests.
- `repair`: later attempt verified after an earlier miss.
- `known_logic`: known answer/process packet.
- `answer_stage`: fixed answer contract with checkpoint scoring.
- `escalate`: no verified answer, so nothing is falsely shipped.

The core invariant is `false_success_count == 0`.

Task JSONL supports these shapes:

```json
{"id":"prime10","kind":"agent","input":"what is the 10th prime?"}
{"id":"code","kind":"agent","input":"Write add(a,b).","tests":["assert add(2,2)==4"],"model_outputs":["def add(a,b): return a*b","def add(a,b): return a+b"]}
{"id":"known","kind":"known_logic","tool":"prime_membership","payload":{"n":97},"model_output":"prime"}
{"id":"stage","kind":"answer_stage","task":{"stage_id":"s","domain":"physics","prompt":"20m/4s","expected_answer":"5","required_process_tokens":["20/4"],"units":"m/s"},"attempt":{"text":"ANSWER: 5\nPROCESS: 20/4\nCHECK: ok\nUNITS: m/s\nCONFIDENCE: high"}}
```

The runner writes one checkpoint receipt per task and optional SFT rows for later training.
