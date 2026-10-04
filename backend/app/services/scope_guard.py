"""
Scope Guard Service.

Enforces domain boundary: GraphTech strictly specializes in Computer Science
and IT technical architecture diagrams.

Rejects requests for:
  - Civil / Architectural construction (floor plans, building elevations, plumbing, HVAC)
  - Mechanical engineering (gearboxes, machine parts, engines, CAD assemblies)
  - Electrical hardware schematics (analog PCB wiring, resistors, breadboards)
  - Creative / Non-technical artwork (portraits, landscapes, logos, paintings)
"""

from dataclasses import dataclass
import re
from typing import Optional


@dataclass
class ScopeCheckResult:
    is_in_scope: bool
    detected_domain: Optional[str] = None
    rejection_reason: Optional[str] = None


# Out-of-scope keyword patterns with specific rejection context
OUT_OF_SCOPE_RULES = [
    {
        "domain": "Civil / Architectural Engineering",
        "patterns": [
            r"\b(floor\s*plan|house\s*plan|building\s*blueprint|elevation\s*plan)\b",
            r"\b(bedroom|bathroom|kitchen\s*layout|living\s*room\s*plan)\b",
            r"\b(plumbing\s*(diagram|schematic)|hvac\s*(diagram|layout))\b",
            r"\b(civil\s*engineering|structural\s*foundation|concrete\s*beam)\b",
        ],
        "reason": (
            "GraphTech specializes exclusively in Computer Science and IT technical diagrams "
            "(Cloud VPC, Microservices, ERD, API Sequence, Kubernetes, State Machines). "
            "Requests for civil architectural blueprints, house floor plans, plumbing, or structural engineering are out of scope."
        ),
    },
    {
        "domain": "Mechanical Engineering",
        "patterns": [
            r"\b(gear\s*(box|assembly|train)|mechanical\s*cad|machine\s*part)\b",
            r"\b(piston|crankshaft|combustion\s*engine|turbine\s*blade)\b",
            r"\b(hydraulic\s*cylinder|pneumatic\s*circuit|lathe\s*machine)\b",
            r"\b(mechanical\s*blueprint|torque\s*transmission)\b",
        ],
        "reason": (
            "GraphTech specializes exclusively in Computer Science and IT technical diagrams "
            "(Cloud VPC, Microservices, ERD, API Sequence, Kubernetes, State Machines). "
            "Requests for mechanical machine parts, CAD assemblies, gearboxes, or engines are out of scope."
        ),
    },
    {
        "domain": "Electrical Circuit Board Schematics",
        "patterns": [
            r"\b(pcb\s*layout|breadboard\s*(circuit|wiring))\b",
            r"\b(resistor|transistor|capacitor)\s+and\s+(resistor|transistor|capacitor|inductor)\b",
            r"\b(analog\s*circuit\s*schematic|soldering\s*diagram)\b",
        ],
        "reason": (
            "GraphTech specializes in software systems and cloud/IT architecture. "
            "Physical analog PCB circuit schematics and hardware breadboard wiring diagrams are out of scope."
        ),
    },
    {
        "domain": "Non-Technical / Creative Artwork",
        "patterns": [
            r"\b(portrait\s*of|landscape\s*painting|anime\s*character|oil\s*painting)\b",
            r"\b(artistic\s*drawing\s*of|photorealistic\s*image\s*of)\b",
            r"\b(logo\s*design\s*for\s*my\s*brand|cartoon\s*illustration)\b",
        ],
        "reason": (
            "GraphTech is an AI technical diagram studio for software architecture and IT systems. "
            "Creative illustrations, portraits, and artistic artwork are out of scope."
        ),
    },
]


class ScopeGuard:
    """Evaluates whether user prompts fall strictly within Computer Science / IT technical domains."""

    def check_scope(self, prompt: str) -> ScopeCheckResult:
        normalized = prompt.strip().lower()

        # Test against out-of-scope domains
        for rule in OUT_OF_SCOPE_RULES:
            for pattern in rule["patterns"]:
                if re.search(pattern, normalized, re.IGNORECASE):
                    return ScopeCheckResult(
                        is_in_scope=False,
                        detected_domain=rule["domain"],
                        rejection_reason=rule["reason"],
                    )

        return ScopeCheckResult(is_in_scope=True)


scope_guard = ScopeGuard()
