## TongueSystem — Sacred Tongue definitions, XP tracking, egg region checks
##
## Six Sacred Tongues with golden-ratio weights, Hodge dual pairs,
## Cl(4,0) bivector mappings, and B^6 egg hatching regions.
##
## Tongue indices: 0=KO, 1=AV, 2=RU, 3=CA, 4=UM, 5=DR

extends Node

const PHI: float = 1.618033988749895

# -- Tongue definitions --

enum Tongue { KO, AV, RU, CA, UM, DR }

const TONGUE_NAMES: PackedStringArray = ["KO", "AV", "RU", "CA", "UM", "DR"]
const TONGUE_FULL_NAMES: PackedStringArray = [
	"Kor'aelin", "Avali", "Runethic", "Cassisivadan", "Umbroth", "Draumric"
]

# Golden ratio weights: KO=1.00, AV=φ, RU=φ², CA=φ³, UM=φ⁴, DR=φ⁵
var tongue_weights: Array[float] = [
	1.0,          # KO
	PHI,          # AV  ≈ 1.618
	PHI * PHI,    # RU  ≈ 2.618
	pow(PHI, 3),  # CA  ≈ 4.236
	pow(PHI, 4),  # UM  ≈ 6.854
	pow(PHI, 5),  # DR  ≈ 11.09
]

# Harmonic frequencies (Hz) from GDD synesthesia mapping
const TONGUE_FREQUENCIES: Array[float] = [220.0, 247.0, 277.0, 311.0, 349.0, 392.0]

# Hue degrees for color mapping
const TONGUE_HUES: Array[float] = [0.0, 60.0, 120.0, 180.0, 240.0, 300.0]

# Tongue colors (saturated, GBA-era)
const TONGUE_COLORS: Dictionary = {
	0: Color(0.86, 0.24, 0.24),  # KO — Red
	1: Color(0.86, 0.71, 0.24),  # AV — Yellow
	2: Color(0.24, 0.86, 0.47),  # RU — Green
	3: Color(0.24, 0.71, 0.86),  # CA — Cyan
	4: Color(0.24, 0.24, 0.86),  # UM — Blue
	5: Color(0.86, 0.24, 0.86),  # DR — Magenta
}

# Hodge dual pairs: (KO,DR), (AV,UM), (RU,CA)
const HODGE_PAIRS: Array[Vector2i] = [
	Vector2i(0, 5),  # KO ↔ DR
	Vector2i(1, 4),  # AV ↔ UM
	Vector2i(2, 3),  # RU ↔ CA
]

# Cl(4,0) bivector basis: e12, e13, e14, e23, e24, e34
# Each tongue maps to one bivector
const BIVECTOR_MAP: Dictionary = {
	0: "e12",  # KO
	1: "e13",  # AV
	2: "e14",  # RU
	3: "e23",  # CA
	4: "e24",  # UM
	5: "e34",  # DR
}

# Zone palettes (from GDD Section 1.4)
const ZONE_DATA: Dictionary = {
	"ember_reach":     {"tongue": 0, "name": "Ember Reach",     "palette": Color(0.86, 0.24, 0.24)},
	"glass_drift":     {"tongue": 3, "name": "Glass Drift",     "palette": Color(0.24, 0.71, 0.86)},
	"null_vale":       {"tongue": 2, "name": "Null Vale",       "palette": Color(0.55, 0.24, 0.86)},
	"bastion_fields":  {"tongue": 5, "name": "Bastion Fields",  "palette": Color(0.72, 0.55, 0.72)},
	"aerial_expanse":  {"tongue": 1, "name": "Aerial Expanse",  "palette": Color(0.53, 0.81, 0.92)},
	"ward_sanctum":    {"tongue": 4, "name": "Ward Sanctum",    "palette": Color(0.24, 0.86, 0.47)},
}


# ========================
# TYPE ADVANTAGE (Cl(4,0))
# ========================

# Bivector commutator table [A][B] → sign of Δ
# Derived from Cl(4,0) structure constants
# +1 = A has advantage, -1 = B has advantage, 0 = neutral
const COMMUTATOR_SIGN: Array[Array] = [
	# KO  AV  RU  CA  UM  DR
	[ 0, +1, +1, -1, -1,  0],  # KO (e12)
	[-1,  0, +1, +1,  0, -1],  # AV (e13)
	[-1, -1,  0,  0, +1, +1],  # RU (e14)
	[+1, -1,  0,  0, +1, -1],  # CA (e23)
	[+1,  0, -1, -1,  0, +1],  # UM (e24)
	[ 0, +1, -1, +1, -1,  0],  # DR (e34)
]

## Compute type advantage Δ between two tongue indices.
## Returns float in [-1, 1]. Positive = attacker advantage.
func compute_advantage(attacker_tongue: int, defender_tongue: int,
					   attacker_phase: Array[float], defender_phase: Array[float]) -> float:
	if attacker_tongue < 0 or attacker_tongue > 5 or defender_tongue < 0 or defender_tongue > 5:
		return 0.0
	var base_sign: int = COMMUTATOR_SIGN[attacker_tongue][defender_tongue]
	if base_sign == 0:
		# Hodge dual or same tongue — phase angles break the tie
		var phase_diff := 0.0
		for i in range(mini(attacker_phase.size(), defender_phase.size())):
			phase_diff += attacker_phase[i] - defender_phase[i]
		return clampf(phase_diff * 0.1, -1.0, 1.0)
	# Scale by phase magnitude
	var phase_magnitude := 0.0
	for i in range(mini(attacker_phase.size(), defender_phase.size())):
		phase_magnitude += absf(attacker_phase[i] - defender_phase[i])
	var strength := clampf(0.3 + phase_magnitude * 0.05, 0.0, 1.0)
	return float(base_sign) * strength


# ====================
# EGG HATCHING (B^6)
# ====================

## Check which eggs can hatch given a player's tongue distribution.
## Returns array of egg type strings.
func check_egg_conditions(tongue_xp: Array[float]) -> Array[String]:
	var result: Array[String] = []
	var total := 0.0
	for xp in tongue_xp:
		total += xp
	if total < 0.01:
		return result

	# Normalize to [0,1]
	var t: Array[float] = []
	for xp in tongue_xp:
		t.append(xp / total)

	# Mono-tongue eggs
	if t[0] >= 0.6 and t[0] > 2.0 * t[5]:
		result.append("ember")   # KO
	if t[1] >= 0.5 and t[1] > 1.5 * t[4]:
		result.append("gale")    # AV
	if t[2] >= 0.5 and t[2] > 1.5 * t[3]:
		result.append("void")    # RU
	if t[3] >= 0.5 and t[3] > 1.5 * t[2]:
		result.append("crystal") # CA
	if t[4] >= 0.5 and t[4] > 1.5 * t[1]:
		result.append("ward")    # UM
	if t[5] >= 0.5 and t[5] > 1.5 * t[0]:
		result.append("helix")   # DR

	# Hodge dual eggs
	if t[0] >= 0.4 and t[5] >= 0.4 and absf(t[0] - t[5]) < 0.15:
		result.append("eclipse")  # KO+DR
	if t[1] >= 0.4 and t[4] >= 0.4 and absf(t[1] - t[4]) < 0.15:
		result.append("storm")    # AV+UM
	if t[2] >= 0.4 and t[3] >= 0.4 and absf(t[2] - t[3]) < 0.15:
		result.append("paradox")  # RU+CA

	# Omni egg
	var all_above := true
	for val in t:
		if val < 0.35 / 6.0:  # Scaled threshold
			all_above = false
			break
	if all_above and t.min() >= 0.1:
		result.append("prism")

	return result


## Check if two tongues are Hodge duals
func are_hodge_dual(a: int, b: int) -> bool:
	for pair in HODGE_PAIRS:
		if (pair.x == a and pair.y == b) or (pair.x == b and pair.y == a):
			return true
	return false


## Get the Hodge dual of a tongue index
func hodge_dual_of(tongue: int) -> int:
	for pair in HODGE_PAIRS:
		if pair.x == tongue:
			return pair.y
		if pair.y == tongue:
			return pair.x
	return -1


## Get tongue color
func get_tongue_color(tongue_index: int) -> Color:
	if TONGUE_COLORS.has(tongue_index):
		return TONGUE_COLORS[tongue_index]
	return Color.WHITE
