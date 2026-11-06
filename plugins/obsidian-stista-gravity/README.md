# STISTA gravity for Obsidian

The Six Tongues view uses the existing SS1 phase/weight definitions and the
vault's full-path node index. It starts paused and displays at most 120 nodes
per page; searching covers the whole index. Topic roles are editable keyword
estimates, not learned tokenizer embeddings.

Build from the SCBE repo: `node plugins/obsidian-stista-gravity/build.cjs`.
`entry.js` and `graph-view.js` are bundled into `main.js`; Obsidian's loader
does not resolve a local `require('./graph-view.js')` from an unbundled entry.

The organizer installs `main.js`, `manifest.json`, `styles.css`, and the local
graph. Run its `plan` then `apply` commands with an audit directory. Its backups
and receipts retain the prior bytes. Rebuild before reinstalling source edits.

Commands: **STISTA gravity: Open Tongue Gravity** and **Reload Tongue Gravity
data**. The latter reloads the current graph JSON after Codex/Clay refreshes it.
Plugin code changes need a plugin/app reload. This local package has not been
published to the community catalog; no public release or auto-update claim is made.

The native UI was checked in Obsidian 1.13.4, including light-theme compatibility
and opening the exact selected note. The renderer's math also has equal-weight
and zero-gravity controls in `test-physics.cjs`.
