---
name: post-commit-audit
description: >
  Audit recent git commits for security issues, code quality, compliance gaps, test coverage,
  and dependency changes. Use this skill whenever the user says "audit my commit", "review what
  I just pushed", "check my recent changes for issues", "post-commit review", "what did I break",
  "audit the last N commits", or asks about the safety/quality/compliance of recent code changes.
  Also use when the user wants a pre-merge sanity check or asks to validate changes before
  opening a PR.
---

# Post-Commit Audit

Perform a comprehensive audit of recent git commits covering five areas: security, code quality,
compliance, test coverage, and dependency changes. The goal is to catch problems early — before
they reach code review or production — by giving the developer a structured report they can act on.

## When to run this audit

- After committing code, to catch issues before pushing
- Before opening a pull request, as a self-review step
- After merging, to verify nothing slipped through
- When onboarding to unfamiliar code and wanting to understand recent changes
- When the user asks to "audit", "review", or "check" recent commits

## Audit workflow

### Step 1: Determine scope

Ask the user which commits to audit if it's not obvious from context. Sensible defaults:

- **"audit my last commit"** → `HEAD~1..HEAD`
- **"audit my branch"** → `main..HEAD` (or `master..HEAD`)
- **"audit the last 3 commits"** → `HEAD~3..HEAD`
- If unclear, default to the latest commit and confirm with the user

Collect the diff and changed file list:

```bash
git log --oneline <range>
git diff --stat <range>
git diff <range>
```

### Step 2: Security audit

Scan the diff for security concerns. Focus on what *changed*, not the entire codebase.

**Secrets & credentials:**
- API keys, tokens, passwords, connection strings added to code or config
- `.env` files or sensitive config committed by accident
- Private keys, certificates, JWTs in the diff

**Vulnerability patterns (reference OWASP Top 10 and CWE):**
- SQL injection via string concatenation in queries (CWE-89)
- Command injection via unsanitized input in shell calls (CWE-78)
- Path traversal via user input in file paths (CWE-22)
- XSS via unescaped user input in HTML/templates (CWE-79)
- Unsafe deserialization of untrusted data (CWE-502)
- Hardcoded credentials (CWE-798)

**Dependency security:**
- New dependencies added — check if they're well-maintained and widely used
- Version pins removed or loosened
- Known-vulnerable versions introduced

Report each finding with the file, line number, severity (critical/high/medium/low), and a
one-line explanation of the risk.

### Step 3: Code quality review

Review the changed code for quality issues that automated linters might miss:

- **Complexity:** Functions that grew too long or deeply nested
- **Error handling:** Bare `except:` clauses, swallowed exceptions, missing error handling on I/O
- **Naming:** Unclear variable/function names that hurt readability
- **Dead code:** Commented-out code, unreachable branches, unused imports added
- **Duplication:** Copy-pasted logic that should be extracted
- **API misuse:** Using deprecated functions, incorrect argument types, ignoring return values

Keep this proportional — a 5-line bugfix doesn't need the same scrutiny as a 500-line feature.
Flag only issues that meaningfully impact maintainability or correctness.

### Step 4: Test coverage assessment

Check whether the changes are adequately tested:

1. Identify which functions/classes were added or modified
2. Check if corresponding test files exist and were updated
3. Look for untested edge cases in the new logic (error paths, boundary conditions, empty inputs)
4. If test files were changed, verify the tests actually exercise the new code paths

Don't demand 100% coverage — focus on whether the *important* paths are tested. A config change
doesn't need a test. A new parsing function does.

### Step 5: Compliance documentation check

Relevant when the project has compliance requirements (like this one's LLM compliance integration):

- Were new AI models or third-party AI components added without documentation?
- Do dependency changes affect supply chain documentation?
- Were system transparency docs (README, architecture docs) updated to reflect changes?
- If compliance config exists, does it still accurately describe the system?

Skip this section if the project has no compliance concerns — don't force it.

### Step 6: Dependency change analysis

If `pyproject.toml`, `requirements.txt`, `package.json`, or similar files changed:

- List added, removed, and version-changed dependencies
- For new deps: note what they do, their license, download count/popularity if easily checkable
- For removed deps: verify no remaining imports reference them
- For version changes: note if it's a major version bump (potential breaking changes)

### Step 7: Generate the report

Present findings as a structured report:

```
## Post-Commit Audit: <commit range>

### Summary
- Commits audited: N
- Files changed: N
- Security findings: N (X critical, Y high, Z medium)
- Quality issues: N
- Test coverage gaps: N
- Compliance notes: N
- Dependency changes: N

### Security
[findings with severity, file:line, description, and suggested fix]

### Code Quality
[issues with file:line and recommendation]

### Test Coverage
[gaps identified and what tests would help]

### Compliance
[documentation gaps or supply chain changes]

### Dependencies
[changes with risk assessment]

### Verdict
[Overall assessment: PASS / PASS WITH NOTES / NEEDS ATTENTION]
- PASS: No critical/high findings, changes look solid
- PASS WITH NOTES: Minor issues worth addressing but not blocking
- NEEDS ATTENTION: Critical or high-severity findings that should be fixed before merging
```

## Calibration guidance

The audit should be genuinely useful, not a wall of noise. A few important principles:

- **Severity matters.** A hardcoded API key is critical. A slightly-too-long function name is not
  worth mentioning unless there's a pattern.
- **Context matters.** A `TODO` in test code is fine. Unsanitized user input passed to shell
  commands is not.
- **Be specific.** "Consider adding error handling" is useless. "The `parse_workflow()` call on
  line 47 can raise `JSONDecodeError` but nothing catches it — this will crash the CLI" is helpful.
- **Don't invent problems.** If the commit is clean, say so. A short "looks good, no issues found"
  is a valid audit result.
