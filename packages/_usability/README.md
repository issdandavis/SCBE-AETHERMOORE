# Package usability harness

Measures each npm package against the commands its README already claims.

```bash
node packages/_usability/measure.cjs --surface local
node packages/_usability/measure.cjs --surface published
```

Writes `RECEIPT.json`. Do not change bins until both surfaces have a receipt.
