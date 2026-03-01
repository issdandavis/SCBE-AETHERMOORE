# PollyPad — The Octopus
#
# Polly IS the octopus. Not sitting on top — she IS it.
# She started as DM, became partner, became meta-character,
# became everything, then cycled back. That's the shape.
#
# The octopus has 8 tentacles. Each tentacle is a major domain.
# Each tentacle has suckers — individual capabilities within that domain.
# The mantle (body) is the SCBE governance core.
# The brain is Polly — distributed across all arms, not centralized.
# Chromatophores are the adaptive surface — tone/style shifts per context.
# Ink sac is the antivirus membrane — defense when threatened.
#
# Tentacles:
#   1. Code    — development, testing, deployment, debugging
#   2. Journal — persistent memory, knowledge base, learning log
#   3. Organize — task management, planning, scheduling, priorities
#   4. Research — academic, competitive, market intelligence
#   5. Outreach — marketing, sales, partnerships, grants
#   6. Commerce — products, pricing, delivery, revenue
#   7. Create  — content, design, story, lore, visuals
#   8. Guard   — governance, security, scanning, quarantine
#
# The PollyPad is the interface — the skin of the octopus.
# Users touch the skin. The skin routes to tentacles.
# Every interaction flows through the mantle (SCBE governance).
# Every interaction generates training data (SFT/DPO pairs).
#
# Persistent Memory = the octopus's distributed nervous system.
# 2/3 of neurons are in the arms, not the brain.
# Memory lives WHERE it's used, not in a central database.
#
# Patent: USPTO #63/961,403 (Pending)

from .octopus import Octopus, Tentacle, TentacleType, Sucker
from .memory import PersistentMemory, MemoryCell, MemoryQuery
from .pad import PollyPad, Interaction, TrainingPair
from .ray_caster import (
    RayCaster, Point, BeamType, BeamResult, ScatterResult,
    ReflectionType, Reflection, BeamSegment,
    harmonic_wall, harmonic_gradient,
)

__all__ = [
    "Octopus",
    "Tentacle",
    "TentacleType",
    "Sucker",
    "PersistentMemory",
    "MemoryCell",
    "MemoryQuery",
    "PollyPad",
    "Interaction",
    "TrainingPair",
    # Ray Caster
    "RayCaster",
    "Point",
    "BeamType",
    "BeamResult",
    "ScatterResult",
    "ReflectionType",
    "Reflection",
    "BeamSegment",
    "harmonic_wall",
    "harmonic_gradient",
]
