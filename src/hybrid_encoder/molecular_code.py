"""Molecular Code Mapper -- code as chemical molecules.

Maps code constructs to molecular structures:
  Functions  = molecules (collections of bonded atoms)
  Variables  = atoms (with valence = number of references)
  Imports    = ionic bonds (external connections)
  Calls      = covalent bonds (strong internal connections)
  Comments   = hydrogen bonds (weak stabilizing forces)
  Classes    = macromolecules (aggregated molecular clusters)

Each bond gets a Sacred Tongue affinity based on the nature of
the connection:
  KO: control flow bonds (if/for/while)
  AV: transport bonds (imports, returns)
  RU: constraint bonds (assertions, type hints)
  CA: compute bonds (arithmetic, function calls)
  UM: hidden bonds (closures, private refs)
  DR: structural bonds (class definitions, inheritance)

@layer Layer 3, Layer 9
@component HybridEncoder.MolecularCode
"""
from __future__ import annotations

import ast
import re
from typing import Dict, List

from src.hybrid_encoder.types import MolecularBond, TONGUE_NAMES

# Keyword -> tongue affinity mapping
_CONTROL_FLOW = {"if", "else", "elif", "for", "while", "break", "continue", "match", "case"}
_TRANSPORT = {"import", "from", "return", "yield", "raise"}
_CONSTRAINT = {"assert", "isinstance", "issubclass", "typing", "Optional", "List", "Dict", "Tuple"}
_COMPUTE = {"sum", "min", "max", "abs", "len", "range", "map", "filter", "sorted", "enumerate"}

# Regex fallbacks for non-Python or unparseable code
_RE_IMPORT = re.compile(r"^\s*(?:from\s+\S+\s+)?import\s+", re.MULTILINE)
_RE_FUNCTION = re.compile(r"^\s*def\s+(\w+)", re.MULTILINE)
_RE_CLASS = re.compile(r"^\s*class\s+(\w+)", re.MULTILINE)
_RE_COMMENT = re.compile(r"#.*$", re.MULTILINE)
_RE_CALL = re.compile(r"(\w+)\s*\(")
_RE_IF = re.compile(r"^\s*(?:if|elif|else|for|while)\b", re.MULTILINE)
_RE_ASSIGN = re.compile(r"(\w+)\s*=(?!=)", re.MULTILINE)


class MolecularCodeMapper:
    """Map Python code text into molecular bond structures."""

    def map_code(self, code_text: str) -> List[MolecularBond]:
        """Parse code and extract molecular bonds.

        Uses ast.parse() for Python code, falls back to regex
        for non-Python or unparseable code.
        """
        try:
            tree = ast.parse(code_text)
            return self._ast_bonds(tree)
        except SyntaxError:
            return self._regex_bonds(code_text)

    def _ast_bonds(self, tree: ast.Module) -> List[MolecularBond]:
        """Extract bonds from AST nodes."""
        bonds: List[MolecularBond] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    bonds.append(MolecularBond(
                        element_a="module",
                        element_b=alias.name,
                        bond_type="ionic",
                        valence=1,
                        tongue_affinity="AV",
                    ))
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or "unknown"
                for alias in node.names:
                    bonds.append(MolecularBond(
                        element_a=mod,
                        element_b=alias.name,
                        bond_type="ionic",
                        valence=1,
                        tongue_affinity="AV",
                    ))
            elif isinstance(node, ast.FunctionDef):
                bonds.append(MolecularBond(
                    element_a="scope",
                    element_b=node.name,
                    bond_type="covalent",
                    valence=len(node.args.args),
                    tongue_affinity="CA",
                ))
            elif isinstance(node, ast.ClassDef):
                bases = [
                    getattr(b, "id", getattr(b, "attr", "?"))
                    for b in node.bases
                ]
                for base in bases:
                    bonds.append(MolecularBond(
                        element_a=node.name,
                        element_b=str(base),
                        bond_type="covalent",
                        valence=2,
                        tongue_affinity="DR",
                    ))
                if not bases:
                    bonds.append(MolecularBond(
                        element_a="scope",
                        element_b=node.name,
                        bond_type="covalent",
                        valence=2,
                        tongue_affinity="DR",
                    ))
            elif isinstance(node, ast.Call):
                func_name = ""
                if isinstance(node.func, ast.Name):
                    func_name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    func_name = node.func.attr
                if func_name:
                    bonds.append(MolecularBond(
                        element_a="caller",
                        element_b=func_name,
                        bond_type="covalent",
                        valence=len(node.args),
                        tongue_affinity="CA",
                    ))
            elif isinstance(node, (ast.If, ast.For, ast.While)):
                bonds.append(MolecularBond(
                    element_a="flow",
                    element_b=type(node).__name__.lower(),
                    bond_type="covalent",
                    valence=1,
                    tongue_affinity="KO",
                ))
            elif isinstance(node, ast.Assert):
                bonds.append(MolecularBond(
                    element_a="constraint",
                    element_b="assert",
                    bond_type="covalent",
                    valence=1,
                    tongue_affinity="RU",
                ))
            elif isinstance(node, ast.Return):
                bonds.append(MolecularBond(
                    element_a="function",
                    element_b="return",
                    bond_type="covalent",
                    valence=1,
                    tongue_affinity="AV",
                ))

        return bonds

    def _regex_bonds(self, code: str) -> List[MolecularBond]:
        """Fallback bond extraction via regex patterns."""
        bonds: List[MolecularBond] = []

        for m in _RE_IMPORT.finditer(code):
            bonds.append(MolecularBond(
                element_a="module", element_b=m.group().strip(),
                bond_type="ionic", valence=1, tongue_affinity="AV",
            ))
        for m in _RE_FUNCTION.finditer(code):
            bonds.append(MolecularBond(
                element_a="scope", element_b=m.group(1),
                bond_type="covalent", valence=1, tongue_affinity="CA",
            ))
        for m in _RE_CLASS.finditer(code):
            bonds.append(MolecularBond(
                element_a="scope", element_b=m.group(1),
                bond_type="covalent", valence=2, tongue_affinity="DR",
            ))
        for m in _RE_IF.finditer(code):
            bonds.append(MolecularBond(
                element_a="flow", element_b="control",
                bond_type="covalent", valence=1, tongue_affinity="KO",
            ))
        for m in _RE_COMMENT.finditer(code):
            bonds.append(MolecularBond(
                element_a="doc", element_b="comment",
                bond_type="hydrogen", valence=0, tongue_affinity="UM",
            ))

        return bonds

    def valence_spectrum(self, bonds: List[MolecularBond]) -> Dict[str, int]:
        """Compute tongue-wise valence spectrum.

        Returns {tongue: total_valence} -- higher valence means
        more connections in that tongue domain.
        """
        spectrum: Dict[str, int] = {t: 0 for t in TONGUE_NAMES}
        for bond in bonds:
            if bond.tongue_affinity in spectrum:
                spectrum[bond.tongue_affinity] += bond.valence
        return spectrum

    def stability_score(self, bonds: List[MolecularBond]) -> float:
        """Compute molecular stability.

        Ratio of stabilizing bonds (hydrogen, covalent) to
        destabilizing (high-valence ionic).  Analogous to
        chemical stability = defensive posture.
        """
        if not bonds:
            return 1.0

        stabilizing = sum(
            1 for b in bonds if b.bond_type in ("hydrogen", "covalent")
        )
        destabilizing = sum(
            b.valence for b in bonds if b.bond_type == "ionic"
        )

        total = stabilizing + destabilizing
        if total == 0:
            return 1.0
        return stabilizing / total
