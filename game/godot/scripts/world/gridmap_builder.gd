## GridMapBuilder — Procedural MeshLibrary generator for Six Sacred Tongue tile sets
##
## Creates placeholder low-poly 3D tiles at runtime since MeshLibrary
## resources are best authored in-editor. Each tongue zone has distinct
## tile colors following GDD Section 1.4 palettes.
##
## Tile IDs:
##   0 = Ground (grass/stone)
##   1 = Wall (waist-height)
##   2 = Building floor
##   3 = Building wall (tall)
##   4 = Water/special
##   5 = Path/road
##   6 = Decoration (plants, crates)
##   7 = Ward pylon (interactive)

extends Node

class_name GridMapBuilder

# Tile type constants
const TILE_GROUND: int = 0
const TILE_WALL: int = 1
const TILE_BUILDING_FLOOR: int = 2
const TILE_BUILDING_WALL: int = 3
const TILE_WATER: int = 4
const TILE_PATH: int = 5
const TILE_DECORATION: int = 6
const TILE_WARD_PYLON: int = 7


## Create a MeshLibrary with tongue-themed tiles
static func create_tongue_mesh_library(tongue_index: int) -> MeshLibrary:
	var lib := MeshLibrary.new()
	var palette := _get_tongue_palette(tongue_index)

	# Ground tile (1x1x0.1 box)
	_add_tile(lib, TILE_GROUND, _make_box(Vector3(1, 0.1, 1)), palette["ground"])

	# Wall tile (1x0.5x1 box)
	_add_tile(lib, TILE_WALL, _make_box(Vector3(1, 0.5, 1)), palette["wall"])

	# Building floor (1x0.05x1 flat)
	_add_tile(lib, TILE_BUILDING_FLOOR, _make_box(Vector3(1, 0.05, 1)), palette["building"])

	# Building wall (1x2x1 tall)
	_add_tile(lib, TILE_BUILDING_WALL, _make_box(Vector3(1, 2, 1)), palette["building_wall"])

	# Water (1x0.05x1 blue tint)
	_add_tile(lib, TILE_WATER, _make_box(Vector3(1, 0.05, 1)), palette["water"])

	# Path (1x0.08x1)
	_add_tile(lib, TILE_PATH, _make_box(Vector3(1, 0.08, 1)), palette["path"])

	# Decoration (0.4x0.6x0.4 small object)
	_add_tile(lib, TILE_DECORATION, _make_box(Vector3(0.4, 0.6, 0.4)), palette["decoration"])

	# Ward pylon (0.3x1.5x0.3 tall thin)
	_add_tile(lib, TILE_WARD_PYLON, _make_box(Vector3(0.3, 1.5, 0.3)), palette["pylon"])

	return lib


static func _add_tile(lib: MeshLibrary, id: int, mesh: Mesh, color: Color) -> void:
	lib.create_item(id)
	# Apply material
	var mat := StandardMaterial3D.new()
	mat.albedo_color = color
	mat.roughness = 0.8
	if id == TILE_WATER:
		mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
		mat.albedo_color.a = 0.7
	if id == TILE_WARD_PYLON:
		mat.emission_enabled = true
		mat.emission = color
		mat.emission_energy_multiplier = 1.5
	mesh.surface_set_material(0, mat)
	lib.set_item_mesh(id, mesh)
	# Simple box shape for collision
	var shape := BoxShape3D.new()
	match id:
		TILE_GROUND: shape.size = Vector3(1, 0.1, 1)
		TILE_WALL: shape.size = Vector3(1, 0.5, 1)
		TILE_BUILDING_FLOOR: shape.size = Vector3(1, 0.05, 1)
		TILE_BUILDING_WALL: shape.size = Vector3(1, 2, 1)
		TILE_WATER: shape.size = Vector3(1, 0.05, 1)
		TILE_PATH: shape.size = Vector3(1, 0.08, 1)
		TILE_DECORATION: shape.size = Vector3(0.4, 0.6, 0.4)
		TILE_WARD_PYLON: shape.size = Vector3(0.3, 1.5, 0.3)
	lib.set_item_shapes(id, [shape, Transform3D.IDENTITY])


static func _make_box(size: Vector3) -> BoxMesh:
	var mesh := BoxMesh.new()
	mesh.size = size
	return mesh


## Get tongue-specific color palette
static func _get_tongue_palette(tongue_index: int) -> Dictionary:
	match tongue_index:
		0:  # KO — Ember Reach: warm reds, oranges, amber
			return {
				"ground":        Color(0.55, 0.35, 0.20),
				"wall":          Color(0.60, 0.30, 0.15),
				"building":      Color(0.50, 0.28, 0.15),
				"building_wall": Color(0.70, 0.35, 0.20),
				"water":         Color(0.80, 0.40, 0.10),
				"path":          Color(0.65, 0.45, 0.25),
				"decoration":    Color(0.40, 0.55, 0.25),
				"pylon":         Color(0.90, 0.30, 0.20),
			}
		1:  # AV — Aerial Expanse: sky blue, teal, cloud white
			return {
				"ground":        Color(0.60, 0.75, 0.65),
				"wall":          Color(0.70, 0.85, 0.90),
				"building":      Color(0.80, 0.90, 0.95),
				"building_wall": Color(0.65, 0.80, 0.90),
				"water":         Color(0.30, 0.70, 0.90),
				"path":          Color(0.75, 0.85, 0.80),
				"decoration":    Color(0.50, 0.80, 0.70),
				"pylon":         Color(0.30, 0.80, 0.95),
			}
		2:  # RU — Null Vale: violet, grey, black
			return {
				"ground":        Color(0.25, 0.20, 0.30),
				"wall":          Color(0.35, 0.25, 0.40),
				"building":      Color(0.30, 0.22, 0.35),
				"building_wall": Color(0.40, 0.30, 0.50),
				"water":         Color(0.20, 0.10, 0.35),
				"path":          Color(0.35, 0.30, 0.38),
				"decoration":    Color(0.50, 0.30, 0.60),
				"pylon":         Color(0.60, 0.20, 0.80),
			}
		3:  # CA — Glass Drift: cyan, gold, white
			return {
				"ground":        Color(0.70, 0.80, 0.75),
				"wall":          Color(0.60, 0.85, 0.85),
				"building":      Color(0.85, 0.90, 0.92),
				"building_wall": Color(0.50, 0.80, 0.85),
				"water":         Color(0.20, 0.75, 0.85),
				"path":          Color(0.80, 0.80, 0.65),
				"decoration":    Color(0.85, 0.75, 0.30),
				"pylon":         Color(0.20, 0.90, 0.90),
			}
		4:  # UM — Ward Sanctum: emerald, ivory, deep green
			return {
				"ground":        Color(0.20, 0.50, 0.25),
				"wall":          Color(0.15, 0.55, 0.30),
				"building":      Color(0.85, 0.88, 0.80),
				"building_wall": Color(0.20, 0.60, 0.35),
				"water":         Color(0.10, 0.45, 0.30),
				"path":          Color(0.70, 0.78, 0.65),
				"decoration":    Color(0.15, 0.65, 0.30),
				"pylon":         Color(0.10, 0.90, 0.40),
			}
		5:  # DR — Bastion Fields: stone, rose, silver
			return {
				"ground":        Color(0.55, 0.50, 0.50),
				"wall":          Color(0.65, 0.55, 0.55),
				"building":      Color(0.70, 0.65, 0.65),
				"building_wall": Color(0.60, 0.50, 0.55),
				"water":         Color(0.50, 0.45, 0.55),
				"path":          Color(0.70, 0.68, 0.65),
				"decoration":    Color(0.75, 0.50, 0.55),
				"pylon":         Color(0.85, 0.60, 0.70),
			}
		_:  # Hearthstone Landing — warm neutral (mix of all tongues)
			return {
				"ground":        Color(0.45, 0.55, 0.35),
				"wall":          Color(0.55, 0.50, 0.40),
				"building":      Color(0.60, 0.55, 0.45),
				"building_wall": Color(0.65, 0.55, 0.42),
				"water":         Color(0.25, 0.50, 0.70),
				"path":          Color(0.60, 0.55, 0.42),
				"decoration":    Color(0.40, 0.60, 0.35),
				"pylon":         Color(0.70, 0.65, 0.30),
			}
