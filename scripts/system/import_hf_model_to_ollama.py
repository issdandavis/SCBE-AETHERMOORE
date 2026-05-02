"""Download a Hugging Face causal LM, convert it to GGUF, and import into Ollama.

This is the safer successor path for SCBE's local pair-mode models. The older
``merge_to_gguf.py`` script is adapter-centric and hardcodes an ``F:`` output
lane; this script takes explicit directories and defaults to the verified
GeoSeal harness merged model.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

from huggingface_hub import snapshot_download


DEFAULT_REPO = "issdandavis/scbe-coding-agent-qwen-geoseal-harness-merged-v1"
DEFAULT_OLLAMA_NAME = "scbe-geoseal-coder:0.5b"
DEFAULT_WORK_DIR = Path("C:/SCBE_CACHE/gguf-work")
DEFAULT_GGUF_DIR = Path("C:/SCBE_CACHE/gguf")
DEFAULT_LLAMA_CPP = Path(os.environ.get("LLAMA_CPP_PATH", "C:/tools/llama.cpp"))

SYSTEM_PROMPT = """You are SCBE GeoSeal Coder, a local coding assistant.
Use GeoSeal and deterministic SCBE tools when available. Prefer small, tested
patches, explicit file paths, and concise explanations. If a task requires
Sacred Tongues CA opcodes, route through the deterministic CA planner instead
of inventing byte codes."""

QWEN_CHAT_TEMPLATE = r"""{{- if .Suffix }}<|fim_prefix|>{{ .Prompt }}<|fim_suffix|>{{ .Suffix }}<|fim_middle|>
{{- else if .Messages }}
{{- if or .System .Tools }}<|im_start|>system
{{- if .System }}
{{ .System }}
{{- end }}
{{- if .Tools }}

# Tools

You may call one or more functions to assist with the user query.

You are provided with function signatures within <tools></tools>:
<tools>
{{- range .Tools }}
{"type": "function", "function": {{ .Function }}}
{{- end }}
</tools>

For each function call, return a json object with function name and arguments within <tool_call></tool_call> with NO other text. Do not include any backticks or ```json.
<tool_call>
{"name": <function-name>, "arguments": <args-json-object>}
</tool_call>
{{- end }}<|im_end|>
{{ end }}
{{- range $i, $_ := .Messages }}
{{- $last := eq (len (slice $.Messages $i)) 1 -}}
{{- if eq .Role "user" }}<|im_start|>user
{{ .Content }}<|im_end|>
{{ else if eq .Role "assistant" }}<|im_start|>assistant
{{ if .Content }}{{ .Content }}
{{- else if .ToolCalls }}<tool_call>
{{ range .ToolCalls }}{"name": "{{ .Function.Name }}", "arguments": {{ .Function.Arguments }}}
{{ end }}</tool_call>
{{- end }}{{ if not $last }}<|im_end|>
{{ end }}
{{- else if eq .Role "tool" }}<|im_start|>user
<tool_response>
{{ .Content }}
</tool_response><|im_end|>
{{ end }}
{{- if and (ne .Role "assistant") $last }}<|im_start|>assistant
{{ end }}
{{- end }}
{{- else }}
{{- if .System }}<|im_start|>system
{{ .System }}<|im_end|>
{{ end }}{{ if .Prompt }}<|im_start|>user
{{ .Prompt }}<|im_end|>
{{ end }}<|im_start|>assistant
{{ end }}{{ .Response }}{{ if .Response }}<|im_end|>{{ end }}"""


def run(cmd: list[str], *, cwd: Path | None = None) -> None:
    print("+", " ".join(str(part) for part in cmd))
    subprocess.run(cmd, cwd=str(cwd) if cwd else None, check=True)


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def ensure_llama_cpp(path: Path, *, clone_if_missing: bool) -> Path:
    if path.exists():
        return path
    if not clone_if_missing:
        raise SystemExit(
            f"llama.cpp not found at {path}. Re-run with --clone-llama-cpp or set LLAMA_CPP_PATH."
        )
    ensure_dir(path.parent)
    run(["git", "clone", "--depth", "1", "https://github.com/ggerganov/llama.cpp", str(path)])
    return path


def conversion_script(llama_cpp: Path) -> Path:
    for candidate in (
        llama_cpp / "convert_hf_to_gguf.py",
        llama_cpp / "convert_hf_to_gguf_update.py",
        llama_cpp / "convert.py",
    ):
        if candidate.exists():
            return candidate
    raise SystemExit(f"No HF-to-GGUF conversion script found under {llama_cpp}")


def install_convert_requirements(llama_cpp: Path) -> None:
    candidates = [
        llama_cpp / "requirements" / "requirements-convert_hf_to_gguf.txt",
        llama_cpp / "requirements.txt",
    ]
    for req in candidates:
        if req.exists():
            run([sys.executable, "-m", "pip", "install", "-r", str(req)])
            return
    print("No llama.cpp Python requirements file found; continuing with current environment.")


def download_model(repo_id: str, work_dir: Path, revision: str | None) -> Path:
    target = ensure_dir(work_dir) / repo_id.replace("/", "__")
    print(f"Downloading {repo_id} to {target}")
    path = snapshot_download(
        repo_id=repo_id,
        repo_type="model",
        revision=revision,
        local_dir=str(target),
        local_dir_use_symlinks=False,
        ignore_patterns=["*.msgpack", "*.h5", "*.ot", "*.onnx", "*.tflite"],
    )
    return Path(path)


def convert_to_gguf(model_dir: Path, gguf_dir: Path, llama_cpp: Path, outtype: str) -> Path:
    ensure_dir(gguf_dir)
    outfile = gguf_dir / f"{model_dir.name}-{outtype}.gguf"
    if outfile.exists():
        print(f"GGUF already exists, reusing: {outfile}")
        return outfile
    script = conversion_script(llama_cpp)
    run([sys.executable, str(script), str(model_dir), "--outfile", str(outfile), "--outtype", outtype])
    return outfile


def write_modelfile(gguf_path: Path, name: str, num_ctx: int) -> Path:
    modelfile = gguf_path.parent / f"Modelfile.{name.replace(':', '_')}"
    content = f'''FROM {gguf_path}

TEMPLATE """{QWEN_CHAT_TEMPLATE}"""

SYSTEM """{SYSTEM_PROMPT}"""

PARAMETER temperature 0.2
PARAMETER top_p 0.9
PARAMETER repeat_penalty 1.08
PARAMETER num_ctx {num_ctx}
'''
    modelfile.write_text(content, encoding="utf-8")
    return modelfile


def create_ollama_model(name: str, modelfile: Path) -> None:
    if not shutil.which("ollama"):
        raise SystemExit("ollama executable not found on PATH")
    run(["ollama", "create", name, "-f", str(modelfile)])


def smoke_ollama_model(name: str) -> None:
    prompt = "Write a Python function add(a, b) that returns their sum. Return code only."
    run(["ollama", "run", name, prompt])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=DEFAULT_REPO)
    parser.add_argument("--revision")
    parser.add_argument("--ollama-name", default=DEFAULT_OLLAMA_NAME)
    parser.add_argument("--work-dir", type=Path, default=DEFAULT_WORK_DIR)
    parser.add_argument("--gguf-dir", type=Path, default=DEFAULT_GGUF_DIR)
    parser.add_argument("--llama-cpp", type=Path, default=DEFAULT_LLAMA_CPP)
    parser.add_argument("--clone-llama-cpp", action="store_true")
    parser.add_argument("--install-requirements", action="store_true")
    parser.add_argument("--outtype", default="f16", choices=["f16", "f32", "q8_0"])
    parser.add_argument("--num-ctx", type=int, default=4096)
    parser.add_argument("--skip-download", action="store_true")
    parser.add_argument("--skip-convert", action="store_true")
    parser.add_argument("--skip-create", action="store_true")
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()

    llama_cpp = ensure_llama_cpp(args.llama_cpp, clone_if_missing=args.clone_llama_cpp)
    if args.install_requirements:
        install_convert_requirements(llama_cpp)

    model_dir = args.work_dir / args.repo.replace("/", "__")
    if not args.skip_download:
        model_dir = download_model(args.repo, args.work_dir, args.revision)
    if not model_dir.exists():
        raise SystemExit(f"Model directory not found: {model_dir}")

    gguf_path = args.gguf_dir / f"{model_dir.name}-{args.outtype}.gguf"
    if not args.skip_convert:
        gguf_path = convert_to_gguf(model_dir, args.gguf_dir, llama_cpp, args.outtype)
    if not gguf_path.exists():
        raise SystemExit(f"GGUF not found: {gguf_path}")

    modelfile = write_modelfile(gguf_path, args.ollama_name, args.num_ctx)
    print(f"Modelfile written: {modelfile}")

    if not args.skip_create:
        create_ollama_model(args.ollama_name, modelfile)
    if args.smoke:
        smoke_ollama_model(args.ollama_name)

    print(f"Ready: {args.ollama_name}")


if __name__ == "__main__":
    main()
