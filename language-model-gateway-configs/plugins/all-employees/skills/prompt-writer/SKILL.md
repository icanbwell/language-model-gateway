---
name: prompt-writer
description: Create high-quality prompt templates that instruct another AI assistant how to perform a user-provided task. Use when the user asks to write, rewrite, improve, or optimize a prompt, instruction set, rubric, or system/task template. Use even if the user does not explicitly say "prompt template" but asks for better instructions for an AI.
license: Internal use only
metadata:
  owner: icanbwell
  last_reviewed: 2026-03-25
  scope: Prompt template authoring and refinement
---

# Prompt Writer

## Skill Card

**Goal**: Produce a robust prompt template that another AI can follow reliably, with minimal variables, explicit structure, and precise output requirements.

**Use when**:
- User asks to write or rewrite a prompt
- User wants to improve instructions for an AI agent
- User shares a rough task description and asks for a polished template
- User asks for a reusable framework for repeated AI tasks
- User asks to transform a current prompt into a better one

**Do not use when**:
- User wants the task solved directly instead of creating instructions
- User asks for code-only output with no prompt design component
- User requests policy-violating behavior

**Required inputs**:
- The user-provided task, goal, or current prompt

**Outputs**:
- A prompt template containing exactly these sections:
  - `<Inputs>`
  - `<Instructions Structure>`
  - `<Instructions>`
- Clear variable names in `{$VARIABLE_NAME}` format
- Concrete behavioral rules and output format requirements

## Purpose

Use this skill to convert a user request into a high-quality instruction template for another assistant. The template must be explicit, consistent, and easy to execute across repeated runs.

## Core Rules

1. Treat the user input as the source of truth for scope.
2. Minimize variables: include only required, non-overlapping inputs.
3. Place long-form inputs before instructions that reference them.
4. Specify output format unambiguously (required tags, sections, ordering).
5. Require reasoning/justification before final score when scoring is requested.
6. Include constraints and failure handling only when relevant.
7. Avoid adding irrelevant process, tools, or domain assumptions.
8. Keep wording precise and implementation-ready.

## Required Workflow

### 1) Understand the task intent
- Identify whether the user wants generation, classification, extraction, transformation, evaluation, planning, or dialogue behavior.
- Determine if the request is simple or complex.
- Preserve domain terms from the user input.

### 2) Define minimal inputs
- Create the smallest set of text variables needed.
- Use short, specific names (for example: `{$TASK}`, `{$DOCUMENT}`, `{$QUESTION}`).
- Avoid overlapping variables (for example, do not define both `{$PROMPT}` and `{$INSTRUCTIONS}` if one fully contains the other).

### 3) Plan instruction structure
- In `<Instructions Structure>`, explain where each variable appears.
- Put long inputs first, then action rules, then output contract.
- Include scratchpad/inner-monologue instructions only for genuinely complex tasks.

### 4) Write the final instructions
- In `<Instructions>`, define role, objective, constraints, and exact output format.
- Add task-specific quality checks (accuracy, citation rules, formatting, safety, refusal behavior if relevant).
- If outputs must be tagged, explicitly require the tag names.
- If evaluation is requested, require: justification first, then score.

### 5) Validate before returning
- Ensure every variable appears exactly once in its XML block.
- Ensure instructions can be followed without outside context.
- Ensure no conflicting or redundant directives.
- Ensure the template is reusable, not tied to a single example.

## Output Contract

Return the result as a prompt template with exactly the following top-level sections and order:

1. `<Inputs>`
2. `<Instructions Structure>`
3. `<Instructions>`

Do not include extra top-level sections unless the user explicitly asks for them.

## Style Requirements

- Be specific, not verbose.
- Prefer imperative language ("Do X", "Return Y").
- Use XML tags to delimit inputs and required output sections.
- Keep formatting consistent and copy/paste ready.
- Do not include meta commentary about how you wrote the template.

## Quality Checklist

Before finalizing, verify all of the following:
- The task is faithfully represented.
- Inputs are minimal and non-overlapping.
- Long context appears before transformation instructions.
- Output format is testable and deterministic.
- Edge conditions are handled (missing info, ambiguity, unsupported requests).
- Scoring tasks require justification before score.
- Template is concise and reusable.

## Failure Handling

If the user input is too ambiguous to produce a reliable template:
- State what is missing in one short sentence.
- Ask only the minimum clarifying questions needed.
- Do not invent domain requirements.

If the request is unsafe or policy-violating:
- Refuse according to policy and do not provide an enabling template.

## Example Skeleton

Use this skeleton shape when generating outputs:

````markdown
<Inputs>
{$TASK}
</Inputs>

<Instructions Structure>
- Briefly describe where TASK appears and why.
- Describe output ordering and required sections.
</Instructions Structure>

<Instructions>
You are an AI assistant responsible for completing the task described below.

<task>
{$TASK}
</task>

Follow these rules:
- Rule 1
- Rule 2
- Rule 3

Return your final output inside <answer> tags.
</Instructions>
````

## Notes

- Prefer one strong template over many weak alternatives.
- Include examples only when they materially improve reliability.
- Optimize for consistent execution by an inexperienced assistant.
