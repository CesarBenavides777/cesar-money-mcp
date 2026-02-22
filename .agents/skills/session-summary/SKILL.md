---
name: session-summary
description: Produce a concise summary of the current working session (what changed, decisions, next steps).
license: MIT
metadata:
  author: CesarBenavides777
  version: "1.0.0"
user-invocable: true
---

# Session Summary

Use at the end of a working block to capture what happened and what to do next.

## Checklist

- Review `git status` and `git log -1 --stat` to list changes.
- Note tasks addressed (PR links, issue numbers) and decisions made.
- Call out blockers or follow-ups.
- Provide next steps with owners and due dates when known.

## Output Template

```
What we did:
- ...
Decisions:
- ...
Blockers:
- ...
Next up:
- ...
```
