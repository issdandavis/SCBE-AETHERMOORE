# Changelog

## Unreleased

- Preserve recipe text that follows boolean flags, including the documented
  `polly run plan --dry-run "task"` ordering.
- Parse value-taking short flags such as `-f` and `-t` consistently with their
  long forms.
- Replace repository-only Python router discovery with package-native
  Cerebras, Groq, and HuggingFace routing so installed copies cannot execute a
  consumer project's lookalike script.

## 0.2.0

- Add governed task submission, status, and wait commands.
- Persist remote task IDs and fail-closed evidence dispositions in the pad.
- Add owned-network URL enforcement and strict non-promotion validation.

## 0.1.0

- Initial governed terminal workpad release.
