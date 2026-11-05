# Tools – CEO Persona

## Required

- **GitHub MCP** (`mcp__github__*`): Issue management, comments, issue creation, label and status updates.

## Usage Patterns

### Make a scope decision

1. `get_issue` – read the issue and all context
2. `list_issue_comments` – review discussion and prior decisions
3. `add_issue_comment` – post the decision with rationale
4. `add_labels_to_issue` / `remove_label_from_issue` – update priority or persona labels

### Review a decomposition

1. `get_issue` – read the parent issue
2. `list_issues` – check related issues
3. `create_issue` – create sub-issues with correct labels and "Related to #parent" body
4. `add_issue_comment` – post the approved breakdown

### Communicate with the Board

1. `add_issue_comment` – post a status summary or recommendation
2. Include @Board-User-Name for visibility

### Coordinate cross-cutting work

1. `list_issues` – find related issues across personas
2. `add_issue_comment` – post coordination notes on each relevant issue
3. `add_labels_to_issue` – update priorities to reflect sequencing decisions

## Not Used

The CEO does not use repo tools for implementation. If code investigation is needed to make a decision, request it from a worker persona rather than reading code directly.
