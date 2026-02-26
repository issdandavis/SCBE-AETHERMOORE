## SymbioticNetwork — Graph topology for companion bonds (GDD Section 3.5)
##
## Companions form a weighted graph. Graph Laplacian L = D - A
## computes emergent bonuses: XP multiplier, insight, resilience,
## governance weight, diversity.
##
## Hodge dual pairs bond 30% stronger: (KO,DR), (AV,UM), (RU,CA)

class_name SymbioticNetwork
extends RefCounted

# Adjacency matrix (dense, small graph — max ~20 companions)
var adjacency: Array[Array] = []  # [i][j] = edge weight
var node_ids: Array[String] = []   # Ordered companion IDs
var node_tongues: Array[int] = []  # Dominant tongue per node

const HODGE_BOND_BOOST: float = 0.3


## Add a node (companion or player avatar)
func add_node(id: String, dominant_tongue: int) -> void:
	if node_ids.has(id):
		return
	node_ids.append(id)
	node_tongues.append(dominant_tongue)
	# Expand adjacency matrix
	for row in adjacency:
		row.append(0.0)
	var new_row: Array = []
	for _i in range(node_ids.size()):
		new_row.append(0.0)
	adjacency.append(new_row)


## Set bond weight between two companions
func set_bond(id_a: String, id_b: String, weight: float) -> void:
	var i := node_ids.find(id_a)
	var j := node_ids.find(id_b)
	if i < 0 or j < 0 or i == j:
		return
	# Apply Hodge dual boost
	var actual_weight := weight
	if TongueSystem.are_hodge_dual(node_tongues[i], node_tongues[j]):
		actual_weight *= (1.0 + HODGE_BOND_BOOST)
	adjacency[i][j] = actual_weight
	adjacency[j][i] = actual_weight


## Get bond weight between two companions
func get_bond(id_a: String, id_b: String) -> float:
	var i := node_ids.find(id_a)
	var j := node_ids.find(id_b)
	if i < 0 or j < 0:
		return 0.0
	return adjacency[i][j]


## Compute degree matrix diagonal
func _degree_diagonal() -> Array[float]:
	var n := node_ids.size()
	var degrees: Array[float] = []
	for i in range(n):
		var deg := 0.0
		for j in range(n):
			deg += adjacency[i][j]
		degrees.append(deg)
	return degrees


## Compute spectral gap λ₂ (second-smallest eigenvalue of Laplacian)
## Uses power iteration on L for small graphs
func spectral_gap() -> float:
	var n := node_ids.size()
	if n < 2:
		return 0.0

	# Build Laplacian L = D - A
	var L: Array[Array] = []
	var degrees := _degree_diagonal()
	for i in range(n):
		var row: Array = []
		for j in range(n):
			if i == j:
				row.append(degrees[i])
			else:
				row.append(-adjacency[i][j])
		L.append(row)

	# For small graphs (n <= 6), compute eigenvalues via characteristic tricks
	# For larger, use inverse power iteration
	# Simple approach: compute Lv for random vectors, find smallest non-zero eigenvalue
	if n == 2:
		return degrees[0] + degrees[1]  # = 2w for single edge

	# Power iteration to find λ₂
	# First find λ₁ (always 0 for connected graph, eigenvector = [1,1,...,1]/√n)
	var ones: Array[float] = []
	for _i in range(n):
		ones.append(1.0 / sqrt(float(n)))

	# Random vector orthogonal to ones
	var v: Array[float] = []
	for i in range(n):
		v.append(float(i) - float(n - 1) / 2.0)
	v = _normalize(v)
	v = _orthogonalize(v, ones)
	v = _normalize(v)

	# Power iteration on L (converges to largest eigenvalue)
	# We want smallest non-zero, so iterate on (max_eigenvalue * I - L)
	# Estimate max eigenvalue
	var max_eig := 0.0
	for i in range(n):
		max_eig = maxf(max_eig, 2.0 * degrees[i])
	if max_eig < 0.001:
		return 0.0

	# Iterate on (max_eig * I - L) to find its largest eigenvalue
	# Then λ₂ = max_eig - that
	for _iter in range(50):
		var new_v: Array[float] = []
		for i in range(n):
			var sum := 0.0
			for j in range(n):
				var M_ij := -L[i][j]
				if i == j:
					M_ij += max_eig
				sum += M_ij * v[j]
			new_v.append(sum)
		new_v = _orthogonalize(new_v, ones)
		new_v = _normalize(new_v)
		v = new_v

	# Rayleigh quotient: λ = v^T L v / v^T v
	var vLv := 0.0
	for i in range(n):
		var Lv_i := 0.0
		for j in range(n):
			Lv_i += L[i][j] * v[j]
		vLv += v[i] * Lv_i

	return maxf(0.0, vLv)


## Compute all emergent bonuses (GDD Section 3.5 table)
func compute_bonuses() -> Dictionary:
	var gap := spectral_gap()
	var density := _graph_density()
	var total_bond := _total_bond_weight()
	var unique_count := _unique_tongues()

	return {
		"xp_multiplier":    1.0 + gap * 0.5,
		"insight_bonus":    density * 0.3,
		"resilience":       minf(1.0, gap * 0.2),
		"governance_weight": minf(2.0, total_bond * 0.1 + 1.0),
		"diversity_bonus":  float(unique_count) / 6.0,
		"spectral_gap":     gap,
	}


func _graph_density() -> float:
	var n := node_ids.size()
	if n < 2:
		return 0.0
	var edge_count := 0
	for i in range(n):
		for j in range(i + 1, n):
			if adjacency[i][j] > 0.001:
				edge_count += 1
	var max_edges := n * (n - 1) / 2
	return float(edge_count) / float(max_edges)


func _total_bond_weight() -> float:
	var total := 0.0
	var n := node_ids.size()
	for i in range(n):
		for j in range(i + 1, n):
			total += adjacency[i][j]
	return total


func _unique_tongues() -> int:
	var seen: Array[int] = []
	for t in node_tongues:
		if not seen.has(t):
			seen.append(t)
	return seen.size()


# -- Linear algebra helpers --

static func _normalize(v: Array[float]) -> Array[float]:
	var norm := 0.0
	for val in v:
		norm += val * val
	norm = sqrt(norm)
	if norm < 1e-10:
		return v
	var result: Array[float] = []
	for val in v:
		result.append(val / norm)
	return result


static func _orthogonalize(v: Array[float], basis: Array[float]) -> Array[float]:
	# v = v - (v·basis) * basis
	var dot := 0.0
	for i in range(v.size()):
		dot += v[i] * basis[i]
	var result: Array[float] = []
	for i in range(v.size()):
		result.append(v[i] - dot * basis[i])
	return result
