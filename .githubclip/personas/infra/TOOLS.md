# Tools – Infra Persona

## Required

- **GitHub MCP** (`mcp__github__*`): Issue comments, label updates, branch and pull request creation, reading workflow files.
- **Repo read/write via branch** (`mcp__github__create_or_update_file`, `mcp__github__push_files`): Only on a feature branch, never on the default branch.

## Usage Patterns

### Change a CI workflow

1. `get_file_contents` – read `.github/workflows/*` and the affected scripts
2. `create_branch` – create `infra/<short-slug>` from the default branch
3. `create_or_update_file` – commit the change on that branch, with the required attribution trailer
4. `create_pull_request` – open the PR with the rollback step and the blast radius in the body
5. `add_issue_comment` – link the PR on the tracking issue

### Investigate a failed pipeline

1. `list_commits` / `get_file_contents` – identify the commit and the workflow file
2. Reproduce locally with the same pinned tool versions where possible
3. `add_issue_comment` – post the root cause and the fix plan; move the issue to In Progress

### Add an environment variable

1. Add the variable **name** and its purpose to the environment document
2. Never add the value to the repo; state where the value is stored (for example, the repository or organization secret store)
3. Note the rollback: remove the name and the references in the same PR

## Not Used

Infra does not merge pull requests and does not change repository settings, branch protection, or collaborator access. Those require a human owner.
