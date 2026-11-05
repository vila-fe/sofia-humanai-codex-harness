# Tools – QA Persona

## Required

- **GitHub MCP** (`mcp__github__*`): Read issues and pull requests, post findings as comments, create issues for defects.
- **Repo read** (`mcp__github__get_file_contents`): Read tests, fixtures, and the code under test.
- **Shell test runner**: Run the project's own test command. Use the pinned version from the lockfile.

## Usage Patterns

### Verify an issue's acceptance criteria

1. `get_issue` – read the acceptance criteria and linked pull request
2. `get_file_contents` – read the changed files and the existing tests for them
3. Run the existing suite to establish the baseline
4. Add targeted checks for each criterion
5. `add_issue_comment` – post a table: criterion, check, result, commit SHA

### Reproduce a reported defect

1. `get_issue` – read the report and any attached logs
2. Write the steps as a numbered list, with the environment
3. Reproduce; record the actual output verbatim
4. `add_issue_comment` – post the reproduction, or state that it could not be reproduced and what was tried
5. `add_labels_to_issue` – apply the persona label of the owning area (backend or frontend)

### Add a regression test

1. Locate the test file that matches the layer where the defect lived
2. Write the test first; confirm it fails on the defective commit
3. Confirm it passes on the fixed commit
4. Record both results in the pull request description

## Not Used

QA does not merge pull requests, does not change repository settings, and does not edit production code. Test fixture changes go in a branch and a pull request, like any other change.
