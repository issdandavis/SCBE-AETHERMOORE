"""Companion-package discovery for the lightweight SCBE agent bus.

This module intentionally does not install anything. It only explains which
SCBE package unlocks a requested feature so users can keep their local install
small and add companion packs when they actually need them.
"""

from __future__ import annotations

from typing import Literal, TypedDict

CompanionName = Literal[
    "scbe-aethermoore",
    "scbe-agent-bus",
    "@scbe/kernel",
    "scbe-sixtongues",
]


class CompanionPackage(TypedDict):
    name: CompanionName
    ecosystem: Literal["npm", "pypi"]
    install: str
    purpose: str
    features: list[str]
    heavy: bool


class CompanionRecommendation(TypedDict):
    feature: str
    package: CompanionName
    install: str
    reason: str


COMPANION_PACKAGES: list[CompanionPackage] = [
    {
        "name": "scbe-aethermoore",
        "ecosystem": "npm",
        "install": "npm install scbe-aethermoore",
        "purpose": "Core TypeScript governance, tokenizer, harmonic wall, and operator APIs.",
        "features": ["governance", "operator-manifold", "tokenizer", "browser", "node"],
        "heavy": False,
    },
    {
        "name": "scbe-agent-bus",
        "ecosystem": "pypi",
        "install": "pip install scbe-agent-bus",
        "purpose": "Python event runner surface for agent-bus workflows and governed batch dispatch.",
        "features": ["agent-bus", "python", "batch-dispatch", "workspace"],
        "heavy": False,
    },
    {
        "name": "@scbe/kernel",
        "ecosystem": "npm",
        "install": "npm install @scbe/kernel",
        "purpose": "Smaller kernel-level package for Sacred Tongues and core math without the full repo.",
        "features": ["kernel", "sacred-tongues", "lightweight-math"],
        "heavy": False,
    },
    {
        "name": "scbe-sixtongues",
        "ecosystem": "pypi",
        "install": "pip install scbe-sixtongues",
        "purpose": "Standalone Python Six Tongues tokenizer package for local scripts.",
        "features": ["sacred-tongues", "python", "tokenizer"],
        "heavy": False,
    },
]


def _normalize_feature(feature: str) -> str:
    return "-".join(feature.strip().lower().replace("_", " ").split())


def recommend_companion_packages(
    requested_features: list[str],
    available_packages: list[CompanionName] | None = None,
) -> list[CompanionRecommendation]:
    """Return optional package prompts for missing features.

    The first matching package is returned for each feature. Already available
    packages are skipped so this function can be used in CLIs without nagging
    users to install what they already have.
    """

    available = set(available_packages or ["scbe-agent-bus"])
    recommendations: list[CompanionRecommendation] = []
    for raw_feature in requested_features:
        feature = _normalize_feature(raw_feature)
        provider = next(
            (
                package
                for package in COMPANION_PACKAGES
                if package["name"] not in available
                and feature
                in {_normalize_feature(item) for item in package["features"]}
            ),
            None,
        )
        if provider is None:
            continue
        recommendations.append(
            {
                "feature": feature,
                "package": provider["name"],
                "install": provider["install"],
                "reason": (
                    f"{provider['name']} provides {feature} without being installed "
                    "as a forced dependency."
                ),
            }
        )
    return recommendations
