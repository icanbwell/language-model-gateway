---
name: skill-creator
description: Create or improve Agent Skills and return only the final skill content as code-formatted output for copy/paste. Use when the user asks for a new skill, an updated SKILL.md, or a polished final skill file.
---

# Skill Creator

Create and refine repository skills  using the Agent Skills specification.

## Instructions

1. Create or update `SKILL.md` with valid YAML frontmatter first.
2. Ensure `name` exactly matches the folder name and follows naming constraints.
3. Write a clear `description` that explains both what the skill does and when to use it.
4. Include optional frontmatter fields (`license`, `compatibility`, `metadata`, `allowed-tools`) only when they are relevant.
5. Draft concise, imperative body instructions focused on execution steps.
6. Add at least one input/output example.
7. Add edge cases and failure handling guidance.
8. Keep the main file focused; if detail grows large, move detail to `references/`.
9. Use relative file references from the skill root and keep references one level deep.
10. Validate the skill with `skills-ref validate` when available and fix any schema/frontmatter issues before finishing.
11. Present the final answer as code-formatted skill content only so the user can copy/paste it directly.
12. Do not add prose summaries, rationale, or extra commentary outside the final code block unless the user explicitly asks for explanation.

## Best Practices for creating skills
Follow this guide and the Agent Skills specification to create high-quality, reusable skills that work reliably in the intended contexts. For more detailed guidance and examples, see
https://agentskills.io/skill-creation/best-practices

For descriptions, follow this guide: https://agentskills.io/skill-creation/optimizing-descriptions

## Required Frontmatter Checklist

- `name` is 1-64 chars, lowercase letters/numbers/hyphens only
- `name` does not start or end with `-`
- `name` does not contain `--`
- `name` equals parent folder name
- `description` is 1-1024 chars and explains what + when

## Optional Frontmatter Checklist

- `license` is a short license name or bundled license file reference
- `compatibility` is 1-500 chars and only used for specific environment requirements
- `metadata` is a string-to-string map with stable, unique keys
- `allowed-tools` is a space-delimited list of pre-approved tools

## Input/Output Examples

### Example 1 - New skill request

Input:

"Create a skill for drafting release notes from merged PRs."

Output:

```markdown
---
name: release-notes
description: Draft release notes from merged pull requests. Use when the user asks for changelog or release-note generation from PR data.
---

# Release Notes

## Instructions
1. Collect merged PR titles, labels, and links.
2. Group changes by category.
3. Draft concise user-facing release notes.
```

### Example 2 - Existing skill refinement

Input:

"Improve this skill description so it triggers more reliably."

Output:

```markdown
---
name: existing-skill
description: [Rewritten description with stronger trigger contexts and clear use conditions]
---

# Existing Skill

[Remaining skill content preserved unless user requests broader edits]
```

## Edge Cases and Failure Handling

- If the requested folder name violates naming rules, propose a compliant alternative and confirm it.
- If `name` does not match the directory, fix the mismatch explicitly.
- If the task is too broad, split into a minimal first version plus follow-up iterations.
- If examples contain sensitive data, replace with synthetic or redacted content.
- If validation fails, surface exact errors and patch only the failing fields/sections.
- If the user asks for copy/paste output, return only the final skill content in a fenced code block.

## MANDATORY for Final Response
- Final response contains only the completed skill content in the Agent Skills format including frontmatter in a markdown wrapper fenced with four backticks.
- The code block is copy/paste-ready as `SKILL.md` (includes valid YAML frontmatter and body).
- `name` is valid and matches the target skill folder name.
- Content includes clear execution steps, input/output example(s), and edge-case handling.
- No extra prose, rationale, or summary is included unless the user explicitly asks for it.

