"""
One-time script: converts ESCO CSV files → backend/skills_taxonomy.json
Run from the project root:  python backend/build_taxonomy_from_esco.py
"""
from __future__ import annotations

import csv
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ESCO_DIR = Path(__file__).parent.parent / "ESCO"
OUT_FILE = Path(__file__).parent / "skills_taxonomy.json"

# ---------------------------------------------------------------------------
# Occupation → role mapping
# ---------------------------------------------------------------------------
OCCUPATION_ROLES: dict[str, list[str]] = {
    "software developer":                  ["backend", "fullstack"],
    "ict application developer":           ["backend", "fullstack"],
    "ict system developer":                ["backend"],
    "software architect":                  ["backend", "fullstack", "cloud_devops"],
    "software analyst":                    ["backend"],
    "software tester":                     ["backend", "fullstack"],
    "database developer":                  ["backend"],
    "database administrator":             ["backend", "cloud_devops"],
    "database designer":                   ["backend"],
    "database integrator":                 ["backend"],
    "embedded systems software developer": ["backend"],
    "web developer":                       ["fullstack"],
    "user interface developer":            ["fullstack"],
    "mobile application developer":        ["fullstack"],
    "digital games developer":             ["fullstack"],
    "cloud devops engineer":               ["cloud_devops"],
    "cloud architect":                     ["cloud_devops"],
    "cloud engineer":                      ["cloud_devops"],
    "cloud software developer":            ["cloud_devops"],
    "data engineer":                       ["cloud_devops", "backend"],
    "blockchain developer":                ["cloud_devops", "backend"],
}

# ---------------------------------------------------------------------------
# Keyword → category mapping (first match wins)
# ---------------------------------------------------------------------------
CATEGORY_RULES: list[tuple[list[str], str]] = [
    (["python", "java", "javascript", "typescript", "golang", " go,", "rust",
      "c#", ".net", "c++", "ruby", "php", "swift", "kotlin", "scala", "haskell",
      "perl", "matlab", "cobol", "fortran", "assembly", "lua", "dart", "abap",
      "apex ", "groovy", "elixir", "clojure", "erlang", "f#", "vba", "apl",
      "programming language", "object-oriented", "functional programming",
      "scripting language"],
     "Programming Languages"),

    (["react", "angular", "vue", "svelte", "html", "css", "sass", "webpack",
      "frontend", "front-end", "front end", "browser", "dom ", "ui framework",
      "user interface design", "responsive design", "web design", "accessibility",
      "visual design", "spa ", "pwa", "ajax", "adobe illustrator", "adobe photoshop",
      "photoshop", "illustrator", "figma", "sketch ", "ux design", "wireframe",
      "usability", "application usability", "3d lighting", "3d texturing",
      "augmented reality", "virtual reality", "animation", "multimedia"],
     "Frontend Concepts"),

    (["sql", "postgresql", "mysql", "oracle", "mongodb", "redis", "elasticsearch",
      "cassandra", "dynamodb", "sqlite", "nosql", "database", "data model",
      "schema design", "query", "transaction", "orm ", "data store", "relational",
      "data warehouse", "data lake", "business intelligence", "bi tool"],
     "Databases"),

    (["aws", "azure", "google cloud", "gcp", "cloud architect", "cloud service",
      "cloud infrastructure", "cloud native", "cloud migration", "cloud security",
      "cloud deploy", "serverless", "lambda", "s3 ", "ec2", "cloud platform",
      "automate cloud", "cloud task", "cloud application"],
     "Cloud Platforms"),

    (["docker", "kubernetes", "k8s", "container", "helm", "terraform", "ansible",
      "puppet", "chef ", "jenkins", "ci/cd", "pipeline", "gitlab ci", "github action",
      "devops", "infrastructure as code", "iac", "deployment", "release management",
      "build automation", "continuous integration", "continuous delivery",
      "continuous deployment", "monitoring", "observability", "logging"],
     "DevOps & CI/CD"),

    (["linux", "unix", "bash", "shell script", "powershell", "operating system",
      "system administration", "networking", "tcp/ip", "dns ", "firewall",
      "load balanc", "nginx", "apache", "virtualisation", "virtualization",
      "hypervisor", "network protocol"],
     "Infrastructure & OS"),

    (["rest", "api design", "graphql", "grpc", "microservice", "event-driven",
      "message queue", "kafka", "rabbitmq", "websocket", "openapi", "swagger",
      "http ", "oauth", "jwt", "soap ", "xml ", "json ", "integration",
      "web service", "service-oriented"],
     "APIs & Integration"),

    (["machine learning", "deep learning", "neural network", "natural language",
      "tensorflow", "pytorch", "scikit", "pandas", "numpy", "data pipeline",
      "etl ", "spark", "hadoop", "analytics", "data science", "data engineer",
      "data mining", "predictive", "statistical", "big data"],
     "Data & ML"),

    (["blockchain", "distributed ledger", "smart contract", "decentralis",
      "decentraliz", "consensus", "cryptocurrency", "web3", "nft "],
     "Blockchain & Web3"),

    (["security", "encryption", "owasp", "penetration", "vulnerability",
      "cryptograph", "identity", "access control", "compliance", "gdpr",
      "risk", "threat", "attack vector", "audit technique", "cyber",
      "authentication", "authorisation", "authorization", "zero trust"],
     "Auth & Security"),

    (["agile", "scrum", "kanban", "jira", "confluence", "project management",
      "version control", "git ", "code review", "refactor", "design pattern",
      "software architecture", "system design", "software design", "software quality",
      "software development", "software testing", "test-driven", "debugging",
      "software specification", "requirements", "documentation", "uml",
      "software lifecycle", "ict system", "information system", "business process",
      "process model"],
     "Architecture & Patterns"),

    (["communicate", "collaborate", "present", "report", "stakeholder", "teamwork",
      "leadership", "mentor", "problem solv", "analytical", "creative",
      "company polic", "business relationship", "customer", "client"],
     "Professional Skills"),
]


def categorise(label: str) -> str:
    low = label.lower()
    for keywords, category in CATEGORY_RULES:
        if any(kw in low for kw in keywords):
            return category
    return "General ICT"


def make_aliases(label: str) -> list[str]:
    """Generate alias list from a skill label."""
    aliases = [label]
    low = label.lower()
    if low != label:
        aliases.append(low)

    # Add common abbreviations for well-known terms
    ABBREVS = {
        "javascript": ["js"],
        "typescript": ["ts"],
        "python": ["py"],
        "kubernetes": ["k8s"],
        "continuous integration": ["ci"],
        "continuous delivery": ["cd"],
        "infrastructure as code": ["iac"],
        "application programming interface": ["api"],
        "representational state transfer": ["rest"],
        "structured query language": ["sql"],
        "object-relational mapping": ["orm"],
        "machine learning": ["ml"],
        "artificial intelligence": ["ai"],
        "natural language processing": ["nlp"],
        "extract transform load": ["etl"],
        "command line interface": ["cli"],
    }
    for full, abbrs in ABBREVS.items():
        if full in low:
            aliases.extend(abbrs)

    return list(dict.fromkeys(aliases))  # deduplicate, preserve order


def skill_id(label: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", label.lower()).strip("_")


def main() -> None:
    # --- Load occupation→skill relations ---
    skill_data: dict[str, dict] = {}

    with open(ESCO_DIR / "occupationSkillRelations_uk.csv", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            occ = row["occupationLabel"].lower()
            if occ not in OCCUPATION_ROLES:
                continue
            uri = row["skillUri"]
            label = row["skillLabel"].strip()
            rel = row["relationType"]  # essential | optional

            if not label:
                continue

            if uri not in skill_data:
                skill_data[uri] = {
                    "uri": uri,
                    "label": label,
                    "roles": set(),
                    "essential": False,
                }
            skill_data[uri]["roles"].update(OCCUPATION_ROLES[occ])
            if rel == "essential":
                skill_data[uri]["essential"] = True

    # --- Build taxonomy entries ---
    seen_ids: dict[str, int] = {}
    skills: list[dict] = []

    for entry in skill_data.values():
        label = entry["label"]
        base_id = skill_id(label)

        # Deduplicate IDs
        if base_id in seen_ids:
            seen_ids[base_id] += 1
            sid = f"{base_id}_{seen_ids[base_id]}"
        else:
            seen_ids[base_id] = 0
            sid = base_id

        skills.append({
            "id": sid,
            "canonical_name": label,
            "aliases": make_aliases(label),
            "category": categorise(label),
            "roles": sorted(entry["roles"]),
            "level": "core" if entry["essential"] else "advanced",
        })

    # Sort by canonical name for readability
    skills.sort(key=lambda s: s["canonical_name"].lower())

    taxonomy = {
        "version": "2.0.0-esco",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "ESCO v1.2 (https://esco.ec.europa.eu)",
        "roles": {
            "backend": "Backend Engineer",
            "fullstack": "Fullstack Engineer",
            "cloud_devops": "Cloud/DevOps Engineer",
        },
        "skills": skills,
    }

    OUT_FILE.write_text(json.dumps(taxonomy, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Written {len(skills)} skills to {OUT_FILE} - build_taxonomy_from_esco.py:241")

    # Summary
    from collections import Counter
    cats = Counter(s["category"] for s in skills)
    print("\nCategory breakdown: - build_taxonomy_from_esco.py:246")
    for cat, count in cats.most_common():
        print(f"{cat:<35} {count} - build_taxonomy_from_esco.py:248")


if __name__ == "__main__":
    main()
