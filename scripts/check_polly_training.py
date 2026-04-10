"""Quick training progress checker — run anytime to see current state."""
import re, sys, os

LOG_PATTERN = "artifacts/training/polly-v2-run*.log"

def check(logfile):
    with open(logfile, 'r', errors='replace') as f:
        text = f.read()

    blocks = re.findall(r'\{[^}]*loss[^}]*\}', text)
    pbar = re.findall(r'(\d+)/(\d+)\s*\[', text)

    if not pbar:
        print(f"No progress bar found in {logfile}")
        return

    step, total = int(pbar[-1][0]), int(pbar[-1][1])
    pct = step / total * 100
    print(f"\n{'='*60}")
    print(f"POLLY V2 TRAINING — {logfile}")
    print(f"{'='*60}")
    print(f"Progress: {step}/{total} ({pct:.1f}%)")

    train_blocks = []
    eval_blocks = []
    for b in blocks:
        d = eval(b)
        if 'eval_loss' in d:
            eval_blocks.append(d)
        else:
            train_blocks.append(d)

    print(f"\nTrain metrics: {len(train_blocks)}, Eval metrics: {len(eval_blocks)}")

    if train_blocks:
        first = train_blocks[0]
        last = train_blocks[-1]
        print(f"\n  First: loss={first['loss']}, acc={first.get('mean_token_accuracy','?')}")
        print(f"  Latest: loss={last['loss']}, acc={last.get('mean_token_accuracy','?')}, epoch={last.get('epoch','?')}")

        # Check for convergence
        if len(train_blocks) >= 5:
            recent = [float(t['loss']) for t in train_blocks[-5:]]
            avg = sum(recent) / len(recent)
            print(f"  Avg last 5: loss={avg:.4f}")

    if eval_blocks:
        print(f"\n  Eval results:")
        for e in eval_blocks:
            print(f"    eval_loss={e['eval_loss']}, epoch={e.get('epoch','?')}")

    # Check for errors
    if 'error' in text.lower() or 'OOM' in text or 'CUDA error' in text:
        errors = re.findall(r'(?i)(error|oom|cuda error)[^\n]*', text)
        if errors:
            print(f"\n  WARNINGS: {len(errors)} error-like lines found")
            for e in errors[-3:]:
                print(f"    {e[:100]}")

    # Check for completion
    if 'Training complete!' in text:
        print(f"\n  *** TRAINING COMPLETE ***")

    print(f"{'='*60}")


if __name__ == "__main__":
    import glob
    logfile = sys.argv[1] if len(sys.argv) > 1 else None
    if not logfile:
        logs = sorted(glob.glob("artifacts/training/polly-v2-run*.log"), key=os.path.getmtime, reverse=True)
        if logs:
            logfile = logs[0]
        else:
            print("No training logs found")
            sys.exit(1)
    check(logfile)
