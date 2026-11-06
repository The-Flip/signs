---
name: commit
description: Generates commit messages and creates commits. Use when writing commit messages, committing changes, or reviewing staged changes.
---

# Commit Messages

Use [Conventional Commits](https://www.conventionalcommits.org/) format.

## Format

```text
<type>(<scope>): <description>

[optional body]
```

## Types

- `feat`: User-facing features or behavior changes (must change production code)
- `fix`: Bug fixes (must change production code)
- `docs`: Documentation only
- `style`: Code style/formatting (no logic changes)
- `refactor`: Code restructuring without behavior change
- `test`: Adding or updating tests
- `chore`: CI/CD, tooling, dependency bumps, configs (no production code)

## Scopes

Optional. Use when it adds clarity. Examples: `cli`, `render`, `merge`.

## Examples

```text
feat(cli): add command to render a sign
fix(merge): skip blank rows in data files
refactor(render): simplify page size handling
chore: add pre-commit hooks
docs: update architecture notes
test: add tests for merged sign output
```

## Instructions

1. Run `git diff --staged` to see staged changes
2. Analyze the changes and determine the appropriate type
3. Write a concise description (under 72 characters)
4. Add body only if the "why" isn't obvious from the description
