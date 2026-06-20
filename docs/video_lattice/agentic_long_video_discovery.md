# Agentic Long Video Discovery

## Why This Exists

An hour of 30 FPS video is 108,000 frames before audio, transcript, pose, depth,
or scene metadata. A model should not ingest that as one giant prompt. It should
investigate it.

The SCBE video lattice should therefore have two linked layers:

1. A searchable long-video memory.
2. A geometry/perception lattice for frame-level verification and correction.

This follows the same practical pattern as Deep Video Discovery and EGAgent:
make video searchable first, then let an agent gather only the evidence needed
for the user question.

## External Pattern

Deep Video Discovery divides long videos into short clips, builds global,
clip-level, and frame-level records, then uses an LLM planner to call tools such
as global browse, clip search, and frame inspection.

EGAgent adds entity scene graphs for very long egocentric video, giving the
agent structured entities, scenes, and relationships to search instead of only
raw frame or transcript text.

## SCBE Version

Our version should add the body/depth/rendering layers that generic long-video
QA systems usually do not carry:

- transcript chunks
- clip captions
- frame thumbnails
- text and frame vectors in a shared multimodal embedding space
- visual embeddings
- body and hand landmarks
- depth and undefined-space scores
- multi-view perception vectors
- sketch/control-frame assets
- lattice drift and correction events
- entity-scene graph nodes

## Data Model

### Video

- `video_id`
- `source_path`
- `duration_seconds`
- `fps`
- `created_at`
- `global_summary`

### Clip

- `clip_id`
- `video_id`
- `start_seconds`
- `end_seconds`
- `caption`
- `transcript`
- `embedding_ref`
- `entity_refs`

### Frame

- `frame_id`
- `clip_id`
- `timestamp_seconds`
- `thumbnail_path`
- `pose_landmarks_path`
- `depth_summary`
- `undefined_space_score`
- `lattice_state_ref`
- `control_assets_ref`

### Entity

- `entity_id`
- `label`
- `kind`
- `first_seen_seconds`
- `last_seen_seconds`
- `frame_refs`
- `relations`

## Tool Surface

The planner should not receive raw video. It should receive tools:

1. `global_browse(video_id)`
   - Returns topic summary, scene bands, known entities, and high-level timeline.
2. `clip_search(video_id, query, start=None, end=None, top_k=8)`
   - Searches captions, transcript, and embeddings.
3. `frame_inspect(video_id, timestamp, question=None)`
   - Returns visual details, pose/depth state, thumbnail path, and uncertainty.
4. `entity_graph_search(video_id, entity=None, relation=None, time_range=None)`
   - Searches who/what appears, interacts, moves, or disappears.
5. `lattice_probe(video_id, start, end, axis=None)`
   - Finds drift spikes, correction frames, bad anatomy, undefined space, or scene cuts.
6. `control_frame_get(video_id, timestamp)`
   - Returns SVG/PNG sketches and prompt layers for render correction.

## Agent Loop

For a question, the agent runs:

1. Decompose the query.
2. Browse global context.
3. Search clips by transcript/caption/entity graph.
4. Inspect frames only inside promising windows.
5. Probe lattice anomalies if the visual answer depends on body, hand, depth, or motion.
6. Reflect on missing evidence.
7. Repeat until evidence is enough or uncertainty is explicit.
8. Synthesize answer with timestamps and evidence paths.

## How This Connects To Current Code

Current modules already provide the low-level evidence:

- `realtime_perception.py`: multi-view observations and undefined-space scoring.
- `pose_polygons.py`: hands, fingers, torso, body chains.
- `sketch_pad.py`: SVG/PNG control assets.
- `temporal_tracker.py`: frame drift history.
- `frame_corrector.py`: correction signals for renderer or neural generator.
- `vector_index.py`: local cosine search over CLIP/SigLIP-style vectors.
- `synthetic_video_lattice_demo.py`: prototype manifest and sketch artifacts.

The missing next layer is a clip/frame/entity indexer over real video files.

## Multimodal Embedding Layer

Text-to-frame lookup uses a shared latent space:

1. A frame encoder maps frame pixels or visual summaries into a vector.
2. A text encoder maps the user query into the same dimensional vector space.
3. Vectors are normalized.
4. Cosine similarity ranks candidate frames or clips.

The first local implementation uses exact cosine search in `LocalVectorIndex`
so it is deterministic and dependency-free. Later, the same record format can
be backed by FAISS, Qdrant, Milvus, Pinecone, or another ANN index.

The key rule is that embeddings are retrieval evidence, not final truth. The
agent still needs frame inspection, lattice probing, and uncertainty reporting
before answering.

## First Testable Milestone

Build a local indexer that can ingest a short video or folder of frames and
write:

- `video_index.json`
- `clips/*.json`
- `frames/*.json`
- `entities.json`
- `lattice_events.json`

Then build one CLI query:

```powershell
python scripts/video_lattice/query_video_index.py --video-id demo --query "where does the hand break"
```

The first query does not need to be smart. It only needs to prove the database
shape and evidence trail work.
