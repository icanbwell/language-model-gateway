---
name: bwell-skill-publisher
description: Publish a skill to the shared b.well skills marketplace so it becomes available to all users. Use this skill when the user wants to publish, save, deploy, or share a skill they have created or refined. Use even if the user does not explicitly say "publish" but asks to make a skill available to others, push a skill to the marketplace, or commit a skill to the repository.
license: Internal use only
metadata:
  owner: icanbwell
  last_reviewed: 2026-05-04
  scope: Skill publishing and marketplace deployment
allowed-tools:
  - skills-publisher:*
  - skills-library:list_skills
  - skills-library:load_skill
---

# Skill Publisher

## Skill Card

**Goal**: Publish a completed skill to the b.well shared skills marketplace via the skills-publisher MCP server, making it available to all users across the organization.

**Use when**:
- User asks to publish, save, or deploy a skill to the marketplace
- User wants to share a skill with others in the organization
- User asks to push or commit a skill to the skills repository
- User has finished creating or refining a skill and wants it live
- User asks to update an existing published skill with new content

**Do not use when**:
- User wants to create or author a new skill from scratch (use bwell-skill-library instead)
- User wants to browse or load existing skills (use skills-library MCP server directly)
- User is asking about skill concepts without intent to publish

**Required inputs**:
- The complete skill content (SKILL.md with valid YAML frontmatter and markdown body)
- The skill name (must match the name field in frontmatter)

**Outputs**:
- Confirmation that the skill was published to the marketplace
- The skill name and location in the marketplace
- Any errors or issues encountered during publishing

**Tool usage**:
- **skills-publisher MCP server**: Used to save and publish skill content to the repository
- **skills-library MCP server**: Used to verify the skill appears in the marketplace after publishing

## Prerequisites

Before publishing a skill, verify these requirements:

1. **Valid SKILL.md content**: The skill must have valid YAML frontmatter with at minimum `name` and `description` fields
2. **Name follows conventions**: 1-64 characters, lowercase letters, numbers, and hyphens only, no leading/trailing/double hyphens
3. **Description is actionable**: Starts with an action verb, describes what the skill does and when to use it
4. **Content is complete**: The skill has been reviewed and is ready for others to use

## Publishing Workflow

### Step 1: Validate the skill content

Before publishing, confirm the skill content is ready:

- [ ] Frontmatter has `name` and `description` fields
- [ ] Name follows naming constraints (lowercase, hyphens, 1-64 chars)
- [ ] Description is 1-1024 characters and includes what + when
- [ ] Body contains clear execution instructions
- [ ] No PHI, PII, credentials, or secrets in the content

If the skill was created using the `bwell-skill-library` skill, it should already be validated. If not, review the content against these requirements before proceeding.

### Step 2: Publish using skills-publisher

Use the **skills-publisher** MCP server tools to publish the skill.

Call the skills-publisher MCP tools to save the skill content. The skills-publisher server handles:
- Creating or updating the skill files in the skills repository
- Creating a pull request for the changes
- Making the skill available in the marketplace once merged

If the skills-publisher requires OAuth authentication, the user will be prompted to authenticate via Okta. This is expected and required for write access.

### Step 3: Verify publication

After publishing:
1. Call `list_skills` on the **skills-library** MCP server to confirm the skill appears
2. Report the result to the user including:
   - Whether the publish succeeded
   - The skill name as it appears in the marketplace
   - Any next steps (e.g., PR review required)

## Handling Common Scenarios

### Updating an existing skill
If a skill with the same name already exists, the publish operation updates the existing skill. Confirm with the user before overwriting.

### Authentication required
The skills-publisher MCP server requires OAuth authentication through Okta. If you receive an authentication error:
1. Inform the user that authentication is required
2. The OAuth flow will be triggered automatically
3. Retry the publish after authentication completes

### Publish fails
If the publish operation fails:
1. Report the error message to the user
2. Check if it is a validation error (fix the skill content) or a server error (retry or escalate)
3. Do not retry more than once without user confirmation

## Example Usage

**User**: "I just finished creating the fhir-query-builder skill. Can you publish it to the marketplace?"

**Agent workflow**:
1. Confirm the user has the complete SKILL.md content ready
2. Validate the content meets requirements
3. Call skills-publisher to publish the skill named `fhir-query-builder`
4. Call `list_skills` on skills-library to verify it appears
5. Report success to the user

## Gotchas

- The skills-publisher and skills-library are separate MCP servers. Do not try to publish using skills-library tools — it is read-only.
- OAuth authentication is required for publishing. The first publish in a session will trigger an auth flow.
- Skill names must exactly match between the frontmatter `name` field and the directory/folder name used for publishing.
- Publishing creates a PR in the skills repository. The skill may not be immediately available until the PR is merged, depending on the repository's review requirements.
