# Auto Review Documentation Workflow

This workflow automatically reviews documentation changes and can be triggered in two ways:

## Triggers

### 1. Automatic Trigger
- **Push to main branch**: The workflow automatically runs when changes are pushed to the `main` branch

### 2. Manual Trigger (workflow_dispatch)
- **Manual execution**: You can manually trigger this workflow from the GitHub Actions UI
- **Any branch**: Can be run on any branch or commit, not just `main`
- **On-demand review**: Useful for reviewing documentation changes before merging

## How to Run Manually

1. Go to the **Actions** tab in your GitHub repository
2. Select **Auto Review Documentation** from the workflow list
3. Click **Run workflow**
4. Choose the branch you want to run the workflow on
5. Click **Run workflow** to start the manual execution

## Benefits of workflow_dispatch

- **Flexibility**: Run documentation reviews on feature branches before merging
- **Testing**: Test workflow changes without needing to push to main
- **On-demand reviews**: Review documentation at any time, not just on push events
- **Quality assurance**: Ensure documentation quality across all branches

## Workflow Configuration

```yaml
on:
  push:
    branches:
      - main
  workflow_dispatch:
```

The `workflow_dispatch` trigger enables manual runs from the Actions tab, allowing you to select any branch or commit for review.