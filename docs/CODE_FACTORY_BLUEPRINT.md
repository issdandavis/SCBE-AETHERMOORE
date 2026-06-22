# Code Factory Blueprint

Generated: 2026-06-19

## Core Thesis

An agentic AI work facility should not be one giant smart agent. It should behave like a warehouse, fab, and chip interconnect:

- bounded stations do narrow work
- routers label and dispatch jobs
- conveyors move packets between stations
- policy gates refuse unsafe work before execution
- managers handle exceptions, training, bottlenecks, and layout changes

The product is the facility, not the individual model.

## Research Anchors

Warehouse operations usually split work into receiving, putaway/storage, picking, packing/shipping, inventory control, and quality control. The important pattern is that flow is designed into the facility, not improvised by each worker.

Warehouse sortation is the connective routing layer. It labels inventory, groups work, sends it to the correct station, and prevents downstream bottlenecks.

Nintendo North Bend is a useful local analogy: a distribution center where inventory control, conveyor flow, pick lists, QC, security, and shipping let a relatively small staff handle large order volume. The key lesson is not "more smart workers"; it is system design plus managers watching exceptions.

Semiconductor fabs add the higher-precision version: MES gives orders, ECS exchanges state, AMHS executes movement. TSMC describes automation across equipment automation, standardized carriers, MES-driven AMHS, real-time dispatch, and yield analysis. That maps cleanly to agentic AI work.

Network-on-chip routing gives the packet model: each router has input ports, output ports, a switching matrix, and control logic for routing/arbitration. Deterministic routing is preferred where possible; adaptive routing is used when links or stations are congested.

## Facility Layers

### 1. Receiving Dock

Accept user work as a job packet.

Fields:

- job_id
- requested outcome
- artifacts/files
- user intent
- risk level
- deadline/cost budget
- required tools
- provenance

### 2. Label And Inventory

Normalize the job into facility-readable labels.

Labels:

- kind: code, research, cleanup, document, deploy, image, data, security
- lane: deterministic, weak-model, strong-model, human-review
- risk: read-only, write, destructive, network, credentials, legal/medical/financial
- artifact class: file, repo, report, command, PR, dashboard, model output

### 3. Policy Gate

Policy is not the model's conscience. It is an object owned by the facility.

Responsibilities:

- block unsafe commands
- require approval for destructive or high-risk actions
- enforce repo rules
- enforce privacy and credential boundaries
- decide when human review is mandatory

### 4. Triage Routers

Use multiple routers instead of one overloaded brain.

Recommended shape:

- router A: deterministic rules and cheap classifiers
- router B: model router for ambiguous jobs
- arbiter: compares routes, resolves disagreement, or escalates

Routing should be measured as its own task. Weak models may be better routers than doers.

### 5. Conveyors

Conveyors are deterministic handoffs.

They should carry:

- packet state
- station input/output
- logs
- exit codes
- confidence
- error class
- next station

No station should need global context if the conveyor packet is well-formed.

### 6. Work Stations

Stations do bounded work.

Examples:

- parse station
- search station
- code edit station
- test station
- benchmark station
- cite/source station
- summarize station
- cleanup station
- deploy station

Stations can be pure code, cheap models, strong models, or human actions. Prefer pure deterministic tools where possible.

### 7. QC And Verification

Every shipment needs inspection.

Verification types:

- tests pass
- diff reviewed
- citations present
- copied files match counts/hashes
- generated artifact opens
- safety policy satisfied
- final output matches job label

### 8. Shipping

Package the result for the user or downstream system.

Shipping outputs:

- final answer
- patch
- commit/PR
- report
- local artifact path
- machine-readable JSON
- audit ledger

### 9. Manager Layer

Managers do not work every item. They watch the facility.

Manager responsibilities:

- handle exceptions
- retrain weak stations
- change routing rules
- add/remove stations
- watch bottlenecks
- inspect safety incidents
- decide when a strong model is worth the cost

## Chip/Fab/Warehouse Mapping

| Real system | AI facility equivalent |
| --- | --- |
| Receiving dock | intake parser |
| Barcode/label | job packet schema |
| WMS | triage router plus policy |
| Conveyor | deterministic state transition |
| Putaway | context storage / artifact indexing |
| Picking | retrieval and tool selection |
| Packing | result assembly |
| Shipping | response/PR/artifact delivery |
| Inventory control | provenance ledger |
| QC | tests, evals, citations, diff checks |
| MES | facility scheduler |
| AMHS | tool/executor layer |
| NoC router | model/tool router |
| Arbiter | route conflict resolver |
| Manager | exception handler and optimizer |

## Metrics

The facility should be judged by flow metrics, not only answer quality.

- route accuracy
- station accuracy
- manager calls per 100 jobs
- exception rate
- rework rate
- average queue time
- bottleneck station
- unsafe action blocks
- cost per shipped job
- cheap-model success rate
- strong-model escalation rate

The North Bend economics test is: can throughput scale by adding stations and conveyors while expensive manager calls stay low?

## Build Order

1. Define the job packet schema.
2. Implement receiving, label, policy, triage, execute, QC, and ship as separate stations.
3. Add two routers: deterministic and model-router.
4. Add an arbiter that escalates disagreement.
5. Track manager calls per 100 jobs.
6. Add station-level dashboards.
7. Expand job kinds only after the factory can explain where each job went and why.

## Design Rule

Deterministic routing where possible. Model routing where necessary. Specialized stations do the work. Strong managers handle exceptions.
