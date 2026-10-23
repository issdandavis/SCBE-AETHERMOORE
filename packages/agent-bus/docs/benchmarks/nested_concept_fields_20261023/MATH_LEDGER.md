# Math ledger

Let \(V\) be the 84 source-bound public artifacts, \(E\) the typed directed edges, \(B\) the overlapping concept bubbles, and \(F\) the acyclic topic-field hierarchy.

## Canonical identity and tongue view

For sentence bytes \(x_i\) and tongue permutation \(\sigma_k\):

\[v*{i,k}=\sigma_k(x_i), \qquad \sigma_k^{-1}(v*{i,k})=x_i.\]

The round trip proves representation integrity only.

## Overlapping membership

\[M(v_i)=\{(b,w,a,s,H):v_i\in b\}.\]

Here \(w\in(0,1]\), \(a\) is authority, \(s\in\{source,verified,hypothesis,rejected\}\), and \(H\) is the receipt-hash set. One sentence may occupy several bubbles.

## Goal-conditioned edge cost

For edge \(e\) with relation \(r(e)\), positive base cost \(c(e)\), and goal multiplier \(g_r>0\):

\[c*G(e)=c(e)g*{r(e)}.\]

The selected route is

\[P^\*=\arg\min*{P:s\leadsto T}\sum*{e\in P}c_G(e),\]

with lexical artifact-id order as the deterministic tie-break. Dijkstra is valid because every admitted cost is positive.

## Bubble hop

A bubble is an explicit hyperedge. If two artifacts have admitted memberships in the same bubble, the router may add a \(co_member\) hop at the goal's declared bubble cost. No geometric closeness creates an edge.

## Receipt chain

\[h*0=H(goal, reasoning_graph, concept_graph),\qquad h_j=H(h*{j-1},e_j,c_j,C_j).\]

Changing a hop, cost, graph, or goal changes the route digest. Replanning from the normalized goal must reproduce the same digest.

## Control rule

Typed routing must beat the flat baseline and untyped baseline, and

\[A*{typed}-\bar A*{shuffle}>2s\_{pooled}.\]

Observed: \(1.0000-0.4427=0.5573\); threshold \(0.0565\).
