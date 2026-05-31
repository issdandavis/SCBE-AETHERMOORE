# AWS Lambda Integration

This directory contains AWS Lambda deployment code for the SCBE 14-Layer Hyperbolic Governance System.

## Files

- **index.js** - Node.js Lambda handler (Manifold Classifier + Trajectory Kernel)
- **demo.html** - Interactive web demo for testing Lambda API
- **lambda_handler.py** - Python Lambda handler (full SCBE pipeline)

## Quick Deploy

```bash
# Package Python Lambda
cd ../..
./scripts/package_lambda.sh

# Deploy using SAM
sam deploy --guided
```

## Documentation

See the current [Product Quickstart](../../docs/PRODUCT_QUICKSTART.md) for supported deployment and runtime entrypoints.
