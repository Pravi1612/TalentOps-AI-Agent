import hashlib
import random
import re
from typing import List, Type, TypeVar

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

T = TypeVar("T", bound=BaseModel)

_COMPANIES = ["Acme Corp", "Globex", "Initech", "Hooli", "Pied Piper", "Umbrella Systems", "Stark Industries"]
_ROLES = ["Senior Engineer", "Staff Engineer", "Engineering Manager", "Tech Lead", "Principal Engineer"]
_DOMAINS = ["FinTech", "E-commerce", "SaaS", "Healthcare", "AdTech", "Logistics"]
_TECH = ["Python", "Go", "Distributed systems", "Kubernetes", "AWS", "PostgreSQL", "Kafka", "Redis", "Docker"]


def _rng(seed_text: str) -> random.Random:
    h = hashlib.sha256(seed_text.encode("utf-8")).hexdigest()
    return random.Random(int(h[:16], 16))


def _extract_name(resume_text: str, fallback_seed: str) -> str:
    lines = [ln.strip() for ln in resume_text.splitlines() if ln.strip()]
    skip = {"RESUME", "CV", "CURRICULUM VITAE", "PROFILE"}
    for line in lines[:6]:
        candidate = re.sub(r"[^A-Za-z .'-]", "", line).strip()
        if (
            candidate
            and candidate.upper() not in skip
            and 2 <= len(candidate.split()) <= 5
            and len(candidate) <= 60
        ):
            return candidate.title()
    rng = _rng(fallback_seed)
    first = rng.choice(["Alex", "Jordan", "Priya", "Sam", "Taylor", "Riya", "Aarav", "Maya", "Devon", "Kai"])
    last = rng.choice(["Patel", "Nguyen", "Garcia", "Smith", "Iyer", "Khan", "Brown", "Singh", "Cole", "Adams"])
    return f"{first} {last}"


def _mock_profile(resume_text: str) -> CandidateProfile:
    rng = _rng(resume_text or "fallback")
    name = _extract_name(resume_text or "", fallback_seed=str(rng.random()))

    email_match = re.search(r"[\w.+-]+@[\w.-]+\.\w+", resume_text or "")
    email = email_match.group(0) if email_match else f"{name.lower().replace(' ', '.')}@example.com"

    phone_match = re.search(r"\+?\d[\d\-\s().]{7,}\d", resume_text or "")
    phone = phone_match.group(0).strip() if phone_match else None

    years = round(rng.uniform(4.0, 12.0), 1)

    n_jobs = rng.randint(2, 3)
    work: List[WorkHistoryEntry] = []
    start_year = 2018
    for i in range(n_jobs):
        end = "Present" if i == n_jobs - 1 else f"{start_year + 2}-12"
        work.append(
            WorkHistoryEntry(
                company=rng.choice(_COMPANIES),
                role=rng.choice(_ROLES),
                start_date=f"{start_year}-01",
                end_date=end,
                tenure_months=rng.randint(18, 48),
                responsibilities=[
                    "Owned production services end-to-end",
                    "Mentored 2 junior engineers",
                    "Drove design reviews for new features",
                ],
                achievements=[
                    f"Cut latency by {rng.randint(20, 60)}% on the {rng.choice(['payments', 'auth', 'search'])} service",
                ],
            )
        )
        start_year += rng.randint(2, 3)

    technical = rng.sample(_TECH, k=rng.randint(4, 6))
    domains = rng.sample(_DOMAINS, k=rng.randint(1, 3))

    return CandidateProfile(
        full_name=name,
        email=email,
        phone=phone,
        total_years_experience=years,
        work_history=work,
        skills=Skills(technical=technical, certifications=[]),
        education=[EducationEntry(degree="B.Tech Computer Science", institution="State University", year=2014)],
        industry_domains=domains,
        career_progression=rng.choice(["growth", "growth", "lateral", "mixed"]),
        resume_flags=[],
    )


def _mock_fitment(profile: CandidateProfile, checklist: EvaluationChecklist) -> FitmentAnalysis:
    rng = _rng(profile.full_name + "|" + checklist.role_title)
    pool_must = ["Meets", "Meets", "Meets", "Partially Meets", "Does Not Meet"]
    pool_nice = ["Present", "Present", "Absent"]
    pool_flag = ["None", "None", "None", "Minor"]

    must_haves = []
    for sr in checklist.must_have_skills:
        rating = rng.choice(pool_must)
        if sr.name in profile.skills.technical:
            rating = "Meets"
        must_haves.append(
            MustHaveRating(
                skill=sr.name,
                rating=rating,
                justification=(
                    f"{profile.full_name} has ~{profile.total_years_experience} yrs total experience; "
                    f"{sr.name} appears {'in declared skills' if rating == 'Meets' else 'with limited evidence'}."
                ),
            )
        )

    nice_to_haves = []
    for sr in checklist.nice_to_have_skills:
        rating = rng.choice(pool_nice)
        if sr.name in profile.skills.technical:
            rating = "Present"
        nice_to_haves.append(
            NiceToHaveRating(
                skill=sr.name,
                rating=rating,
                justification="Mentioned in resume." if rating == "Present" else "Not mentioned.",
            )
        )

    red_flags = [
        RedFlagRating(
            indicator=ind,
            rating=rng.choice(pool_flag),
            justification="Mock heuristic; verify against resume manually.",
        )
        for ind in checklist.red_flag_indicators
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


_Q_TEMPLATES = {
    "Technical Depth": [
        ("Walk me through the most complex {skill} system you have built and why the design held up.",
         "Validates depth of declared {skill} experience."),
        ("How would you debug a sudden latency regression in a {domain} service?",
         "Probes incident-response habits and instrumentation."),
        ("Describe a tradeoff you made when choosing between two technologies for a recent project.",
         "Validates decision quality under real constraints."),
    ],
    "Behavioural Scenarios": [
        ("Tell me about a time you disagreed with a senior stakeholder on a technical decision. (STAR)",
         "Surfaces influence and handling of senior pushback."),
        ("Describe a time you led a project that missed its deadline. What did you do? (STAR)",
         "Tests accountability and recovery."),
        ("Walk me through a time you mentored someone struggling with their work. (STAR)",
         "People-development signal."),
    ],
    "Gap Probing": [
        ("In your role at {company}, what specifically did you own end-to-end vs. contribute to?",
         "Address responsibility ambiguity from resume."),
        ("Can you walk me through the transition from {role_a} to {role_b}?",
         "Surfaces unexplained transitions or short tenures."),
        ("Your fitment shows '{skill_gap}' as partially met. Give a concrete example using it.",
         "Probes partially-met requirement."),
    ],
    "Situational": [
        ("Imagine our team needs to scale {domain} throughput 10x in 6 months. How would you approach it?",
         "Tests scaling and prioritisation thinking."),
        ("If you joined and inherited a service with no tests, what would you do in the first 90 days?",
         "Tests pragmatism and incremental delivery."),
        ("How would you decide whether to rewrite vs. refactor a legacy service?",
         "Tests judgment on risk vs. velocity."),
    ],
}


def _mock_question_bank(
    profile: CandidateProfile,
    fitment: FitmentAnalysis,
    checklist: EvaluationChecklist,
    role_description: str,
) -> QuestionBank:
    rng = _rng(profile.full_name + "|questions")
    must_skill = checklist.must_have_skills[0].name if checklist.must_have_skills else "the core technology"
    domain = profile.industry_domains[0] if profile.industry_domains else "your domain"
    company = profile.work_history[0].company if profile.work_history else "your most recent company"
    role_a = profile.work_history[0].role if profile.work_history else "your prior role"
    role_b = profile.work_history[1].role if len(profile.work_history) > 1 else "your current role"
    skill_gap = next(
        (mh.skill for mh in fitment.must_haves if mh.rating != "Meets"),
        must_skill,
    )

    signals_pool = [
        "concrete examples", "ownership", "tradeoffs", "metrics", "scale",
        "user impact", "team dynamics", "failure recovery", "stakeholder framing",
    ]

    questions: List[InterviewQuestion] = []
    for category, templates in _Q_TEMPLATES.items():
        for q_tpl, r_tpl in templates:
            q = q_tpl.format(
                skill=must_skill, domain=domain, company=company,
                role_a=role_a, role_b=role_b, skill_gap=skill_gap,
            )
            r = r_tpl.format(skill=must_skill, domain=domain)
            questions.append(
                InterviewQuestion(
                    category=category,
                    question=q,
                    rationale=r,
                    expected_signals=rng.sample(signals_pool, k=3),
                )
            )

    return QuestionBank(
        candidate_name=profile.full_name,
        role_title=checklist.role_title,
        questions=questions,
    )


def _mock_briefing(
    profiles: List[CandidateProfile],
    fitments: List[FitmentAnalysis],
    checklist: EvaluationChecklist,
) -> PanelBriefing:
    per_candidate: List[CandidateBriefing] = []
    for p, f in zip(profiles, fitments):
        strengths = [mh.skill for mh in f.must_haves if mh.rating == "Meets"][:3]
        gaps = [mh.skill for mh in f.must_haves if mh.rating != "Meets"][:3]
        per_candidate.append(
            CandidateBriefing(
                candidate_name=p.full_name,
                strengths=[f"{s} — meets bar" for s in strengths] or ["Solid baseline experience"],
                gaps=[f"{g} — probe in interview" for g in gaps] or ["No major gaps surfaced"],
            )
        )

    focus: List[str] = []
    if checklist.must_have_skills:
        focus.append(f"Probe depth on {checklist.must_have_skills[0].name} across the slate.")
    focus.append("Cross-check ownership claims with concrete examples in past roles.")
    if checklist.compliance_checks:
        focus.append(
            "Confirm compliance items ("
            + ", ".join(c.name for c in checklist.compliance_checks if c.required)
            + ") before the next round."
        )

    return PanelBriefing(
        headline=(
            f"Reviewed {len(profiles)} candidate(s) for {checklist.role_title}. "
            "Mock mode — outputs are illustrative; not real LLM analysis."
        ),
        per_candidate=per_candidate,
        panel_focus_areas=focus,
    )


_TECH_MUST = {
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

_TECH_NICE = {
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

_DOMAIN_KEYWORDS = {
    "payment": ("Payments / FinTech domain", "Direct experience with payment rails, reconciliation, or ledgers", True),
    "fintech": ("FinTech domain", "Direct experience with financial systems and regulated data", True),
    "healthcare": ("Healthcare domain", "Experience with HIPAA-regulated systems", True),
    "ecommerce": ("E-commerce domain", "Production experience with e-commerce platforms"),
    "saas": ("SaaS / multi-tenant", "Multi-tenant SaaS platform experience"),
    "adtech": ("AdTech", "High-throughput ad serving or bidding systems"),
}

_SENIORITY = [
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


def _extract_role_title(text: str) -> str:
    patterns = [
        r"hiring\s+(?:a|an|the)\s+([A-Za-z][\w\s\-/]+?)(?:\s+to\s|\s+who\s|\.|,|\n)",
        r"looking\s+for\s+(?:a|an|the)\s+([A-Za-z][\w\s\-/]+?)(?:\s+to\s|\s+who\s|\.|,|\n)",
        r"seeking\s+(?:a|an|the)\s+([A-Za-z][\w\s\-/]+?)(?:\s+to\s|\s+who\s|\.|,|\n)",
        r"role:\s*([A-Za-z][\w\s\-/]+?)(?:\.|,|\n)",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            title = m.group(1).strip().rstrip(".,;:")
            if 5 <= len(title) <= 80:
                return title.title() if title.islower() else title
    first_line = (text.strip().split("\n", 1)[0] if text.strip() else "").strip()
    if 5 <= len(first_line) <= 80 and len(first_line.split()) <= 8:
        return first_line
    return "Engineering Role"


def _mock_derive_checklist(role_description: str) -> EvaluationChecklist:
    text = role_description or "Senior Engineer role"
    text_l = " " + text.lower() + " "

    role_title = _extract_role_title(text)

    must_haves: List[dict] = []
    nice_to_haves: List[dict] = []
    detected: set[str] = set()

    for kw, (name, desc) in _TECH_MUST.items():
        if kw in text_l and name not in detected:
            must_haves.append({"name": name, "description": desc})
            detected.add(name)

    if any(x in text_l for x in ["microservice", "distributed", "monolith", "service-oriented"]):
        if "Distributed systems" not in detected:
            must_haves.append({
                "name": "Distributed systems",
                "description": "Designed or operated microservices / service-oriented systems at scale",
            })
            detected.add("Distributed systems")

    if any(x in text_l for x in [" api", "rest ", "grpc", "graphql"]):
        if "API design" not in detected:
            must_haves.append({
                "name": "API design",
                "description": "Has designed and shipped REST or gRPC APIs serving production traffic",
            })
            detected.add("API design")

    if any(x in text_l for x in ["mentor", "lead ", "manage", "junior", "team lead", "tech lead", "guide engineers"]):
        if "Technical mentorship" not in detected:
            must_haves.append({
                "name": "Technical mentorship",
                "description": "Has directly mentored or led 2+ engineers; can describe their growth concretely",
            })
            detected.add("Technical mentorship")

    must_haves = must_haves[:6]
    if not must_haves:
        must_haves = [
            {"name": "Software engineering", "description": "Strong production engineering background"},
            {"name": "System design", "description": "Has designed systems serving production traffic"},
        ]

    for kw, (name, desc) in _TECH_NICE.items():
        if kw in text_l and name not in detected:
            nice_to_haves.append({"name": name, "description": desc})
            detected.add(name)

    is_regulated = False
    for kw, payload in _DOMAIN_KEYWORDS.items():
        if kw in text_l:
            name, desc = payload[0], payload[1]
            regulated = len(payload) > 2 and bool(payload[2])
            nice_to_haves.append({"name": name, "description": desc})
            if regulated:
                is_regulated = True
            break

    if any(x in text_l for x in ["scale ", "scaling", "throughput", "10x", "8x", "5x", "high-traffic", "high traffic"]):
        nice_to_haves.append({
            "name": "High-scale systems",
            "description": "Has handled significant traffic growth or capacity planning in production",
        })

    if any(x in text_l for x in ["sre", "observability", "on-call", "on call", "slo", "reliability", "incident"]):
        nice_to_haves.append({
            "name": "SRE / observability",
            "description": "Has owned SLOs, error budgets, on-call rotations, or partnered closely with platform teams",
        })

    nice_to_haves = nice_to_haves[:5]

    min_years = 3
    for kw, years in _SENIORITY:
        if kw in text_l:
            min_years = years
            break

    m = re.search(r"(\d+)\+?\s*(?:years?|yrs)", text_l)
    if m:
        try:
            min_years = max(min_years, int(m.group(1)))
        except ValueError:
            pass

    red_flags = [
        "Unexplained gap > 12 months",
        "Title/responsibility mismatch (claimed seniority not backed by resume scope)",
    ]
    if min_years >= 6:
        red_flags.insert(0, "Job-hopping with <18 month tenures across senior roles")
    else:
        red_flags.insert(0, "Job-hopping with <12 month tenures")

    if any(x in text_l for x in ["mentor", "lead ", "team lead", "junior"]):
        red_flags.append("Pure IC profile with no evidence of mentoring, design reviews, or cross-team work")

    if is_regulated:
        red_flags.append("No production exposure to regulated / sensitive-data domains")

    compliance = [
        {"name": "Background verification (BGV)", "required": True,
         "description": "BGV consent signed and clearance received"},
        {"name": "Right to work", "required": True,
         "description": "Work authorisation confirmed for the hiring location"},
        {"name": "Video consent", "required": True,
         "description": "Recording consent form signed before the interview begins"},
    ]
    if is_regulated:
        compliance.append({
            "name": "Regulatory acknowledgment",
            "required": True,
            "description": "Acknowledgment of sector compliance obligations (data handling, AML/HIPAA awareness)",
        })

    return EvaluationChecklist(
        role_title=role_title,
        must_have_skills=[SkillRequirement(**s) for s in must_haves],
        nice_to_have_skills=[SkillRequirement(**s) for s in nice_to_haves],
        red_flag_indicators=red_flags,
        min_years_experience=min_years,
        compliance_checks=[ComplianceCheck(**c) for c in compliance],
    )


def mock_response(step: str, schema: Type[T], context: dict) -> T:
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
