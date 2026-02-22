---
name: commit-and-push
description: Creates a git commit with Conventional Commits format and pushes to the current branch.
license: MIT
metadata:
  author: CesarBenavides777
  version: "1.0.0"
user-invocable: true
---

# Commit and Push

Creates a standardized git commit using Conventional Commits and pushes to the current branch.

## Usage

Run `/commit-and-push` or `/commit` after completing work.

## Commit Message Format

```
<type>: <description>

- Bullet point describing specific change
- Another change made

[optional footer]
```

### Types

| Type       | When to use                                             |
| ---------- | ------------------------------------------------------- |
| `feat`     | New feature or new MCP tool                             |
| `fix`      | Bug fix                                                 |
| `chore`    | Maintenance, dependencies                               |
| `docs`     | Documentation only                                      |
| `refactor` | Code change that neither fixes a bug nor adds a feature |
| `test`     | Adding or updating tests                                |
| `style`    | Formatting, missing semicolons, etc.                    |
| `perf`     | Performance improvement                                 |
| `ci`       | CI/CD changes                                           |

## Process

### Step 1: Gather Context

1. Run `git status` to see changed files
2. Run `git diff --staged` and `git diff` to understand changes
3. Determine the appropriate commit type from the changes

### Step 2: Draft Commit Message

Create a commit message following Conventional Commits:

```
<type>: Brief imperative description (50 chars max)

- Specific change 1
- Specific change 2
- Specific change 3
```

**Guidelines:**

- First line: type prefix + imperative mood ("Fix", "Add", "Update", not "Fixed", "Added")
- Keep first line under 72 characters
- Blank line after first line
- Bullet points for specific changes (what, not why)
- Use scope when helpful: `feat(tools):`, `fix(oauth):`, `chore(deps):`
- **NEVER** include `Co-Authored-By` lines

### Step 3: Confirm with User

Show the proposed commit message and ask:

> "Ready to commit and push with this message? (yes/no/edit)"

### Step 4: Execute

If confirmed:

```bash
git add -A
git commit -m "$(cat <<'EOF'
<type>: Brief description

- Change 1
- Change 2
EOF
)"
git push origin HEAD
```

### Step 5: Report

After completion, report:

- Commit hash
- Branch name
- Files changed count
- Push status

## Examples

### Example 1: New MCP Tool

```
feat(tools): add recurring transaction detection tool

- Implement get_recurring_transactions via MonarchClient
- Add Zod input schema for date range filtering
- Register tool with readOnlyHint annotation
```

### Example 2: Bug Fix

```
fix(oauth): resolve HTTPS URL generation behind reverse proxy

- Respect X-Forwarded-Proto header in OAuth discovery endpoint
- Fix redirect URLs using HTTP instead of HTTPS on Fly.io
```

### Example 3: Analysis Feature

```
feat(analysis): add cash flow forecasting engine

- Implement 30/60/90 day projection based on recurring transactions
- Add confidence intervals using historical variance
- Include unit tests with mock transaction data
```

## Safety Rules

- Always stage all changes with `git add -A` unless user specifies otherwise
- **Never force push** unless explicitly requested
- **Never** include `Co-Authored-By` in commit messages
- If push fails due to remote changes, pull and rebase:
  ```bash
  git pull --rebase origin HEAD
  git push origin HEAD
  ```
- If rebase has conflicts, stop and report to user
