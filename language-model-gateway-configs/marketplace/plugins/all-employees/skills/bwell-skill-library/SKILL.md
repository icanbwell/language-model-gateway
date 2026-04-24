---
name: bwell-skill-library
description: Creates or refines Agent Skills following the Agent Skills specification. Use this skill when the user requests a new skill, asks to improve an existing SKILL.md, needs a skill validated against specification requirements, wants to optimize a skill description for better triggering, or requests a polished final skill file ready for deployment. Use even if the user doesn't explicitly mention "Agent Skills" or "SKILL.md" but is asking about creating reusable instructions, procedures, or capabilities for an agent.
license: Internal use only
metadata:
  owner: baileyai
  source: Agent Skills Specification
  source_url: https://agentskills.io
  last_reviewed: 2024-01-15
  scope: Agent skill creation, refinement, and optimization
---

# Skill Creator

## Skill Card

**Goal**: Create or refine Agent Skills that follow the Agent Skills specification, producing copy/paste-ready SKILL.md files with valid YAML frontmatter, clear execution instructions, and optimized descriptions that trigger reliably.

**Use when**:
- User requests a new skill be created
- User asks to improve or update an existing SKILL.md file
- User needs a skill validated against the Agent Skills specification
- User wants to optimize a skill description for better triggering
- User asks for help structuring skill documentation
- User describes a reusable procedure or capability they want to capture
- User mentions creating instructions for repetitive tasks

**Do not use when**:
- User is asking about skill usage (not creation)
- Request is for general documentation unrelated to Agent Skills
- User wants to execute a skill rather than create one
- User is asking about non-skill documentation formats

**Required inputs**:
- Skill purpose or goal (what the skill should accomplish)
- Skill name or proposed folder name
- Context about when the skill should be used
- Domain-specific knowledge or existing artifacts (optional but highly recommended)

**Outputs**:
- Complete SKILL.md file with valid YAML frontmatter
- Formatted as copy/paste-ready markdown code block (four backticks)
- Validated against Agent Skills specification
- Validation is mandatory before final output (see Section 9 for the exact command)
- Includes execution steps, examples, and edge case handling
- Optimized description for reliable triggering
- Under 500 lines (move detail to references/ if needed)
- No extra prose unless explicitly requested

**Tool usage**:
- Use web search or documentation retrieval to reference Agent Skills specification when needed
- Validate against specification requirements before finalizing
- No external tools required for basic skill creation

**Safety and privacy**:
- Replace any sensitive data in examples with synthetic content
- Ensure skill descriptions don't expose internal system details unnecessarily
- Follow principle of least privilege for allowed-tools specifications
- Never include credentials, API keys, or PII in skill examples

## **MANDATORY SKILL CREATION PROTOCOL**

**BEFORE drafting any skill:**

1. ✓ Understand the domain and gather context (see "Start from Real Expertise" below)
2. ✓ Confirm the skill name follows naming constraints (1-64 chars, lowercase, hyphens only, no leading/trailing/double hyphens)
3. ✓ Verify the skill name matches the target folder name
4. ✓ Identify the skill's purpose and trigger conditions
5. ✓ Determine required inputs and expected outputs
6. ✓ Identify if any specific tools must be used
7. ✓ Plan to keep SKILL.md under 500 lines (use references/ for detail)
8. ✓ Plan to run mandatory validation as defined in Section 9 before final output
9. ✓ Only then proceed with drafting the skill

**Never create a skill without first gathering domain-specific context. Generic skills based solely on LLM training knowledge produce vague, low-value instructions.**

## Purpose

Use this skill to create high-quality, specification-compliant Agent Skills that are reusable, reliable, and work consistently in their intended contexts. The skill ensures proper frontmatter structure, clear execution logic, comprehensive documentation, and optimized descriptions that trigger on the right prompts. All skills must stay under 500 lines in the main SKILL.md file.

## Start from Real Expertise

**The most common pitfall in skill creation is generating skills without domain-specific context.** Effective skills are grounded in real expertise, not generic knowledge.

### Gather Context First

**Before creating any skill, ask the user for domain-specific material:**

- "Do you have existing documentation, runbooks, or style guides for this process?"
- "Can you walk me through a real example of this task, including what worked and what didn't?"
- "Are there specific tools, APIs, or conventions I should know about?"
- "Have you encountered common failure modes or edge cases?"
- "Do you have code review comments, issue trackers, or incident reports related to this?"

### Extract from Hands-On Tasks

If the user doesn't have existing artifacts, complete a real task with them first:

1. Have them describe a specific instance of the task
2. Work through it together, noting corrections and preferences
3. Pay attention to:
   - Steps that worked
   - Corrections they made ("use library X instead of Y")
   - Input/output formats
   - Project-specific facts they provided
4. Extract the reusable pattern into the skill

### Synthesize from Existing Artifacts

When the user has existing material, use it to ground the skill:

**Good source material:**
- Internal documentation, runbooks, style guides
- API specifications, schemas, configuration files
- Code review comments and issue trackers
- Version control history (patches, fixes)
- Real-world failure cases and resolutions
- Incident reports and post-mortems

**Ask:** "Can you share any of these materials? They'll help me create a skill that matches your actual practices rather than generic best practices."

## Required Inputs

**From User (gather before creation):**
- Skill purpose and goal
- Proposed skill name or folder name
- Trigger conditions (when should this skill be used)
- Required functionality and tools
- **Domain-specific context** (documentation, examples, conventions)
- Any existing skill content (if refining)

**Specification Requirements (validate during creation):**
- Agent Skills specification constraints
- Naming rules and conventions
- Frontmatter schema requirements
- Best practices from https://agentskills.io
- 500-line limit for main SKILL.md

## Expected Outputs

- **Complete SKILL.md file**: Valid YAML frontmatter + markdown body
- **Copy/paste ready**: Wrapped in four-backtick code fence
- **Specification compliant**: Passes all validation rules
- **Optimized description**: Triggers on relevant prompts, avoids false positives
- **Clear structure**: Focused on what the agent lacks, not what it knows
- **Practical examples**: Based on real usage, not generic scenarios
- **Under 500 lines**: Main file stays focused; detail moved to references/
- **No extra commentary**: Only the skill content unless user requests explanation
- **Validation confirmation**: Include whether `scripts/validate.py` passed, and if it failed, fix and re-run before final output

## Decision Flow

### 1. Gather Requirements and Context

**Confirm basics:**
- Skill name, purpose, trigger conditions
- If name invalid: Propose compliant alternative and confirm with user
- If purpose unclear: Ask clarifying questions

**CRITICAL: Gather domain-specific context:**
- Ask for existing documentation, examples, or artifacts
- If none available, work through a real example together
- Never proceed with generic knowledge alone

### 2. Validate Naming Constraints

**MANDATORY: Validate BEFORE drafting**
- Name is 1-64 characters
- Lowercase letters, numbers, hyphens only
- No leading/trailing hyphens
- No double hyphens (`--`)
- Matches target folder name

### 3. Draft Optimized Description

**Description must be 1-1024 chars and include:**
- What the skill does (action/capability)
- When to use it (trigger conditions)
- Broad coverage ("even if they don't explicitly mention X")

**Use imperative phrasing:**
- ✅ "Use this skill when..."
- ❌ "This skill does..."

**Focus on user intent, not implementation:**
- ✅ "Analyze CSV and tabular data files"
- ❌ "Uses pandas DataFrame operations to process CSV files"

**Be explicit about trigger contexts:**
- Include cases where user doesn't name the domain directly
- Example: "even if they don't explicitly mention 'CSV' or 'analysis'"

**Keep it concise but complete:**
- A few sentences to a short paragraph
- Cover the skill's scope without bloating context

### 4. Structure Body Content

**Keep main SKILL.md under 500 lines:**
- Focus on essential execution guidance
- Move detailed reference material to `references/` directory
- Tell agent *when* to load each reference file
- Example: "Read `references/api-errors.md` if the API returns a non-200 status code"

**Spend context wisely:**

**Add what the agent lacks:**
- Project-specific conventions
- Domain-specific procedures
- Non-obvious edge cases
- Specific tools or APIs to use
- Gotchas that defy reasonable assumptions

**Omit what the agent knows:**
- Don't explain what a PDF is, how HTTP works, or what a database migration does
- Don't include generic best practices the agent already follows
- Ask yourself: "Would the agent get this wrong without this instruction?"

**Design coherent units:**
- One skill = one coherent unit of work
- Not too narrow (forces multiple skills for one task)
- Not too broad (hard to activate precisely)

**Aim for moderate detail:**
- Concise, stepwise guidance with working examples
- Avoid exhaustive documentation that obscures what's relevant
- When covering every edge case, consider if most are better handled by agent judgment

### 5. Calibrate Control

**Match specificity to fragility:**

**Give the agent freedom** when:
- Multiple approaches are valid
- Task tolerates variation
- Explaining *why* helps agent make context-dependent decisions

**Be prescriptive** when:
- Operations are fragile
- Consistency matters
- Specific sequence must be followed
- Example: "Run exactly this sequence: `python scripts/migrate.py --verify --backup`. Do not modify the command or add additional flags."

**Provide defaults, not menus:**
- ✅ "Use pdfplumber for text extraction. For scanned PDFs requiring OCR, use pdf2image with pytesseract instead."
- ❌ "You can use pypdf, pdfplumber, PyMuPDF, or pdf2image..."

**Favor procedures over declarations:**
- Teach *how to approach* a class of problems
- Not *what to produce* for a specific instance
- The approach should generalize even when details are specific

### 6. Include Effective Instruction Patterns

**Gotchas sections** (highest-value content):
```markdown
## Gotchas

- The `users` table uses soft deletes. Queries must include
  `WHERE deleted_at IS NULL` or results will include deactivated accounts.
- The user ID is `user_id` in the database, `uid` in the auth service,
  and `accountId` in the billing API. All three refer to the same value.
```

**Templates for output format:**
- Provide concrete structures, not prose descriptions
- Agents pattern-match well against templates
- Short templates inline; longer templates in `assets/`

**Checklists for multi-step workflows:**
```markdown
Progress:
- [ ] Step 1: Analyze the form
- [ ] Step 2: Create field mapping
- [ ] Step 3: Validate mapping
- [ ] Step 4: Fill the form
```

**Validation loops:**
```markdown
1. Make your edits
2. Run validation using the exact command in Section 9
3. If validation fails:
   - Review the error message
   - Fix the issues
   - Run validation again
4. Only proceed when validation passes
```

**Plan-validate-execute pattern:**
- For batch or destructive operations
- Create intermediate plan in structured format
- Validate against source of truth
- Only then execute

**Bundle reusable scripts:**
- If agent reinvents same logic across runs, write a tested script
- Place in `scripts/` directory
- Reference from SKILL.md

### 7. Add Examples

**At least one input/output example:**
- Show realistic usage scenarios
- Use synthetic data for sensitive content
- Based on real usage, not generic scenarios
- Include context: file paths, personal details, specific values

### 8. Include Edge Case Handling

**Document common failure modes:**
- Missing data scenarios
- Validation failures
- Recovery strategies
- When to ask for clarification

### 9. Validate Against Specification

**MANDATORY before final output:**

You MUST validate the skill using `run_skill_script` before presenting it to the user. This is not optional.

**Step-by-step validation process:**

1. **Call `run_skill_script`** with:
   - `skill_name`: `"skill-creator"`
   - `script_name`: `"validate.py"`
   - `arguments`: A JSON object with field `"skill_content"` containing the complete SKILL.md text

   **Allowed script note:** `validate.py` is the only script you should call for this skill.
   Never call `create_skill` or `create_skill.py` with `run_skill_script`.

2. **Check validation result:**
   - If validation passes: Proceed to Section 10 (Format Final Output)
   - If validation fails: Review error messages, fix issues, and run validation again

3. **Never skip validation:**
   - Do not present a skill to the user without successful validation
   - Do not ask the user to validate manually
   - Do not provide bash commands for the user to run
   - You must run the validation yourself using `run_skill_script`
   - Do not attempt to call `create_skill`/`create_skill.py`; those scripts do not exist

**Example tool call:**
```
run_skill_script(
  skill_name="skill-creator",
  script_name="validate.py",
  arguments={
    "skill_content": "---\nname: example-skill\n...[full skill content]..."
  }
)
```

**Frontmatter validation:**
- Schema compliance
- Naming constraints met
- Description quality (1-1024 chars, includes what + when)
- Optional fields only when relevant

**Body structure validation:**
- Clear execution steps
- Examples included
- Edge cases documented
- Context spent wisely (adds what agent lacks, omits what it knows)
- **Main SKILL.md under 500 lines**

### 10. Apply Progressive Disclosure

**If skill content exceeds 500 lines:**

1. **Identify what to move:**
   - Detailed API documentation → `references/api-reference.md`
   - Extended examples → `references/examples.md`
   - Technical background → `references/technical-details.md`
   - Error codes and messages → `references/error-handling.md`

2. **Add load triggers in main SKILL.md:**
   ```markdown
   For detailed API specifications, read `references/api-reference.md`
   
   If you encounter an API error, read `references/error-handling.md`
   ```

3. **Keep in main SKILL.md:**
   - Skill Card
   - Core execution steps
   - Gotchas section
   - At least one example
   - Edge case overview

### 11. Format Final Output

- Confirm validator status first (`scripts/validate.py` must pass before final delivery).

**MANDATORY: Wrap in four-backtick markdown code fence:**
````markdown
[Complete skill content here]
````
