# Compile Is the Oven Doctrine

Date: 2026-06-27
Status: operating rule

## Rule

There is one hard gate in coding:

```text
Does it compile/run and emit a working thing in front of the user?
```

Everything before that is cake batter:

- code volume
- architecture notes
- clever plans
- generated files
- UI mockups
- model outputs
- test ideas
- agent confidence

The oven is:

- compile
- build
- run
- load in browser/app
- execute the intended user path
- produce a visible working artifact

If it does not survive the oven, it is not done.

## Product status language

| Status | Meaning |
|---|---|
| `batter` | Code/spec exists but has not been compiled or run. |
| `baked` | Build/compile succeeded. |
| `served` | User-facing path was run and visible output worked. |
| `burnt` | Compile/run failed. |
| `unbaked_claim` | Someone claimed success without compile/run evidence. |

## Release rule

No artifact can be called release-ready unless:

1. The relevant compiler/build command ran.
2. The app/tool emitted the expected working output.
3. The result is visible or inspectable by the user.
4. The receipt names the command/path/output.

## Training rule

Small LLMs must learn:

- writing code is not completion
- documentation is not completion
- a generated patch is not completion
- success requires compile/run evidence
- if validation was not run, say `not validated`

## AetherDesk rule

AetherDesk should show this clearly:

```text
Batter: changed, unbuilt
Baked: build passed
Served: user path worked
Burnt: failed, needs repair
```

## Agent response rule

If the agent did not compile/run:

```text
Code changed, not validated.
```

If the agent did compile/run:

```text
Built with: <command>
Output: <key line or visible route>
Result: baked/served
```

## Why

All the code in the world cannot fix a compiler/codebase that does not emit a working thing in front of the user.

