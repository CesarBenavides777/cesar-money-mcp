---
name: project-summary
description: Generate a quick snapshot of the repo (overview, recent activity, health checks) on demand.
license: MIT
metadata:
  author: CesarBenavides777
  version: "1.0.0"
user-invocable: true
---

# Project Summary Skill

Generate a comprehensive summary of the current project state.

## Instructions

When the user invokes `/project-summary`, gather and present the following information:

### 1. Project Overview

- Read `package.json` for project name, version, and dependencies
- Summarize: TypeScript MCP server for Monarch Money personal finance data

### 2. Recent Activity

```bash
# Recent commits (last 10)
git log --oneline -10

# Current branch and status
git branch --show-current
git status --short
```

### 3. Project Structure

```bash
# Source files
ls src/
ls src/tools/ src/analysis/ src/mcp/ src/oauth/ src/middleware/ src/monarch/
```

### 4. Health Checks

```bash
# Type check
bunx tsc --noEmit

# Tests
bun test

# Live server (if deployed)
curl -s https://monarch-money-mcp.fly.dev/health
```

### 5. Key Stats

- Total MCP tools registered
- Total analysis functions
- Test count and pass rate
- Last deployment status

### 6. Key Documentation

- `CLAUDE.md` - Project configuration and patterns
- `AGENTS.md` - Agent-facing documentation and API reference

## Output Format

```
# Monarch Money MCP - Project Summary

## Overview
- Version: [version from package.json]
- Tools: [count] MCP tools registered
- Analysis: [count] analysis functions
- Tests: [count] tests passing

## Current State
- Branch: [current branch]
- Status: [clean/dirty with X files]
- Last commit: [message]

## Recent Activity (Last 5 commits)
- [commit summaries]

## Source Structure
| Directory       | Purpose              | Files |
|----------------|----------------------|-------|
| src/tools/      | MCP tool handlers    | X     |
| src/analysis/   | Financial analysis   | X     |
| src/mcp/        | Server + transport   | X     |
| src/oauth/      | OAuth 2.1 flow       | X     |
| src/middleware/  | Rate limit, audit    | X     |
| src/monarch/    | API client wrapper   | X     |

## Deployment
- Fly.io: [health check result]
- CI: [last run status]
- Deploy: [last run status]

## Key Commands
- `bun run dev` - Start with hot reload
- `bun run start:stdio` - stdio mode (Claude Desktop)
- `bun run start:http` - HTTP mode (Custom Connector)
- `bunx tsc --noEmit` - Type check
- `bun test` - Run tests
```

## Notes

- Keep the summary concise but informative
- Highlight any uncommitted work
- Note any failing builds or tests
