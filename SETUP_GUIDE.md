# Quick Setup Guide

This guide will help you set up OpenAPI analysis in your GitHub repository in just a few steps.

## Option 1: Use Our Workflow Templates (Recommended)

### Step 1: Choose a Template

We provide three ready-to-use workflow templates:

- **`template-single-file.yml`** - For analyzing a single OpenAPI file
- **`template-repository.yml`** - For analyzing all OpenAPI files in your repository
- **`template-comprehensive.yml`** - Advanced workflow with multiple analysis types

### Step 2: Copy the Template

1. Go to the [workflow templates directory](.github/workflows/)
2. Copy the template file you want to use
3. Create a new file in your repository at `.github/workflows/openapi-analysis.yml`
4. Paste the template content

### Step 3: Customize (Optional)

You can customize the workflow by:

- **Changing triggers**: Modify the `on:` section to run on different events
- **Changing branches**: Update the `branches:` list to run on your preferred branches
- **Adding inputs**: Add custom inputs for manual workflow dispatch

### Step 4: Commit and Push

```bash
git add .github/workflows/openapi-analysis.yml
git commit -m "Add OpenAPI analysis workflow"
git push
```

The workflow will now run automatically on pushes and pull requests!

## Option 2: Create Your Own Workflow

If you prefer to create your own workflow, here's a minimal example:

```yaml
name: OpenAPI Analysis
on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  analyze:
    runs-on: ubuntu-latest
    steps:
    - name: Checkout code
      uses: actions/checkout@v4
      
    - name: Analyze OpenAPI Files
      uses: ApyGuard/apyguard_openapi_analysis@main
      with:
        repository: ${{ github.repository }}
        github_token: ${{ secrets.GITHUB_TOKEN }}
```

## What Happens Next?

Once you've set up the workflow:

1. **Automatic Analysis**: The workflow will run on every push and pull request
2. **PR Comments**: Analysis results will be posted as comments on pull requests
3. **Artifacts**: Detailed reports will be available as workflow artifacts
4. **Notifications**: You'll get notifications about any issues found

## Customization Options

### For Single File Analysis

If you want to analyze a specific OpenAPI file:

```yaml
- name: Analyze OpenAPI File
  uses: ApyGuard/apyguard_openapi_analysis@main
  with:
    spec_url: 'https://api.example.com/openapi.json'
```

### For External Repository Analysis

To analyze another repository:

```yaml
- name: Analyze External Repository
  uses: ApyGuard/apyguard_openapi_analysis@main
  with:
    repository: 'owner/repository-name'
    github_token: ${{ secrets.GITHUB_TOKEN }}
```

### For Manual Triggers

Add manual workflow dispatch:

```yaml
on:
  workflow_dispatch:
    inputs:
      repository:
        description: 'Repository to analyze'
        required: true
        default: 'github/rest-api-description'
```

## Troubleshooting

### Common Issues

1. **Workflow not running**: Make sure the file is in `.github/workflows/` directory
2. **Permission errors**: Ensure the workflow has the necessary permissions
3. **Token issues**: For private repositories, make sure `GITHUB_TOKEN` is available

### Getting Help

- Check the [main README](README.md) for detailed documentation
- Open an [issue](https://github.com/ApyGuard/openapi_analyzer/issues) for bugs
- Start a [discussion](https://github.com/ApyGuard/openapi_analyzer/discussions) for questions

## Examples

### Example 1: Basic Repository Analysis

```yaml
name: OpenAPI Analysis
on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  analyze:
    runs-on: ubuntu-latest
    steps:
    - name: Checkout code
      uses: actions/checkout@v4
      
    - name: Analyze OpenAPI Files
      uses: ApyGuard/apyguard_openapi_analysis@main
      with:
        repository: ${{ github.repository }}
        github_token: ${{ secrets.GITHUB_TOKEN }}
        output_format: 'summary'
```

### Example 2: Single File Analysis with PR Comments

```yaml
name: OpenAPI Analysis
on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  analyze:
    runs-on: ubuntu-latest
    steps:
    - name: Checkout code
      uses: actions/checkout@v4
      
    - name: Analyze OpenAPI File
      id: analyze
      uses: ApyGuard/apyguard_openapi_analysis@main
      with:
        spec_url: 'https://api.example.com/openapi.json'
        
    - name: Comment on PR
      if: github.event_name == 'pull_request'
      uses: actions/github-script@v7
      with:
        script: |
          const analysis = JSON.parse('${{ steps.analyze.outputs.analysis }}');
          const suggestions = analysis.suggestions || [];
          
          if (suggestions.length > 0) {
            const comment = `## 🔍 OpenAPI Analysis Results\n\n` +
              `**Valid**: ${analysis.is_valid ? '✅' : '❌'}\n\n` +
              `### 📋 Suggestions (${suggestions.length}):\n\n` +
              suggestions.map(s => `- ${s}`).join('\n');
              
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: comment
            });
          }
```

That's it! Your OpenAPI analysis is now set up and ready to help improve your API documentation quality.
