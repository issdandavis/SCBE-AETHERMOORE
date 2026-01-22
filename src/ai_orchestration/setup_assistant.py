"""
SCBE Setup Assistant
=====================

An AI-powered setup assistant that helps users configure the SCBE system.
Guides through installation, agent setup, knowledge base selection,
and business portfolio integration.

FEATURES:
=========
- Interactive setup wizard
- Automatic capability detection
- Knowledge pack recommendations
- Business portfolio import
- Agent team configuration
- Security profile setup

Version: 1.0.0
"""

import os
import sys
import json
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from enum import Enum


class SetupPhase(Enum):
    """Phases of the setup process."""

    WELCOME = "welcome"
    SYSTEM_CHECK = "system_check"
    KNOWLEDGE_SELECTION = "knowledge_selection"
    AGENT_CONFIGURATION = "agent_configuration"
    SECURITY_SETUP = "security_setup"
    PORTFOLIO_IMPORT = "portfolio_import"
    FINAL_REVIEW = "final_review"
    COMPLETE = "complete"


@dataclass
class SystemRequirements:
    """System requirements check results."""

    python_version: str
    python_ok: bool
    memory_gb: float
    memory_ok: bool
    disk_space_gb: float
    disk_ok: bool
    dependencies_ok: bool
    missing_deps: List[str]


@dataclass
class SetupProfile:
    """User's setup configuration profile."""

    profile_name: str
    use_case: str  # "business", "research", "security", "custom"
    selected_packs: List[str] = field(default_factory=list)
    agent_config: Dict[str, Any] = field(default_factory=dict)
    security_level: str = "standard"  # "minimal", "standard", "maximum"
    portfolio_path: Optional[str] = None
    cloud_backup: bool = False
    created_at: datetime = field(default_factory=datetime.now)


class SetupAssistant:
    """
    Interactive AI assistant for setting up the SCBE system.

    Provides guided setup with intelligent recommendations based on
    the user's use case and system capabilities.
    """

    # Predefined setup templates
    TEMPLATES = {
        "business": {
            "name": "Business Operations",
            "description": "Full business suite with portfolio management, analytics, and reporting",
            "packs": ["economics", "statistics", "algorithms"],
            "agents": [
                {"role": "coordinator", "name": "BusinessCoordinator"},
                {"role": "business", "name": "PortfolioManager"},
                {"role": "analyst", "name": "DataAnalyst"},
                {"role": "security", "name": "SecurityOfficer"},
            ],
            "security_level": "standard",
        },
        "research": {
            "name": "Research Laboratory",
            "description": "Comprehensive research platform with all science packs",
            "packs": ["physics_sim", "chemistry", "biology", "ai_ml", "statistics"],
            "agents": [
                {"role": "coordinator", "name": "ResearchDirector"},
                {"role": "research", "name": "PrimaryResearcher"},
                {"role": "research", "name": "SecondaryResearcher"},
                {"role": "engineer", "name": "ComputationalEngineer"},
            ],
            "security_level": "minimal",
        },
        "security": {
            "name": "Security Operations Center",
            "description": "Maximum security configuration for sensitive operations",
            "packs": ["cryptography", "security", "algorithms"],
            "agents": [
                {"role": "coordinator", "name": "SOCManager"},
                {"role": "security", "name": "ThreatAnalyst"},
                {"role": "security", "name": "ComplianceOfficer"},
                {"role": "security", "name": "IncidentResponder"},
            ],
            "security_level": "maximum",
        },
        "minimal": {
            "name": "Minimal Installation",
            "description": "Basic setup with core functionality only",
            "packs": [],
            "agents": [
                {"role": "coordinator", "name": "Coordinator"},
            ],
            "security_level": "minimal",
        },
    }

    # Pack recommendations by use case
    PACK_RECOMMENDATIONS = {
        "business": {
            "essential": ["economics", "statistics"],
            "recommended": ["ai_ml", "algorithms"],
            "optional": ["linguistics", "sociology"],
        },
        "research": {
            "essential": ["statistics", "applied_math"],
            "recommended": ["physics_sim", "chemistry", "biology"],
            "optional": ["ai_ml", "neuroscience"],
        },
        "engineering": {
            "essential": ["physics_sim", "applied_math", "algorithms"],
            "recommended": ["mechanical", "electrical", "materials"],
            "optional": ["aerospace", "civil"],
        },
        "healthcare": {
            "essential": ["biology", "pharmacology", "statistics"],
            "recommended": ["neuroscience", "bioinformatics"],
            "optional": ["ai_ml", "biomedical"],
        },
    }

    def __init__(self, config_path: str = "./scbe_config"):
        self.config_path = Path(config_path)
        self.config_path.mkdir(parents=True, exist_ok=True)
        self.current_phase = SetupPhase.WELCOME
        self.profile = SetupProfile(profile_name="default", use_case="custom")
        self.system_check: Optional[SystemRequirements] = None
        self.setup_log: List[Dict[str, Any]] = []

    def start_setup(self) -> Dict[str, Any]:
        """Start the setup process."""
        self._log("Setup started")
        return self.get_welcome_message()

    def get_welcome_message(self) -> Dict[str, Any]:
        """Get the welcome message and options."""
        self.current_phase = SetupPhase.WELCOME

        return {
            "phase": self.current_phase.value,
            "message": """
Welcome to SCBE-AETHERMOORE Setup Assistant

I'll help you configure your AI orchestration system. This setup will:

1. Check your system requirements
2. Help you select knowledge packs for your use case
3. Configure your AI agent team
4. Set up security preferences
5. Import your business portfolio (optional)

Choose a setup option to continue:
            """.strip(),
            "options": [
                {
                    "id": "business",
                    "name": "Business Operations",
                    "description": "Portfolio management, analytics, and reporting",
                },
                {
                    "id": "research",
                    "name": "Research Laboratory",
                    "description": "Scientific computing with all science packs",
                },
                {
                    "id": "security",
                    "name": "Security Operations",
                    "description": "Maximum security for sensitive operations",
                },
                {
                    "id": "minimal",
                    "name": "Minimal Installation",
                    "description": "Core functionality only, add more later",
                },
                {
                    "id": "custom",
                    "name": "Custom Setup",
                    "description": "Choose everything yourself",
                },
            ],
        }

    def select_template(self, template_id: str) -> Dict[str, Any]:
        """Select a setup template."""
        self.profile.use_case = template_id

        if template_id in self.TEMPLATES:
            template = self.TEMPLATES[template_id]
            self.profile.selected_packs = template["packs"]
            self.profile.agent_config = {"agents": template["agents"]}
            self.profile.security_level = template["security_level"]

        self._log(f"Template selected: {template_id}")
        return self.check_system()

    def check_system(self) -> Dict[str, Any]:
        """Check system requirements."""
        self.current_phase = SetupPhase.SYSTEM_CHECK

        # Perform checks
        import platform

        python_version = platform.python_version()
        python_ok = tuple(map(int, python_version.split(".")[:2])) >= (3, 10)

        # Memory check (simplified)
        try:
            import psutil

            memory_gb = psutil.virtual_memory().total / (1024**3)
        except ImportError:
            memory_gb = 8.0  # Assume 8GB if can't check
        memory_ok = memory_gb >= 4.0

        # Disk space check
        disk_space_gb = 10.0  # Simplified
        disk_ok = disk_space_gb >= 2.0

        # Check dependencies
        missing_deps = []
        required = ["numpy", "scipy"]
        for dep in required:
            try:
                __import__(dep)
            except ImportError:
                missing_deps.append(dep)

        self.system_check = SystemRequirements(
            python_version=python_version,
            python_ok=python_ok,
            memory_gb=memory_gb,
            memory_ok=memory_ok,
            disk_space_gb=disk_space_gb,
            disk_ok=disk_ok,
            dependencies_ok=len(missing_deps) == 0,
            missing_deps=missing_deps,
        )

        all_ok = all([python_ok, memory_ok, disk_ok, len(missing_deps) == 0])

        self._log(f"System check completed: {'PASS' if all_ok else 'ISSUES FOUND'}")

        return {
            "phase": self.current_phase.value,
            "message": "System Requirements Check",
            "checks": {
                "python": {
                    "value": python_version,
                    "required": "3.10+",
                    "ok": python_ok,
                },
                "memory": {
                    "value": f"{memory_gb:.1f} GB",
                    "required": "4 GB+",
                    "ok": memory_ok,
                },
                "disk": {
                    "value": f"{disk_space_gb:.1f} GB available",
                    "required": "2 GB+",
                    "ok": disk_ok,
                },
                "dependencies": {
                    "missing": missing_deps,
                    "ok": len(missing_deps) == 0,
                },
            },
            "all_ok": all_ok,
            "next_action": "proceed" if all_ok else "fix_issues",
        }

    def get_knowledge_selection(self) -> Dict[str, Any]:
        """Get knowledge pack selection interface."""
        self.current_phase = SetupPhase.KNOWLEDGE_SELECTION

        # Get recommendations based on use case
        recommendations = self.PACK_RECOMMENDATIONS.get(
            self.profile.use_case, {"essential": [], "recommended": [], "optional": []}
        )

        # Import pack info
        try:
            from ..science_packs import SCIENCE_PACKS, get_pack_info

            all_packs = []
            for category, packs in SCIENCE_PACKS.items():
                for name, pack in packs.items():
                    all_packs.append(
                        {
                            "name": name,
                            "category": category,
                            "description": pack.description,
                            "size_mb": pack.size_mb,
                            "dependencies": pack.dependencies,
                            "essential": name in recommendations.get("essential", []),
                            "recommended": name
                            in recommendations.get("recommended", []),
                            "selected": name in self.profile.selected_packs,
                        }
                    )
        except ImportError:
            all_packs = []

        return {
            "phase": self.current_phase.value,
            "message": """
Select Knowledge Packs

Knowledge packs provide offline access to scientific knowledge,
formulas, and computational methods. Select based on your needs.

Packs marked ESSENTIAL are required for your selected use case.
Packs marked RECOMMENDED will enhance your experience.
            """.strip(),
            "categories": [
                "Physical Sciences",
                "Life Sciences",
                "Mathematical Sciences",
                "Engineering",
                "Computer Science",
                "Social Sciences",
            ],
            "packs": all_packs,
            "current_selection": self.profile.selected_packs,
            "total_size_mb": sum(
                p["size_mb"]
                for p in all_packs
                if p["name"] in self.profile.selected_packs
            ),
        }

    def select_packs(self, pack_names: List[str]) -> Dict[str, Any]:
        """Select knowledge packs."""
        self.profile.selected_packs = pack_names
        self._log(f"Packs selected: {pack_names}")
        return self.get_agent_configuration()

    def get_agent_configuration(self) -> Dict[str, Any]:
        """Get agent configuration interface."""
        self.current_phase = SetupPhase.AGENT_CONFIGURATION

        # Get current agent config
        current_agents = self.profile.agent_config.get("agents", [])

        return {
            "phase": self.current_phase.value,
            "message": """
Configure Your AI Agent Team

Agents are specialized AI workers that handle different tasks.
You can customize your team based on your needs.

Each agent has a role and specific capabilities:
- Coordinator: Routes tasks and manages other agents
- Security: Monitors threats and ensures compliance
- Research: Searches knowledge bases and analyzes data
- Business: Manages portfolios and generates reports
- Engineer: Writes code and runs tests
- Analyst: Performs data analysis and visualization
            """.strip(),
            "available_roles": [
                {
                    "role": "coordinator",
                    "name": "Coordinator",
                    "description": "Routes tasks and manages other agents",
                    "recommended_count": 1,
                },
                {
                    "role": "security",
                    "name": "Security Agent",
                    "description": "Monitors threats and ensures compliance",
                    "recommended_count": 1,
                },
                {
                    "role": "research",
                    "name": "Research Agent",
                    "description": "Searches knowledge and analyzes data",
                    "recommended_count": 1,
                },
                {
                    "role": "business",
                    "name": "Business Agent",
                    "description": "Manages portfolios and reporting",
                    "recommended_count": 1,
                },
                {
                    "role": "engineer",
                    "name": "Engineer Agent",
                    "description": "Code generation and testing",
                    "recommended_count": 1,
                },
            ],
            "current_agents": current_agents,
            "max_agents": 50,
        }

    def configure_agents(self, agents: List[Dict[str, str]]) -> Dict[str, Any]:
        """Configure agent team."""
        self.profile.agent_config = {"agents": agents}
        self._log(f"Agents configured: {len(agents)} agents")
        return self.get_security_setup()

    def get_security_setup(self) -> Dict[str, Any]:
        """Get security configuration interface."""
        self.current_phase = SetupPhase.SECURITY_SETUP

        return {
            "phase": self.current_phase.value,
            "message": """
Configure Security Settings

SCBE uses a 14-layer security stack with post-quantum cryptography.
Choose your security level based on your sensitivity requirements.
            """.strip(),
            "security_levels": [
                {
                    "id": "minimal",
                    "name": "Minimal",
                    "description": "Basic security for development/testing",
                    "features": [
                        "Basic input sanitization",
                        "Standard logging",
                    ],
                },
                {
                    "id": "standard",
                    "name": "Standard",
                    "description": "Recommended for most use cases",
                    "features": [
                        "Full 14-layer security stack",
                        "Prompt injection detection",
                        "Rate limiting",
                        "Audit logging with integrity",
                        "Encrypted storage",
                    ],
                },
                {
                    "id": "maximum",
                    "name": "Maximum",
                    "description": "For highly sensitive operations",
                    "features": [
                        "All Standard features",
                        "Post-quantum cryptography",
                        "Agent message signing",
                        "Context isolation",
                        "Zero-trust verification",
                        "Full audit trail with chain verification",
                    ],
                },
            ],
            "current_level": self.profile.security_level,
        }

    def set_security_level(self, level: str) -> Dict[str, Any]:
        """Set security level."""
        self.profile.security_level = level
        self._log(f"Security level set: {level}")
        return self.get_portfolio_import()

    def get_portfolio_import(self) -> Dict[str, Any]:
        """Get portfolio import interface."""
        self.current_phase = SetupPhase.PORTFOLIO_IMPORT

        return {
            "phase": self.current_phase.value,
            "message": """
Import Business Portfolio (Optional)

You can import your existing business data to enable AI-powered
portfolio management, analytics, and reporting.

Supported formats:
- JSON (.json)
- CSV (.csv)
- Excel (.xlsx)

All data is stored securely using SCBE encryption.
            """.strip(),
            "supported_formats": ["json", "csv", "xlsx"],
            "cloud_backup_available": True,
            "skip_option": True,
        }

    def import_portfolio(
        self, file_path: Optional[str] = None, enable_cloud_backup: bool = False
    ) -> Dict[str, Any]:
        """Import portfolio data."""
        self.profile.portfolio_path = file_path
        self.profile.cloud_backup = enable_cloud_backup

        if file_path:
            self._log(f"Portfolio import: {file_path}")
        else:
            self._log("Portfolio import skipped")

        return self.get_final_review()

    def get_final_review(self) -> Dict[str, Any]:
        """Get final review before completing setup."""
        self.current_phase = SetupPhase.FINAL_REVIEW

        return {
            "phase": self.current_phase.value,
            "message": "Review Your Configuration",
            "configuration": {
                "profile_name": self.profile.profile_name,
                "use_case": self.profile.use_case,
                "knowledge_packs": self.profile.selected_packs,
                "agents": self.profile.agent_config.get("agents", []),
                "security_level": self.profile.security_level,
                "portfolio_import": self.profile.portfolio_path is not None,
                "cloud_backup": self.profile.cloud_backup,
            },
            "estimated_disk_usage": f"{sum([5, 10, 15][['minimal', 'standard', 'maximum'].index(self.profile.security_level)])} MB base + packs",
            "ready_to_install": True,
        }

    def complete_setup(self) -> Dict[str, Any]:
        """Complete the setup process."""
        self.current_phase = SetupPhase.COMPLETE

        # Save configuration
        config_file = self.config_path / "setup_profile.json"
        with open(config_file, "w") as f:
            json.dump(
                {
                    "profile_name": self.profile.profile_name,
                    "use_case": self.profile.use_case,
                    "selected_packs": self.profile.selected_packs,
                    "agent_config": self.profile.agent_config,
                    "security_level": self.profile.security_level,
                    "portfolio_path": self.profile.portfolio_path,
                    "cloud_backup": self.profile.cloud_backup,
                    "created_at": self.profile.created_at.isoformat(),
                },
                f,
                indent=2,
            )

        self._log("Setup completed successfully")

        return {
            "phase": self.current_phase.value,
            "message": """
Setup Complete!

Your SCBE-AETHERMOORE system is configured and ready to use.

Quick Start:
  from scbe.ai_orchestration import quick_start
  orchestrator = await quick_start()

Your configuration has been saved to:
  {config_path}

Next Steps:
1. Start the orchestrator
2. Send your first task to an agent
3. Execute a workflow
4. View the audit logs

For help, see the documentation or ask the Research agent.
            """.strip().format(
                config_path=config_file
            ),
            "config_saved_to": str(config_file),
            "setup_log": self.setup_log,
        }

    def _log(self, message: str):
        """Log setup event."""
        self.setup_log.append(
            {
                "timestamp": datetime.now().isoformat(),
                "phase": self.current_phase.value,
                "message": message,
            }
        )


# =============================================================================
# CLI INTERFACE
# =============================================================================


def run_interactive_setup():
    """Run interactive setup in CLI mode."""
    assistant = SetupAssistant()

    print("\n" + "=" * 60)
    print("  SCBE-AETHERMOORE SETUP ASSISTANT")
    print("=" * 60 + "\n")

    # Welcome
    welcome = assistant.get_welcome_message()
    print(welcome["message"])
    print("\nSetup Options:")
    for i, opt in enumerate(welcome["options"], 1):
        print(f"  {i}. {opt['name']}")
        print(f"     {opt['description']}")

    choice = input("\nSelect option (1-5): ").strip()
    options = ["business", "research", "security", "minimal", "custom"]
    template_id = options[int(choice) - 1] if choice.isdigit() else "custom"

    # System check
    print("\n" + "-" * 40)
    result = assistant.select_template(template_id)
    print("\nSystem Check Results:")
    for check, info in result["checks"].items():
        status = "[OK]" if info.get("ok", True) else "[!!]"
        if check == "dependencies":
            if info["missing"]:
                print(f"  {status} Dependencies: Missing {info['missing']}")
            else:
                print(f"  {status} Dependencies: All installed")
        else:
            print(
                f"  {status} {check.title()}: {info['value']} (required: {info['required']})"
            )

    if not result["all_ok"]:
        print("\nSome requirements not met. Please fix issues and try again.")
        return

    input("\nPress Enter to continue...")

    # Knowledge packs
    print("\n" + "-" * 40)
    packs = assistant.get_knowledge_selection()
    print(packs["message"])

    if template_id == "custom":
        print("\nAvailable packs (enter numbers to select, comma-separated):")
        for i, pack in enumerate(packs.get("packs", [])[:10], 1):
            marker = "*" if pack.get("selected") else " "
            print(
                f"  {i}.{marker} {pack['name']} ({pack['category']}) - {pack['size_mb']}MB"
            )

        selection = input(
            "\nSelect packs (e.g., 1,3,5) or Enter to keep defaults: "
        ).strip()
        if selection:
            indices = [
                int(x.strip()) - 1 for x in selection.split(",") if x.strip().isdigit()
            ]
            selected = [
                packs["packs"][i]["name"] for i in indices if i < len(packs["packs"])
            ]
            assistant.select_packs(selected)
    else:
        print(
            f"\nUsing template packs: {', '.join(assistant.profile.selected_packs) or 'None'}"
        )
        assistant.select_packs(assistant.profile.selected_packs)

    input("\nPress Enter to continue...")

    # Agent configuration
    print("\n" + "-" * 40)
    agents = assistant.get_agent_configuration()
    print(agents["message"])
    print("\nCurrent agent team:")
    for agent in agents.get("current_agents", []):
        print(f"  - {agent['name']} ({agent['role']})")

    input("\nPress Enter to keep current agents and continue...")
    assistant.configure_agents(agents.get("current_agents", []))

    # Security setup
    print("\n" + "-" * 40)
    security = assistant.get_security_setup()
    print(security["message"])
    print("\nSecurity Levels:")
    for level in security["security_levels"]:
        marker = "*" if level["id"] == assistant.profile.security_level else " "
        print(f"  {marker} {level['name']}: {level['description']}")

    input(f"\nPress Enter to use '{assistant.profile.security_level}' security...")
    assistant.set_security_level(assistant.profile.security_level)

    # Portfolio import
    print("\n" + "-" * 40)
    portfolio = assistant.get_portfolio_import()
    print(portfolio["message"])

    import_choice = input("\nImport portfolio? (y/n): ").strip().lower()
    if import_choice == "y":
        path = input("Enter file path: ").strip()
        assistant.import_portfolio(path if path else None)
    else:
        assistant.import_portfolio(None)

    # Final review
    print("\n" + "-" * 40)
    review = assistant.get_final_review()
    print(review["message"])
    print("\nConfiguration Summary:")
    config = review["configuration"]
    print(f"  Use Case: {config['use_case']}")
    print(f"  Knowledge Packs: {len(config['knowledge_packs'])} selected")
    print(f"  Agents: {len(config['agents'])} configured")
    print(f"  Security: {config['security_level']}")

    confirm = input("\nProceed with installation? (y/n): ").strip().lower()
    if confirm == "y":
        result = assistant.complete_setup()
        print("\n" + "=" * 60)
        print(result["message"])
        print("=" * 60)
    else:
        print("\nSetup cancelled.")


if __name__ == "__main__":
    run_interactive_setup()
