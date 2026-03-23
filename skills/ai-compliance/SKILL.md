---
name: AI Compliance Evidence Collection
description: >-
  This skill should be used when the user asks about "AI compliance",
  "AI regulations", "GDPR for AI", "EU AI Act", "compliance evidence",
  "risk classification", "AI disclosure requirements", "privacy impact assessment",
  "bias testing", "human oversight", "consent records", "incident management",
  "governance framework", or mentions building an AI/LLM application that needs
  to comply with regulations in specific countries or jurisdictions. Also trigger
  when the user asks to "generate compliance templates", "check compliance",
  "run evidence checker", or "fill compliance config".
version: 1.0.0
---

# AI Compliance Evidence Collection Kit

Gather AI and LLM compliance information for relevant jurisdictions while building software projects. When an application uses AI, identify applicable regulations, required disclosures, risk classifications, and compliance deadlines for the countries the project will operate in.

## When to Use

- Building an AI-powered application that operates in regulated jurisdictions
- Needing to identify which AI regulations apply to a project
- Generating compliance evidence documentation for legal review
- Running the evidence collection pipeline (config, interactive tools, autofill, checker)

## Knowledge Base

The regulation files in the project root provide jurisdiction-specific guidance:

- `AI-Regulations-Global-Overview.md` — Cross-cutting themes, compliance timeline, comparison matrix
- Regional files: `AI-Regulations-EU.md`, `AI-Regulations-UK.md`, `AI-Regulations-UnitedStates.md`, `AI-Regulations-Canada.md`, `AI-Regulations-China.md`, `AI-Regulations-Japan-SouthKorea.md`, `AI-Regulations-India-Singapore-ASEAN.md`, `AI-Regulations-Australia.md`, `AI-Regulations-NewZealand.md`, `AI-Regulations-Mexico-LatinAmerica.md`, `AI-Regulations-Africa.md`
- `AI-Regulations-World-Map.html` — Interactive D3.js visualization

To answer jurisdiction-specific questions, read the relevant regional file. Start with the Global Overview for cross-jurisdictional comparisons.

## Evidence Collection Pipeline

The pipeline produces filled compliance templates in `output/`. The workflow:

### 1. Configure: `tools/compliance-config.json`

Edit this JSON file with system details, organization info, jurisdictions, and deployment specifics. Key sections:
- `system` — AI system name, version, model type, foundation model, input/output types
- `organization` — Company name, document owner, session reference
- `project` — Target jurisdictions, risk level, sector
- `dates` — Key compliance dates

### 2. Interactive Tools: `tools/interactive/*.html`

19 browser-based HTML tools for human-judgment fields that cannot be auto-filled. Open in any browser, load the config, fill in assessments, save back to config. Each tool saves results to `config.interactiveToolResults.<toolName>`.

Available tools and their template mappings:
- `risk-classification.html` — Template 17: EU AI Act risk tier
- `pia-assessment.html` — Template 07: Privacy Impact Assessment
- `bias-testing.html` — Template 08: Bias/fairness testing
- `human-oversight.html` — Template 09: Oversight model design
- `consent-design.html` — Template 10: Consent mechanism design
- `consent-records-audit.html` — Template 10: Consent records audit
- `dsr-rights-implementation.html` — Template 11: Data subject rights
- `transparency-documentation.html` — Template 01: System transparency
- `disclosure-toolkit.html` — Template 02: User-facing disclosures
- `content-labeling.html` — Template 03: AI content labeling
- `automated-decision-logic.html` — Template 04: Decision logic documentation
- `training-data-disclosure.html` — Template 05: Training data documentation
- `impact-risk-scoring.html` — Template 06: Impact/risk scoring
- `governance-framework.html` — Template 12: Governance structure
- `incident-management.html` — Template 13: Incident response plan
- `security-assessment.html` — Template 15: Security assessment
- `content-moderation.html` — Template 16: Content moderation
- `conformity-assessment.html` — Template 19: Conformity assessment
- `ai-literacy-training.html` — Template 18: AI literacy training

### 3. Auto-fill: `node tools/autofill.js`

Populates all 22 evidence templates from config data and interactive tool results:

```bash
node tools/autofill.js --config tools/compliance-config.json --output output/
```

### 4. Validate: `node tools/evidence-checker.js`

Checks all templates for completeness and compliance gaps:

```bash
node tools/evidence-checker.js --config tools/compliance-config.json --output output/
node tools/evidence-checker.js --config tools/compliance-config.json --output output/ --json
node tools/evidence-checker.js --config tools/compliance-config.json --output output/ --template 07
```

Flags: `--template NN` (filter), `--verbose`, `--json` (structured output).

### 5. Review

Hand the `output/` folder to a legal or compliance expert. The output includes:
- 22 filled evidence templates (markdown)
- `MANIFEST.md` — Index of all templates
- `compliance-config-snapshot.json` — Config at time of generation
- `evidence-check-report.txt` — Validation report

## Supporting Data

- `tools/data/jurisdiction-matrix.json` — Which templates each jurisdiction requires
- `tools/data/deadline-data.json` — 21 compliance deadlines with dates and jurisdictions

## Response Guidelines

- Lead with the most actionable compliance requirement for the user's jurisdiction
- Distinguish between enacted/binding law and voluntary/proposed frameworks
- Always note key compliance deadlines
- When multiple jurisdictions apply, prioritize by enforcement risk
- Cite specific laws, dates, and provisions — do not generalize
- Include a disclaimer that this is research, not legal advice
- If a regulation's status may have changed since the last update date, note that caveat

## Template Categories (24 evidence types)

RC (Risk Classification), CA (Conformity Assessment), RM (Risk Management), IA (Impact Assessment), TD (Transparency Documentation), TD-D (Disclosure), TD-CR (Content/Rights), TRANS (Transparency), DISC (Disclosure), LABEL (Labeling), HO (Human Oversight), BIAS (Bias Testing), PIA (Privacy Impact), CONS (Consent), DSR (Data Subject Rights), GOV (Governance), LIT (AI Literacy), INC (Incident Management), REG (Registration), SEC (Security), SAFE (Safety), MOD (Content Moderation), LOG (Logging), ETH (Ethics).
