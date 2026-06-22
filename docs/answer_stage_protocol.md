# Answer Stage Protocol

This protocol turns "give a clear answer" into a scored stage.

The model receives a checkpoint, a domain, and a fixed answer format. It may choose the process path, but the
score rewards the correct answer, the correct process, proper units, safety gates, and staying within the context
budget. If context usage gets too high or correctness falls below the bar, the run restarts from the checkpoint.

## Output Format

```text
ANSWER: <final value/token>
PROCESS: <known process, equation, or deterministic tool route>
CHECK: <inverse check, unit check, or consistency check>
UNITS: <units or dimensionless>
CONFIDENCE: <low|medium|high and why>
SAFETY: <required for diabetes calculation stages>
```

Diabetes stages are calculation/education only. They do not diagnose, prescribe, or change treatment. If a task asks
for treatment advice, the correct output is an escalation/safety answer unless a verified clinical protocol is supplied
by a separate authoritative tool.

## Scoring

The default score is:

```text
0.40 correctness
0.25 process
0.15 format
0.10 units
0.05 safety
0.05 deliberation time, capped at the stage target
```

The "race arrow" is `arrow_hint`: it points to the next missing section, answer token, process token, or unit. A
complete answer gets `-> FINISH`.

## Checkpoint Rule

Restart from the checkpoint when either condition is true:

```text
context_used / context_budget >= 0.72
score < 0.85
```

This prevents a model from burning context while drifting away from the correct process.

## Repeatable Command

```bash
python -m python.helm.answer_stage \
  --input tests/fixtures/answer_stage_repeat.jsonl \
  --out C:/tmp/answer_stage/report.json \
  --sft-out C:/tmp/answer_stage/sft.jsonl
```

The JSON report contains per-stage scores, checkpoint decisions, and arrow hints. The SFT file teaches the fixed
format and checkpoint behavior.
