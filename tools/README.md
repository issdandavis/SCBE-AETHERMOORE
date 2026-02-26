# Sacred Tongue Tools (stasm / stvm)

## Assemble

```bash
python -m tools.stasm.assembler examples/hello_world.sts /tmp/hello.bin
```

## Run

```bash
python -m tools.stvm.vm /tmp/hello.bin
```

## JSON bytecode output

```bash
python -m tools.stasm.assembler examples/fib.sts /tmp/fib.json --json
python -m tools.stvm.vm /tmp/fib.json
```
