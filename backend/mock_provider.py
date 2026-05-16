"""Deterministic mock LLM provider used when no ``ANTHROPIC_API_KEY`` is set.

The mock returns schema-valid stub data for every pipeline step so the entire
frontend can be exercised end-to-end without a network round-trip or API key.
Output is seeded from input text via SHA-256, so the same resume produces the
same profile across runs — useful for demos and snapshot tests.

The single public entry point is :func:`mock_response`, dispatched from
:func:`llm.call_claude_structured` when ``settings.llm_provider == "mock"``.
"""

from __future__ import annotations

import hashlib
import random
import re
from typing import Type, TypeVar

from pydantic import BaseModel

from schemas.candidate import (
    CandidateBriefing,
    CandidateProfile,
    EducationEntry,
    FitmentAnalysis,
    MustHaveRating,
    NiceToHaveRating,
    PanelBriefing,
    RedFlagRating,
    Skills,
    WorkHistoryEntry,
)
from schemas.checklist import ComplianceCheck, EvaluationChecklist, SkillRequirement
from schemas.questions import InterviewQuestion, QuestionBank

__all__ = ["mock_response"]

T = TypeVar("T", bound=BaseModel)


# --- Lexicons used by the various mock generators -------------------------

_COMPANY_NAMES = [
    "Acme Corp", "Globex", "Initech", "Hooli", "Pied Piper",
    "Umbrella Systems", "Stark Industries",
]
_JOB_ROLES = [
    "Senior Engineer", "Staff Engineer", "Engineering Manager",
    "Tech Lead", "Principal Engineer",
]
_INDUSTRY_DOMAINS = [
    "FinTech", "E-commerce", "SaaS", "Healthcare", "AdTech", "Logistics",
]
_TECH_SKILLS = [
    "Python", "Go", "Distributed systems", "Kubernetes", "AWS",
    "PostgreSQL", "Kafka", "Redis", "Docker",
]
_FIRST_NAMES = [
    "Alex", "Jordan", "Priya", "Sam", "Taylor",
    "Riya", "Aarav", "Maya", "Devon", "Kai",
]
_LAST_NAMES = [
    "Patel", "Nguyen", "Garcia", "Smith", "Iyer",
    "Khan", "Brown", "Singh", "Cole", "Adams",
]


# --- Checklist derivation lexicons ----------------------------------------

# Keyword -> (must-have skill name, description)
_TECH_TO_MUST_HAVE: dict[str, tuple[str, str]] = {
    "python": ("Python", "5+ years production Python experience"),
    "java": ("Java", "5+ years production Java/JVM experience"),
    " go ": ("Go", "Production Go experience at scale"),
    "golang": ("Go", "Production Go experience at scale"),
    "node": ("Node.js", "Production Node.js / TypeScript backend experience"),
    "typescript": ("TypeScript", "Production TypeScript experience"),
    "react": ("React", "Production React experience building user-facing apps"),
    "fastapi": ("FastAPI", "Production FastAPI experience"),
    "django": ("Django", "Production Django experience"),
    "spring": ("Spring Boot", "Production Spring Boot / Java microservices experience"),
    "rust": ("Rust", "Production Rust experience"),
}

# Keyword -> (nice-to-have skill name, description)
_TECH_TO_NICE_TO_HAVE: dict[str, tuple[str, str]] = {
    "kafka": ("Kafka", "Event-streaming pipeline experience in production"),
    "kubernetes": ("Kubernetes", "Production Kubernetes operations"),
    "k8s": ("Kubernetes", "Production Kubernetes operations"),
    "redis": ("Redis", "Caching / pub-sub with Redis at scale"),
    "postgres": ("PostgreSQL", "PostgreSQL at scale, including query tuning"),
    "mysql": ("MySQL", "Production MySQL experience"),
    "mongodb": ("MongoDB", "Production MongoDB experience"),
    "aws": ("AWS", "Hands-on AWS production experience"),
    "gcp": ("GCP", "Google Cloud production experience"),
    "azure": ("Azure", "Microsoft Azure production experience"),
    "terraform": ("Terraform", "Infrastructure-as-code with Terraform"),
    "graphql": ("GraphQL", "Production GraphQL schema design"),
}

# Domain keyword -> (display name, description, is_regulated)
_DOMAIN_KEYWORDS: dict[str, tuple[str, str, bool]] = {
    "payment": ("Payments / FinTech domain", "Direct experience with payment rails, reconciliation, or ledgers", True),
    "fintech": ("FinTech domain", "Direct experience with financial systems and regulated data", True),
    "healthcare": ("Healthcare domain", "Experience with HIPAA-regulated systems", True),
    "ecommerce": ("E-commerce domain", "Production experience with e-commerce platforms", False),
    "saas": ("SaaS / multi-tenant", "Multi-tenant SaaS platform experience", False),
    "adtech": ("AdTech", "High-throughput ad serving or bidding systems", False),
}

# Seniority keyword -> minimum years of experience
_SENIORITY_MIN_YEARS: list[tuple[str, int]] = [
    ("principal", 10),
    ("staff", 8),
    ("architect", 8),
    ("lead engineer", 7),
    ("tech lead", 7),
    ("senior", 6),
    ("mid-level", 3),
    ("junior", 1),
    ("intern", 0),
]


# --- Question bank templates ----------------------------------------------

_QUESTION_TEMPLATES: dict[str, list[tuple[str, str]]] = {
    "Technical Depth": [
        (
            "Walk me through the most complex {skill} system you have built and why the design held up.",
            "Validates depth of declared {skill} experience.",
        ),
        (
            "How would you debug a sudden latency regression in a {domain} service?",
            "Probes incident-response habits and instrumentation.",
        ),
        (
            "Describe a tradeoff you made when choosing between two technologies for a recent project.",
            "Validates decision quality under real constraints.",
        ),
    ],
    "Behavioural Scenarios": [
        (
            "Tell me about a time you disagreed with a senior stakeholder on a technical decision. (STAR)",
            "Surfaces influence and handling of senior pushback.",
        ),
        (
            "Describe a time you led a project that missed its deadline. What did you do? (STAR)",
            "Tests accountability and recovery.",
        ),
        (
            "Walk me through a time you mentored someone struggling with their work. (STAR)",
            "People-development signal.",
        ),
    ],
    "Gap Probing": [
        (
            "In your role at {company}, what specifically did you own end-to-end vs. contribute to?",
            "Address responsibility ambiguity from resume.",
        ),
        (
            "Can you walk me through the transition from {role_a} to {role_b}?",
            "Surfaces unexplained transitions or short tenures.",
        ),
        (
            "Your fitment shows '{skill_gap}' as partially met. Give a concrete example using it.",
            "Probes partially-met requirement.",
        ),
    ],
    "Situational": [
        (
            "Imagine our team needs to scale {domain} throughput 10x in 6 months. How would you approach it?",
            "Tests scaling and prioritisation thinking.",
        ),
        (
            "If you joined and inherited a service with no tests, what would you do in the first 90 days?",
            "Tests pragmatism and incremental delivery.",
        ),
        (
            "How would you decide whether to rewrite vs. refactor a legacy service?",
            "Tests judgment on risk vs. velocity.",
        ),
    ],
}

_EXPECTED_SIGNAL_POOL = [
    "concrete examples", "ownership", "tradeoffs", "metrics", "scale",
    "user impact", "team dynamics", "failure recovery", "stakeholder framing",
]


# --- Public entry point ---------------------------------------------------

def mock_response(step: str, schema: Type[T], context: dict) -> T:
    """Dispatch to the per-step mock generator. ``schema`` is unused but kept
    for signature parity with the real :func:`call_claude_structured`."""
    if step == "derive_checklist":
        return _mock_derive_checklist(context.get("role_description", ""))
    if step == "step2_profile":
        return _mock_profile(context.get("resume_text", ""))
    if step == "step3_fitment":
        return _mock_fitment(context["profile"], context["checklist"])
    if step == "step4_questions":
        return _mock_question_bank(
            context["profile"],
            context["fitment"],
            context["checklist"],
            context.get("role_description", ""),
        )
    if step == "step6_briefing":
        return _mock_briefing(
            context["profiles"],
            context["fitments"],
            context["checklist"],
        )
    raise NotImplementedError(f"Mock response not implemented for step: {step}")


# --- Helpers --------------------------------------------------------------

def _seeded_rng(seed_text: str) -> random.Random:
    """Return a ``random.Random`` seeded deterministically from ``seed_text``."""
    digest = hashlib.sha256(seed_text.encode("utf-8")).hexdigest()
    return random.Random(int(digest[:16], 16))


def _extract_candidate_name(resume_text: str, fallback_seed: str) -> str:
    """Heuristically extract the candidate name from resume text.

    Looks for a 2–5 word line of letters near the top of the document.
    Falls back to a deterministic first+last pick from the seeded lexicon.
    """
    non_name_headers = {"RESUME", "CV", "CURRICULUM VITAE", "PROFILE"}
    non_empty_lines = [ln.strip() for ln in resume_text.splitlines() if ln.strip()]
    for line in non_empty_lines[:6]:
        candidate = re.sub(r"[^A-Za-z .'-]", "", line).strip()
        if (
            candidate
            and candidate.upper() not in non_name_headers
            and 2 <= len(candidate.split()) <= 5
            and len(candidate) <= 60
        ):
            return candidate.title()

    rng = _seeded_rng(fallback_seed)
    return f"{rng.choice(_FIRST_NAMES)} {rng.choice(_LAST_NAMES)}"


# --- Step 2: candidate profile -------------------------------------------

def _mock_profile(resume_text: str) -> CandidateProfile:
    rng = _seeded_rng(resume_text or "fallback")
    name = _extract_candidate_name(resume_text or "", fallback_seed=str(rng.random()))

    email_match = re.search(r"[\w.+-]+@[\w.-]+\.\w+", resume_text or "")
    email = email_match.group(0) if email_match else f"{name.lower().replace(' ', '.')}@example.com"

    phone_match = re.search(r"\+?\d[\d\-\s().]{7,}\d", resume_text or "")
    phone = phone_match.group(0).strip() if phone_match else None

    total_years = round(rng.uniform(4.0, 12.0), 1)
    work_history = _generate_work_history(rng)
    technical_skills = rng.sample(_TECH_SKILLS, k=rng.randint(4, 6))
    domains = rng.sample(_INDUSTRY_DOMAINS, k=rng.randint(1, 3))

    return CandidateProfile(
        full_name=name,
        email=email,
        phone=phone,
        total_years_experience=total_years,
        work_history=work_history,
        skills=Skills(technical=technical_skills, certifications=[]),
        education=[
            EducationEntry(degree="B.Tech Computer Science", institution="State University", year=2014),
        ],
        industry_domains=domains,
        career_progression=rng.choice(["growth", "growth", "lateral", "mixed"]),
        resume_flags=[],
    )


def _generate_work_history(rng: random.Random) -> list[WorkHistoryEntry]:
    """Generate 2–3 plausible work history entries."""
    entries: list[WorkHistoryEntry] = []
    n_jobs = rng.randint(2, 3)
    start_year = 2018
    for i in range(n_jobs):
        end_date = "Present" if i == n_jobs - 1 else f"{start_year + 2}-12"
        entries.append(
            WorkHistoryEntry(
                company=rng.choice(_COMPANY_NAMES),
                role=rng.choice(_JOB_ROLES),
                start_date=f"{start_year}-01",
                end_date=end_date,
                tenure_months=rng.randint(18, 48),
                responsibilities=[
                    "Owned production services end-to-end",
                    "Mentored 2 junior engineers",
                    "Drove design reviews for new features",
                ],
                achievements=[
                    f"Cut latency by {rng.randint(20, 60)}% on the "
                    f"{rng.choice(['payments', 'auth', 'search'])} service",
                ],
            )
        )
        start_year += rng.randint(2, 3)
    return entries


# --- Step 3: fitment ------------------------------------------------------

def _mock_fitment(
    profile: CandidateProfile,
    checklist: EvaluationChecklist,
) -> FitmentAnalysis:
    rng = _seeded_rng(profile.full_name + "|" + checklist.role_title)
    must_have_pool = ["Meets", "Meets", "Meets", "Partially Meets", "Does Not Meet"]
    nice_to_have_pool = ["Present", "Present", "Absent"]
    red_flag_pool = ["None", "None", "None", "Minor"]

    must_haves = []
    for requirement in checklist.must_have_skills:
        rating = rng.choice(must_have_pool)
        if requirement.name in profile.skills.technical:
            rating = "Meets"
        must_haves.append(
            MustHaveRating(
                skill=requirement.name,
                rating=rating,
                justification=(
                    f"{profile.full_name} has ~{profile.total_years_experience} yrs total experience; "
                    f"{requirement.name} appears "
                    f"{'in declared skills' if rating == 'Meets' else 'with limited evidence'}."
                ),
            )
        )

    nice_to_haves = []
    for requirement in checklist.nice_to_have_skills:
        rating = rng.choice(nice_to_have_pool)
        if requirement.name in profile.skills.technical:
            rating = "Present"
        nice_to_haves.append(
            NiceToHaveRating(
                skill=requirement.name,
                rating=rating,
                justification="Mentioned in resume." if rating == "Present" else "Not mentioned.",
            )
        )

    red_flags = [
        RedFlagRating(
            indicator=indicator,
            rating=rng.choice(red_flag_pool),
            justification="Mock heuristic; verify against resume manually.",
        )
        for indicator in checklist.red_flag_indicators
    ]

    return FitmentAnalysis(
        candidate_name=profile.full_name,
        must_haves=must_haves,
        nice_to_haves=nice_to_haves,
        red_flags=red_flags,
        overall_summary=(
            f"{profile.full_name} brings {profile.total_years_experience} yrs experience "
            f"across {', '.join(profile.industry_domains) or 'multiple domains'}. "
            "Mock-mode analysis — illustrative only."
        ),
    )


# --- Step 4: question bank ------------------------------------------------

def _mock_question_bank(
    profile: CandidateProfile,
    fitment: FitmentAnalysis,
    checklist: EvaluationChecklist,
    role_description: str,  # noqa: ARG001 — kept for signature parity
) -> QuestionBank:
    rng = _seeded_rng(profile.full_name + "|questions")

    must_skill = (
        checklist.must_have_skills[0].name
        if checklist.must_have_skills
        else "the core technology"
    )
    domain = profile.industry_domains[0] if profile.industry_domains else "your domain"
    company = (
        profile.work_history[0].company
        if profile.work_history
        else "your most recent company"
    )
    role_a = profile.work_history[0].role if profile.work_history else "your prior role"
    role_b = (
        profile.work_history[1].role
        if len(profile.work_history) > 1
        else "your current role"
    )
    skill_gap = next(
        (mh.skill for mh in fitment.must_haves if mh.rating != "Meets"),
        must_skill,
    )

    questions: list[InterviewQuestion] = []
    for category, templates in _QUESTION_TEMPLATES.items():
        for question_template, rationale_template in templates:
            questions.append(
                InterviewQuestion(
                    category=category,
                    question=question_template.format(
                        skill=must_skill, domain=domain, company=company,
                        role_a=role_a, role_b=role_b, skill_gap=skill_gap,
                    ),
                    rationale=rationale_template.format(skill=must_skill, domain=domain),
                    expected_signals=rng.sample(_EXPECTED_SIGNAL_POOL, k=3),
                )
            )

    return QuestionBank(
        candidate_name=profile.full_name,
        role_title=checklist.role_title,
        questions=questions,
    )


# --- Step 6: panel briefing ----------------------------------------------

def _mock_briefing(
    profiles: list[CandidateProfile],
    fitments: list[FitmentAnalysis],
    checklist: EvaluationChecklist,
) -> PanelBriefing:
    per_candidate: list[CandidateBriefing] = []
    for profile, fitment in zip(profiles, fitments):
        strengths = [mh.skill for mh in fitment.must_haves if mh.rating == "Meets"][:3]
        gaps = [mh.skill for mh in fitment.must_haves if mh.rating != "Meets"][:3]
        per_candidate.append(
            CandidateBriefing(
                candidate_name=profile.full_name,
                strengths=(
                    [f"{s} — meets bar" for s in strengths]
                    or ["Solid baseline experience"]
                ),
                gaps=(
                    [f"{g} — probe in interview" for g in gaps]
                    or ["No major gaps surfaced"]
                ),
            )
        )

    focus_areas: list[str] = []
    if checklist.must_have_skills:
        focus_areas.append(
            f"Probe depth on {checklist.must_have_skills[0].name} across the slate."
        )
    focus_areas.append("Cross-check ownership claims with concrete examples in past roles.")
    if checklist.compliance_checks:
        required_names = ", ".join(c.name for c in checklist.compliance_checks if c.required)
        focus_areas.append(
            f"Confirm compliance items ({required_names}) before the next round."
        )

    return PanelBriefing(
        headline=(
            f"Reviewed {len(profiles)} candidate(s) for {checklist.role_title}. "
            "Mock mode — outputs are illustrative; not real LLM analysis."
        ),
        per_candidate=per_candidate,
        panel_focus_areas=focus_areas,
    )


# --- Checklist derivation -------------------------------------------------

def _extract_role_title(text: str) -> str:
    """Heuristically pull a role title from a free-text role description."""
    patterns = [
        r"hiring\s+(?:a|an|the)\s+([A-Za-z][\w\s\-/]+?)(?:\s+to\s|\s+who\s|\.|,|\n)",
        r"looking\s+for\s+(?:a|an|the)\s+([A-Za-z][\w\s\-/]+?)(?:\s+to\s|\s+who\s|\.|,|\n)",
        r"seeking\s+(?:a|an|the)\s+([A-Za-z][\w\s\-/]+?)(?:\s+to\s|\s+who\s|\.|,|\n)",
        r"role:\s*([A-Za-z][\w\s\-/]+?)(?:\.|,|\n)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            title = match.group(1).strip().rstrip(".,;:")
            if 5 <= len(title) <= 80:
                return title.title() if title.islower() else title

    first_line = (text.strip().split("\n", 1)[0] if text.strip() else "").strip()
    if 5 <= len(first_line) <= 80 and len(first_line.split()) <= 8:
        return first_line
    return "Engineering Role"


def _detect_min_years(text_lower: str) -> int:
    """Detect minimum years of experience from seniority words and "N+ years"."""
    min_years = 3
    for keyword, years in _SENIORITY_MIN_YEARS:
        if keyword in text_lower:
            min_years = years
            break

    explicit = re.search(r"(\d+)\+?\s*(?:years?|yrs)", text_lower)
    if explicit:
        try:
            min_years = max(min_years, int(explicit.group(1)))
        except ValueError:
            pass
    return min_years


def _mock_derive_checklist(role_description: str) -> EvaluationChecklist:
    text = role_description or "Senior Engineer role"
    text_lower = " " + text.lower() + " "

    must_have_names: set[str] = set()
    must_haves: list[dict] = []
    nice_to_have_names: set[str] = set()
    nice_to_haves: list[dict] = []

    for keyword, (name, description) in _TECH_TO_MUST_HAVE.items():
        if keyword in text_lower and name not in must_have_names:
            must_haves.append({"name": name, "description": description})
            must_have_names.add(name)

    if any(k in text_lower for k in ["microservice", "distributed", "monolith", "service-oriented"]):
        if "Distributed systems" not in must_have_names:
            must_haves.append({
                "name": "Distributed systems",
                "description": "Designed or operated microservices / service-oriented systems at scale",
            })
            must_have_names.add("Distributed systems")

    if any(k in text_lower for k in [" api", "rest ", "grpc", "graphql"]):
        if "API design" not in must_have_names:
            must_haves.append({
                "name": "API design",
                "description": "Has designed and shipped REST or gRPC APIs serving production traffic",
            })
            must_have_names.add("API design")

    if any(k in text_lower for k in ["mentor", "lead ", "manage", "junior", "team lead", "tech lead", "guide engineers"]):
        if "Technical mentorship" not in must_have_names:
            must_haves.append({
                "name": "Technical mentorship",
                "description": "Has directly mentored or led 2+ engineers; can describe their growth concretely",
            })
            must_have_names.add("Technical mentorship")

    must_haves = must_haves[:6] or [
        {"name": "Software engineering", "description": "Strong production engineering background"},
        {"name": "System design", "description": "Has designed systems serving production traffic"},
    ]

    for keyword, (name, description) in _TECH_TO_NICE_TO_HAVE.items():
        if keyword in text_lower and name not in nice_to_have_names:
            nice_to_haves.append({"name": name, "description": description})
            nice_to_have_names.add(name)

    is_regulated = False
    for keyword, (name, description, regulated) in _DOMAIN_KEYWORDS.items():
        if keyword in text_lower:
            nice_to_haves.append({"name": name, "description": description})
            if regulated:
                is_regulated = True
            break

    if any(k in text_lower for k in ["scale ", "scaling", "throughput", "10x", "8x", "5x", "high-traffic", "high traffic"]):
        nice_to_haves.append({
            "name": "High-scale systems",
            "description": "Has handled significant traffic growth or capacity planning in production",
        })

    if any(k in text_lower for k in ["sre", "observability", "on-call", "on call", "slo", "reliability", "incident"]):
        nice_to_haves.append({
            "name": "SRE / observability",
            "description": "Has owned SLOs, error budgets, on-call rotations, or partnered closely with platform teams",
        })

    nice_to_haves = nice_to_haves[:5]

    min_years = _detect_min_years(text_lower)

    red_flags = [
        "Unexplained gap > 12 months",
        "Title/responsibility mismatch (claimed seniority not backed by resume scope)",
    ]
    if min_years >= 6:
        red_flags.insert(0, "Job-hopping with <18 month tenures across senior roles")
    else:
        red_flags.insert(0, "Job-hopping with <12 month tenures")
    if any(k in text_lower for k in ["mentor", "lead ", "team lead", "junior"]):
        red_flags.append(
            "Pure IC profile with no evidence of mentoring, design reviews, or cross-team work"
        )
    if is_regulated:
        red_flags.append("No production exposure to regulated / sensitive-data domains")

    compliance = [
        {
            "name": "Background verification (BGV)", "required": True,
            "description": "BGV consent signed and clearance received",
        },
        {
            "name": "Right to work", "required": True,
            "description": "Work authorisation confirmed for the hiring location",
        },
        {
            "name": "Video consent", "required": True,
            "description": "Recording consent form signed before the interview begins",
        },
    ]
    if is_regulated:
        compliance.append({
            "name": "Regulatory acknowledgment",
            "required": True,
            "description": "Acknowledgment of sector compliance obligations "
                           "(data handling, AML/HIPAA awareness)",
        })

    return EvaluationChecklist(
        role_title=_extract_role_title(text),
        must_have_skills=[SkillRequirement(**s) for s in must_haves],
        nice_to_have_skills=[SkillRequirement(**s) for s in nice_to_haves],
        red_flag_indicators=red_flags,
        min_years_experience=min_years,
        compliance_checks=[ComplianceCheck(**c) for c in compliance],
    )
