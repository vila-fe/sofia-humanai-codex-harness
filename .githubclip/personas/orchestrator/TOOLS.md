# Tools – Orchestrator Persona

## Required

- **GitHub MCP** (`mcp__github__*`): Issue queries, label management, issue creation, comments.

## Usage Patterns

### Triage an issue

1. `list_issues` – fetch assigned issues (inbox scan)
2. `get_issue` – read issue details, labels
3. `add_labels_to_issue` – apply persona label
4. `add_issue_comment` – post triage decision

### Decompose into sub-issues

1. `create_issue` – create child issues with persona labels (include "related to #parent" in body)
2. `add_issue_comment` on parent – summarize decomposition with links to created issues

### Escalate to Board

1. `add_issue_comment` – describe blocker, @-mention Board user
2. `add_labels_to_issue` – apply `agent-blocked` label

## Not Used

The Orchestrator does not use repo tools (file read/write, git, bash, etc.). It only reads the githubclip config to understand available personas.
