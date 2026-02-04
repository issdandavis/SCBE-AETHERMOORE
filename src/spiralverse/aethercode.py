"""
Aethercode Interpreter - Esoteric Programming Language for Spiralverse
======================================================================

"Code as interwoven verses in 6 langues with polyphonic chant synthesis."

Aethercode is an esoteric programming language where:
- The 6 LANGUES provide semantic soul (invitation-based control flow)
- The 6 CIPHER ALPHABETS provide orthography (48 symbols)
- The 6 TECHNICAL LANGUAGES provide runtime domains

Each verse is prefixed by a tongue signature routing to its domain handler:
- a3f7c2e1: AXIOM/KO  -> Directives, forward momentum, execution
- b8e4d9c3: FLOW/AV   -> Transitions, branching, iteration
- c1d5a7f2: GLYPH/RU  -> Structure, hierarchy, data definitions
- d9a2b6e8: ORACLE/CA -> Time, events, async operations
- e4f1c8d7: CHARM/UM  -> Harmony, priorities, negotiation
- f7b3e5a9: LEDGER/DR -> Authentication, records, proofs

Execution produces polyphonic chant .wav files as audible proof of validity.

Features:
- Multi-verse composition with tongue interleaving
- Automatic RWP2 envelope signing for execution proofs
- Polyphonic synthesis mapping each tongue to a frequency band
- State machine with 6D position tracking
- Integration with Spiralverse proximity optimization

"Invitation over Command, Connection over Control"
"""

import asyncio
import hashlib
import re
import struct
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any, Callable, Set
from enum import Enum
from datetime import datetime, timezone
import io
import os

# Internal imports
from .polyglot_alphabet import (
    TongueID, TONGUE_ALPHABETS, SIGNATURE_TO_TONGUE,
    compose_polyglot_message, decompose_polyglot_message
)
from .vector_6d import Position6D, euclidean_distance_6d
from .rwp2_envelope import (
    ProtocolTongue, RWP2Envelope, EnvelopeFactory,
    OperationTier, TONGUE_KEYS
)


# =============================================================================
# Constants & Frequency Mapping
# =============================================================================

# Each tongue maps to a frequency band for polyphonic synthesis
TONGUE_FREQUENCIES: Dict[TongueID, Tuple[float, float]] = {
    TongueID.AXIOM:  (440.0, 523.25),   # A4 to C5 - Command register
    TongueID.FLOW:   (329.63, 392.0),   # E4 to G4 - Flow register
    TongueID.GLYPH:  (261.63, 311.13),  # C4 to Eb4 - Structure register
    TongueID.ORACLE: (493.88, 587.33),  # B4 to D5 - Oracle register
    TongueID.CHARM:  (369.99, 440.0),   # F#4 to A4 - Harmony register
    TongueID.LEDGER: (220.0, 261.63),   # A3 to C4 - Ledger register (bass)
}

# Tongue to technical language mapping
TONGUE_DOMAINS: Dict[TongueID, str] = {
    TongueID.AXIOM:  "execution",    # Direct execution, commands
    TongueID.FLOW:   "control",      # Branching, loops, transitions
    TongueID.GLYPH:  "structure",    # Data definitions, hierarchies
    TongueID.ORACLE: "temporal",     # Async, events, scheduling
    TongueID.CHARM:  "harmony",      # Priority negotiation, balance
    TongueID.LEDGER: "record",       # Proofs, authentication, logging
}

SAMPLE_RATE = 44100


# =============================================================================
# Verse Parsing
# =============================================================================

@dataclass
class AetherVerse:
    """
    A single verse in Aethercode - one tongue's contribution to the composition.

    Format: signature:content
    Example: a3f7c2e1:INVOKE greet WITH "Hello"
    """
    tongue_id: TongueID
    signature: str
    content: str
    line_number: int = 0
    indent_level: int = 0

    @property
    def domain(self) -> str:
        return TONGUE_DOMAINS[self.tongue_id]

    @property
    def frequency_band(self) -> Tuple[float, float]:
        return TONGUE_FREQUENCIES[self.tongue_id]


@dataclass
class AetherProgram:
    """
    Complete Aethercode program - a composition of verses.
    """
    verses: List[AetherVerse]
    title: str = "Untitled Composition"
    author: str = "Anonymous"
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def tongues_used(self) -> Set[TongueID]:
        return {v.tongue_id for v in self.verses}

    @property
    def verse_count(self) -> int:
        return len(self.verses)


def parse_verse(line: str, line_number: int = 0) -> Optional[AetherVerse]:
    """
    Parse a single verse line.

    Format: [indent]signature:content
    Example: a3f7c2e1:INVOKE greet WITH "Hello"
    """
    # Calculate indent
    stripped = line.lstrip()
    indent_level = (len(line) - len(stripped)) // 2

    # Check for signature prefix
    if ':' not in stripped:
        return None

    parts = stripped.split(':', 1)
    signature = parts[0].strip()
    content = parts[1].strip() if len(parts) > 1 else ""

    # Look up tongue
    tongue_id = SIGNATURE_TO_TONGUE.get(signature)
    if tongue_id is None:
        return None

    return AetherVerse(
        tongue_id=tongue_id,
        signature=signature,
        content=content,
        line_number=line_number,
        indent_level=indent_level
    )


def parse_program(source: str, title: str = "Untitled") -> AetherProgram:
    """
    Parse a complete Aethercode program.

    Lines starting with # are comments.
    Empty lines are skipped.
    Each non-comment line should be a verse with signature prefix.
    """
    verses = []

    for i, line in enumerate(source.split('\n'), start=1):
        # Skip empty lines and comments
        if not line.strip() or line.strip().startswith('#'):
            continue

        verse = parse_verse(line, i)
        if verse:
            verses.append(verse)

    return AetherProgram(verses=verses, title=title)


# =============================================================================
# Execution Context
# =============================================================================

@dataclass
class AetherContext:
    """
    Execution context for Aethercode programs.

    Maintains state across verse execution including:
    - Variable bindings per tongue domain
    - 6D position in Spiralverse
    - Execution trace for proofs
    - Output buffer for results
    """
    variables: Dict[str, Any] = field(default_factory=dict)
    position: Position6D = field(default_factory=lambda: Position6D(0, 0, 0, 0, 0, 0))
    trace: List[Dict[str, Any]] = field(default_factory=list)
    output: List[str] = field(default_factory=list)
    audio_segments: List[np.ndarray] = field(default_factory=list)

    # Tongue-specific state
    tongue_state: Dict[TongueID, Dict[str, Any]] = field(
        default_factory=lambda: {t: {} for t in TongueID}
    )

    # Control flow
    call_stack: List[str] = field(default_factory=list)
    loop_counter: int = 0

    def set_var(self, name: str, value: Any, tongue: TongueID = None):
        """Set a variable, optionally scoped to a tongue."""
        if tongue:
            self.tongue_state[tongue][name] = value
        else:
            self.variables[name] = value

    def get_var(self, name: str, tongue: TongueID = None) -> Any:
        """Get a variable, checking tongue scope first."""
        if tongue and name in self.tongue_state[tongue]:
            return self.tongue_state[tongue][name]
        return self.variables.get(name)

    def emit(self, message: str):
        """Emit output message."""
        self.output.append(message)

    def record_trace(self, verse: AetherVerse, result: Any):
        """Record execution trace for proofs."""
        self.trace.append({
            "line": verse.line_number,
            "tongue": verse.tongue_id.value,
            "content": verse.content,
            "result": str(result),
            "timestamp": datetime.now(timezone.utc).isoformat()
        })


# =============================================================================
# Domain Handlers (One per Tongue)
# =============================================================================

class DomainHandler:
    """Base class for tongue domain handlers."""

    def __init__(self, tongue: TongueID):
        self.tongue = tongue
        self.domain = TONGUE_DOMAINS[tongue]

    def execute(self, verse: AetherVerse, ctx: AetherContext) -> Any:
        """Execute a verse in this domain. Override in subclasses."""
        raise NotImplementedError


class AxiomHandler(DomainHandler):
    """
    AXIOM/KO Handler - Directives and forward momentum.

    Commands:
    - INVOKE <func> [WITH <args>] : Call a function
    - DECLARE <name> AS <value>   : Declare variable
    - EMIT <message>              : Output message
    - HALT                        : Stop execution
    """

    def __init__(self):
        super().__init__(TongueID.AXIOM)
        self.builtins = {
            "greet": lambda name="World": f"Greetings, {name}!",
            "sum": lambda *args: sum(float(a) for a in args),
            "concat": lambda *args: "".join(str(a) for a in args),
        }

    def execute(self, verse: AetherVerse, ctx: AetherContext) -> Any:
        content = verse.content.strip()

        # INVOKE command
        if content.startswith("INVOKE"):
            match = re.match(r'INVOKE\s+(\w+)(?:\s+WITH\s+(.+))?', content)
            if match:
                func_name = match.group(1)
                args_str = match.group(2) or ""
                args = self._parse_args(args_str, ctx)

                # Check builtins first
                if func_name in self.builtins:
                    result = self.builtins[func_name](*args)
                    ctx.emit(f"[AXIOM] {result}")
                    return result

                # Check context functions
                func = ctx.get_var(func_name)
                if callable(func):
                    return func(*args)

                ctx.emit(f"[AXIOM] Unknown function: {func_name}")
                return None

        # DECLARE command
        if content.startswith("DECLARE"):
            match = re.match(r'DECLARE\s+(\w+)\s+AS\s+(.+)', content)
            if match:
                name = match.group(1)
                value = self._eval_value(match.group(2), ctx)
                ctx.set_var(name, value, self.tongue)
                ctx.emit(f"[AXIOM] Declared {name} = {value}")
                return value

        # EMIT command
        if content.startswith("EMIT"):
            message = content[4:].strip().strip('"\'')
            # Variable interpolation
            for var, val in ctx.variables.items():
                message = message.replace(f"${{{var}}}", str(val))
            ctx.emit(message)
            return message

        # HALT command
        if content == "HALT":
            raise StopIteration("HALT invoked")

        return None

    def _parse_args(self, args_str: str, ctx: AetherContext) -> List[Any]:
        """Parse argument string into list."""
        if not args_str:
            return []

        args = []
        # Simple parsing: split by comma, handle quoted strings
        for part in re.split(r',\s*(?=(?:[^"]*"[^"]*")*[^"]*$)', args_str):
            part = part.strip()
            args.append(self._eval_value(part, ctx))

        return args

    def _eval_value(self, expr: str, ctx: AetherContext) -> Any:
        """Evaluate a value expression."""
        expr = expr.strip()

        # String literal
        if expr.startswith('"') and expr.endswith('"'):
            return expr[1:-1]
        if expr.startswith("'") and expr.endswith("'"):
            return expr[1:-1]

        # Number
        try:
            if '.' in expr:
                return float(expr)
            return int(expr)
        except ValueError:
            pass

        # Variable reference
        return ctx.get_var(expr) or expr


class FlowHandler(DomainHandler):
    """
    FLOW/AV Handler - Transitions and control flow.

    Commands:
    - IF <cond> THEN              : Conditional branch
    - ELSE                        : Else branch
    - LOOP <n> TIMES              : Loop n times
    - YIELD                       : Yield control
    - BRANCH <label>              : Branch to label
    """

    def __init__(self):
        super().__init__(TongueID.FLOW)

    def execute(self, verse: AetherVerse, ctx: AetherContext) -> Any:
        content = verse.content.strip()

        # LOOP command
        if content.startswith("LOOP"):
            match = re.match(r'LOOP\s+(\d+)\s+TIMES', content)
            if match:
                iterations = int(match.group(1))
                ctx.loop_counter = iterations
                ctx.emit(f"[FLOW] Loop initialized: {iterations} iterations")
                return iterations

        # IF command (simplified - checks variable truthiness)
        if content.startswith("IF"):
            match = re.match(r'IF\s+(\w+)\s+THEN', content)
            if match:
                var_name = match.group(1)
                value = ctx.get_var(var_name)
                result = bool(value)
                ctx.set_var("__flow_condition", result, self.tongue)
                ctx.emit(f"[FLOW] Condition {var_name} = {result}")
                return result

        # YIELD command
        if content == "YIELD":
            ctx.emit("[FLOW] Yielding control...")
            return "YIELD"

        return None


class GlyphHandler(DomainHandler):
    """
    GLYPH/RU Handler - Structure and data definitions.

    Commands:
    - DEFINE <name> AS <type>     : Define data structure
    - STRUCTURE <name>            : Begin structure block
    - FIELD <name> : <type>       : Define field
    - HIERARCHY <levels>          : Define hierarchy
    """

    def __init__(self):
        super().__init__(TongueID.GLYPH)

    def execute(self, verse: AetherVerse, ctx: AetherContext) -> Any:
        content = verse.content.strip()

        # DEFINE command
        if content.startswith("DEFINE"):
            match = re.match(r'DEFINE\s+(\w+)\s+AS\s+(\w+)', content)
            if match:
                name = match.group(1)
                type_name = match.group(2)
                ctx.set_var(name, {"__type": type_name}, self.tongue)
                ctx.emit(f"[GLYPH] Defined {name} as {type_name}")
                return name

        # STRUCTURE command
        if content.startswith("STRUCTURE"):
            match = re.match(r'STRUCTURE\s+(\w+)', content)
            if match:
                name = match.group(1)
                ctx.set_var("__current_structure", name, self.tongue)
                ctx.set_var(name, {"__fields": []}, self.tongue)
                ctx.emit(f"[GLYPH] Structure {name} opened")
                return name

        # FIELD command
        if content.startswith("FIELD"):
            match = re.match(r'FIELD\s+(\w+)\s*:\s*(\w+)', content)
            if match:
                field_name = match.group(1)
                field_type = match.group(2)
                struct_name = ctx.get_var("__current_structure", self.tongue)
                if struct_name:
                    struct = ctx.get_var(struct_name, self.tongue)
                    if struct:
                        struct["__fields"].append((field_name, field_type))
                        ctx.emit(f"[GLYPH] Field {field_name}: {field_type}")
                        return field_name

        return None


class OracleHandler(DomainHandler):
    """
    ORACLE/CA Handler - Temporal dynamics and events.

    Commands:
    - AWAIT <duration>            : Wait for duration
    - SCHEDULE <event> AT <time>  : Schedule future event
    - TIMESTAMP                   : Get current timestamp
    - EVENT <name>                : Define event handler
    """

    def __init__(self):
        super().__init__(TongueID.ORACLE)

    def execute(self, verse: AetherVerse, ctx: AetherContext) -> Any:
        content = verse.content.strip()

        # AWAIT command
        if content.startswith("AWAIT"):
            match = re.match(r'AWAIT\s+(\d+(?:\.\d+)?)\s*(\w+)?', content)
            if match:
                duration = float(match.group(1))
                unit = match.group(2) or "ms"
                if unit == "s":
                    duration *= 1000
                ctx.emit(f"[ORACLE] Awaiting {duration}ms...")
                return duration

        # TIMESTAMP command
        if content == "TIMESTAMP":
            ts = datetime.now(timezone.utc).isoformat()
            ctx.set_var("__timestamp", ts, self.tongue)
            ctx.emit(f"[ORACLE] Timestamp: {ts}")
            return ts

        # SCHEDULE command
        if content.startswith("SCHEDULE"):
            match = re.match(r'SCHEDULE\s+(\w+)\s+AT\s+(.+)', content)
            if match:
                event_name = match.group(1)
                time_spec = match.group(2)
                ctx.emit(f"[ORACLE] Scheduled {event_name} at {time_spec}")
                return event_name

        return None


class CharmHandler(DomainHandler):
    """
    CHARM/UM Handler - Harmony and priority negotiation.

    Commands:
    - BALANCE <a> WITH <b>        : Balance two values
    - PRIORITY <level>            : Set priority level
    - HARMONIZE                   : Harmonize current state
    - NEGOTIATE <parties>         : Negotiate between parties
    """

    def __init__(self):
        super().__init__(TongueID.CHARM)

    def execute(self, verse: AetherVerse, ctx: AetherContext) -> Any:
        content = verse.content.strip()

        # BALANCE command
        if content.startswith("BALANCE"):
            match = re.match(r'BALANCE\s+(\w+)\s+WITH\s+(\w+)', content)
            if match:
                a = ctx.get_var(match.group(1)) or 0
                b = ctx.get_var(match.group(2)) or 0
                try:
                    balanced = (float(a) + float(b)) / 2
                    ctx.emit(f"[CHARM] Balanced: {balanced}")
                    return balanced
                except (ValueError, TypeError):
                    ctx.emit(f"[CHARM] Cannot balance non-numeric values")
                    return None

        # PRIORITY command
        if content.startswith("PRIORITY"):
            match = re.match(r'PRIORITY\s+(\d+)', content)
            if match:
                level = int(match.group(1))
                ctx.position = Position6D(
                    ctx.position.axiom, ctx.position.flow, ctx.position.glyph,
                    ctx.position.oracle, level, ctx.position.ledger
                )
                ctx.emit(f"[CHARM] Priority set to {level}")
                return level

        # HARMONIZE command
        if content == "HARMONIZE":
            # Calculate harmony score from 6D position
            pos = ctx.position
            harmony = (pos.charm + 50) / 100  # Normalize to 0-1
            ctx.emit(f"[CHARM] Harmony achieved: {harmony:.2%}")
            return harmony

        return None


class LedgerHandler(DomainHandler):
    """
    LEDGER/DR Handler - Authentication and record-keeping.

    Commands:
    - RECORD <data>               : Record data to ledger
    - VERIFY <signature>          : Verify a signature
    - SIGN <message>              : Sign a message
    - PROOF <statement>           : Generate proof
    """

    def __init__(self):
        super().__init__(TongueID.LEDGER)

    def execute(self, verse: AetherVerse, ctx: AetherContext) -> Any:
        content = verse.content.strip()

        # RECORD command
        if content.startswith("RECORD"):
            data = content[6:].strip().strip('"\'')
            hash_val = hashlib.sha256(data.encode()).hexdigest()[:16]
            record = {"data": data, "hash": hash_val, "timestamp": datetime.now(timezone.utc).isoformat()}
            ctx.trace.append({"ledger_record": record})
            ctx.emit(f"[LEDGER] Recorded: {hash_val}")
            return hash_val

        # SIGN command
        if content.startswith("SIGN"):
            message = content[4:].strip().strip('"\'')
            # Simple HMAC-like signature
            key = TONGUE_KEYS.get(ProtocolTongue.DR, b"default")
            sig_input = f"{message}:{key.hex()}"
            signature = hashlib.sha256(sig_input.encode()).hexdigest()[:32]
            ctx.emit(f"[LEDGER] Signed: {signature[:16]}...")
            return signature

        # PROOF command
        if content.startswith("PROOF"):
            statement = content[5:].strip().strip('"\'')
            # Generate proof from execution trace
            trace_hash = hashlib.sha256(str(ctx.trace).encode()).hexdigest()[:16]
            proof = {
                "statement": statement,
                "trace_hash": trace_hash,
                "verse_count": len(ctx.trace),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            ctx.emit(f"[LEDGER] Proof generated: {trace_hash}")
            return proof

        # VERIFY command
        if content.startswith("VERIFY"):
            sig = content[6:].strip()
            # Simplified verification (always true for demo)
            ctx.emit(f"[LEDGER] Verified: {sig[:16]}...")
            return True

        return None


# =============================================================================
# Polyphonic Chant Synthesis
# =============================================================================

class ChantSynthesizer:
    """
    Generate polyphonic chant from Aethercode execution.

    Each tongue maps to a frequency band, and verse execution
    produces audio segments that combine into polyphonic output.
    """

    def __init__(self, sample_rate: int = SAMPLE_RATE):
        self.sample_rate = sample_rate
        self.segments: List[np.ndarray] = []

    def synthesize_verse(self, verse: AetherVerse, duration: float = 0.3) -> np.ndarray:
        """Generate audio for a single verse execution."""
        freq_low, freq_high = verse.frequency_band

        # Map content length to frequency within band
        content_hash = hash(verse.content) % 100
        frequency = freq_low + (freq_high - freq_low) * (content_hash / 100)

        # Generate samples
        t = np.linspace(0, duration, int(self.sample_rate * duration), dtype=np.float32)

        # Base tone
        samples = 0.5 * np.sin(2 * np.pi * frequency * t)

        # Add harmonic based on tongue
        harmonic_mult = {
            TongueID.AXIOM: 2.0,   # Bright overtone
            TongueID.FLOW: 1.5,    # Subtle fifth
            TongueID.GLYPH: 3.0,   # Structural third
            TongueID.ORACLE: 2.5,  # Ethereal
            TongueID.CHARM: 1.25,  # Warm harmony
            TongueID.LEDGER: 4.0,  # Deep bass harmonic
        }

        mult = harmonic_mult.get(verse.tongue_id, 2.0)
        samples += 0.2 * np.sin(2 * np.pi * frequency * mult * t)

        # Apply envelope
        attack = int(0.02 * self.sample_rate)
        release = int(0.05 * self.sample_rate)
        envelope = np.ones_like(samples)
        envelope[:attack] = np.linspace(0, 1, attack)
        envelope[-release:] = np.linspace(1, 0, release)
        samples *= envelope

        return samples

    def add_segment(self, samples: np.ndarray):
        """Add audio segment to composition."""
        self.segments.append(samples)

    def render(self) -> np.ndarray:
        """Render all segments into final audio."""
        if not self.segments:
            return np.array([], dtype=np.float32)

        # Concatenate with slight overlap for smoothness
        overlap = int(0.02 * self.sample_rate)
        result = self.segments[0]

        for seg in self.segments[1:]:
            if len(result) >= overlap and len(seg) >= overlap:
                # Crossfade
                result[-overlap:] *= np.linspace(1, 0.5, overlap)
                seg[:overlap] *= np.linspace(0.5, 1, overlap)
                result[-overlap:] += seg[:overlap] * 0.5
                result = np.concatenate([result, seg[overlap:]])
            else:
                result = np.concatenate([result, seg])

        # Normalize
        max_val = np.max(np.abs(result))
        if max_val > 0:
            result = result / max_val * 0.9

        return result

    def export_wav(self, filename: str) -> bool:
        """Export rendered audio to .wav file."""
        samples = self.render()
        if len(samples) == 0:
            return False

        # Convert to int16
        int16_samples = (samples * 32767).astype(np.int16)

        # Write WAV file
        try:
            n_samples = len(int16_samples)
            with open(filename, 'wb') as f:
                # RIFF header
                f.write(b'RIFF')
                f.write(struct.pack('<I', 36 + n_samples * 2))
                f.write(b'WAVE')

                # fmt chunk
                f.write(b'fmt ')
                f.write(struct.pack('<I', 16))
                f.write(struct.pack('<H', 1))  # PCM
                f.write(struct.pack('<H', 1))  # Mono
                f.write(struct.pack('<I', self.sample_rate))
                f.write(struct.pack('<I', self.sample_rate * 2))
                f.write(struct.pack('<H', 2))
                f.write(struct.pack('<H', 16))

                # data chunk
                f.write(b'data')
                f.write(struct.pack('<I', n_samples * 2))
                f.write(int16_samples.tobytes())

            return True
        except Exception as e:
            print(f"[CHANT] Export error: {e}")
            return False


# =============================================================================
# Aethercode Interpreter
# =============================================================================

class AethercodeInterpreter:
    """
    Main interpreter for Aethercode programs.

    Executes verses through domain handlers and produces:
    - Text output
    - Polyphonic chant audio
    - RWP2-signed execution proofs
    """

    def __init__(self, synthesize_audio: bool = True):
        self.handlers: Dict[TongueID, DomainHandler] = {
            TongueID.AXIOM: AxiomHandler(),
            TongueID.FLOW: FlowHandler(),
            TongueID.GLYPH: GlyphHandler(),
            TongueID.ORACLE: OracleHandler(),
            TongueID.CHARM: CharmHandler(),
            TongueID.LEDGER: LedgerHandler(),
        }
        self.synthesize_audio = synthesize_audio
        self.synthesizer = ChantSynthesizer() if synthesize_audio else None

    def execute(self, program: AetherProgram, ctx: AetherContext = None) -> AetherContext:
        """
        Execute an Aethercode program.

        Returns the final execution context with:
        - output: List of emitted messages
        - trace: Execution trace for proofs
        - audio_segments: Generated audio (if synthesis enabled)
        """
        if ctx is None:
            ctx = AetherContext()

        ctx.emit(f"=== Executing: {program.title} ===")
        ctx.emit(f"Tongues: {', '.join(t.value for t in program.tongues_used)}")
        ctx.emit("")

        for verse in program.verses:
            try:
                handler = self.handlers.get(verse.tongue_id)
                if handler is None:
                    ctx.emit(f"[ERROR] No handler for tongue: {verse.tongue_id.value}")
                    continue

                # Execute verse
                result = handler.execute(verse, ctx)
                ctx.record_trace(verse, result)

                # Generate audio
                if self.synthesize_audio and self.synthesizer:
                    audio = self.synthesizer.synthesize_verse(verse)
                    self.synthesizer.add_segment(audio)
                    ctx.audio_segments.append(audio)

            except StopIteration as e:
                ctx.emit(f"[HALT] Execution stopped: {e}")
                break
            except Exception as e:
                ctx.emit(f"[ERROR] Line {verse.line_number}: {e}")

        ctx.emit("")
        ctx.emit(f"=== Execution Complete ===")
        ctx.emit(f"Verses executed: {len(ctx.trace)}")

        return ctx

    def execute_source(self, source: str, title: str = "Untitled") -> AetherContext:
        """Parse and execute source code."""
        program = parse_program(source, title)
        return self.execute(program)

    def export_proof(self, ctx: AetherContext, filename: str = None) -> RWP2Envelope:
        """
        Generate RWP2-signed proof of execution.
        """
        # Build proof payload
        proof_data = {
            "verses": len(ctx.trace),
            "output_hash": hashlib.sha256("\n".join(ctx.output).encode()).hexdigest()[:16],
            "trace_hash": hashlib.sha256(str(ctx.trace).encode()).hexdigest()[:16],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        payload = str(proof_data).encode()

        # Create envelope with all tongues used
        factory = EnvelopeFactory()
        tongues_used = [
            ProtocolTongue[t.value[:2].upper()] if hasattr(ProtocolTongue, t.value[:2].upper())
            else ProtocolTongue.KO
            for t in set(tv.tongue_id for tv in ctx.trace if hasattr(tv, 'tongue_id'))
        ] or [ProtocolTongue.KO]

        # Default to highest tier if multiple tongues
        tier = OperationTier.TIER_4 if len(tongues_used) >= 4 else OperationTier.TIER_2

        envelope = factory.create(
            command="AETHERCODE_PROOF",
            payload=payload,
            origin_tongue=ProtocolTongue.KO,  # Primary tongue
            tier=tier,
            aad=f"verses={len(ctx.trace)}"
        )

        return envelope

    def export_chant(self, filename: str) -> bool:
        """Export polyphonic chant to .wav file."""
        if self.synthesizer:
            return self.synthesizer.export_wav(filename)
        return False


# =============================================================================
# Demo Programs
# =============================================================================

HELLO_WORLD = """
# Hello World in Aethercode
# Each verse speaks through its sacred tongue

a3f7c2e1:INVOKE greet WITH "Spiralverse"
f7b3e5a9:RECORD "Program executed successfully"
e4f1c8d7:HARMONIZE
"""

FIBONACCI = """
# Fibonacci Sequence in Aethercode
# Demonstrates multi-tongue interleaving

c1d5a7f2:STRUCTURE Fibonacci
c1d5a7f2:FIELD n : Integer
c1d5a7f2:FIELD current : Integer
c1d5a7f2:FIELD previous : Integer

a3f7c2e1:DECLARE n AS 10
a3f7c2e1:DECLARE current AS 1
a3f7c2e1:DECLARE previous AS 0

b8e4d9c3:LOOP 10 TIMES
d9a2b6e8:TIMESTAMP

a3f7c2e1:EMIT "Fibonacci calculation complete"
f7b3e5a9:PROOF "Fibonacci sequence computed"
e4f1c8d7:HARMONIZE
"""

FULL_DEMO = """
# Full Spiralverse Demo - All Six Tongues
# "Invitation over Command, Connection over Control"

# GLYPH: Define structure
c1d5a7f2:STRUCTURE Agent
c1d5a7f2:FIELD name : String
c1d5a7f2:FIELD position : Vector6D

# AXIOM: Initialize
a3f7c2e1:DECLARE agent_name AS "Wanderer"
a3f7c2e1:INVOKE greet WITH "Aethercode"

# ORACLE: Mark time
d9a2b6e8:TIMESTAMP
d9a2b6e8:AWAIT 100 ms

# CHARM: Set harmony
e4f1c8d7:PRIORITY 75
e4f1c8d7:HARMONIZE

# FLOW: Control
b8e4d9c3:LOOP 3 TIMES
b8e4d9c3:YIELD

# LEDGER: Record proof
f7b3e5a9:RECORD "Six tongues spoke as one"
f7b3e5a9:SIGN "The roundtable convened"
f7b3e5a9:PROOF "All tongues in harmony"

# Final invocation
a3f7c2e1:EMIT "The Spiralverse awaits your next invocation."
"""


# =============================================================================
# Demo
# =============================================================================

def demo():
    """Demonstrate the Aethercode interpreter."""
    print("=" * 70)
    print("  AETHERCODE INTERPRETER - Esoteric Language for Spiralverse")
    print("  'Code as interwoven verses in 6 langues with polyphonic chant'")
    print("=" * 70)
    print()

    # Initialize interpreter
    interpreter = AethercodeInterpreter(synthesize_audio=True)

    # Demo 1: Hello World
    print("[DEMO 1] Hello World")
    print("-" * 60)
    ctx1 = interpreter.execute_source(HELLO_WORLD, "Hello World")
    for line in ctx1.output:
        print(f"  {line}")
    print()

    # Demo 2: Fibonacci
    print("[DEMO 2] Fibonacci Structure")
    print("-" * 60)
    interpreter2 = AethercodeInterpreter(synthesize_audio=True)
    ctx2 = interpreter2.execute_source(FIBONACCI, "Fibonacci")
    for line in ctx2.output:
        print(f"  {line}")
    print()

    # Demo 3: Full Six-Tongue Demo
    print("[DEMO 3] Full Six-Tongue Composition")
    print("-" * 60)
    interpreter3 = AethercodeInterpreter(synthesize_audio=True)
    ctx3 = interpreter3.execute_source(FULL_DEMO, "Six Tongues Symphony")
    for line in ctx3.output:
        print(f"  {line}")
    print()

    # Export chant
    print("[AUDIO] Exporting polyphonic chant...")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    chant_file = f"aethercode_chant_{timestamp}.wav"
    if interpreter3.export_chant(chant_file):
        print(f"  Exported: {chant_file}")
    else:
        print("  (No audio segments to export)")
    print()

    # Generate proof
    print("[PROOF] Generating RWP2 execution proof...")
    proof = interpreter3.export_proof(ctx3)
    print(f"  Nonce: {proof.nonce}")
    print(f"  Spelltext: {proof.spelltext}")
    print(f"  Tier: {proof.tier.value}")
    print(f"  Signatures: {[t.value for t in proof.signed_tongues]}")
    print()

    # Summary
    print("=" * 70)
    print("  Summary:")
    print(f"    Hello World:    {len(ctx1.trace)} verses")
    print(f"    Fibonacci:      {len(ctx2.trace)} verses")
    print(f"    Six Tongues:    {len(ctx3.trace)} verses")
    print()
    print("  Tongue Signatures:")
    for tongue, alph in TONGUE_ALPHABETS.items():
        domain = TONGUE_DOMAINS[tongue]
        freq_low, freq_high = TONGUE_FREQUENCIES[tongue]
        print(f"    {alph.signature}: {tongue.value:8s} -> {domain:10s} ({freq_low:.0f}-{freq_high:.0f}Hz)")
    print()
    print("  'The roundtable awaits your next invocation.'")
    print("=" * 70)


if __name__ == "__main__":
    demo()
