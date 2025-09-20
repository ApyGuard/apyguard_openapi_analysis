# OpenAPI Analyzer

A comprehensive GitHub Action that analyzes OpenAPI specifications and provides detailed feedback on best practices, validation, and documentation quality. Supports both single file analysis and entire repository scanning.

## Features

- 🔍 **Comprehensive Analysis**: Validates OpenAPI specs against best practices
- 📊 **Detailed Reporting**: Provides actionable suggestions for improvement
- 🛡️ **Security Checks**: Identifies missing security definitions and authentication
- 📝 **Documentation Quality**: Checks for missing descriptions, examples, and proper schemas
- 🚀 **Easy Integration**: Simple one-step setup in your GitHub workflows
- 🏢 **Repository Analysis**: Analyze entire repositories for OpenAPI files
- 🔍 **Auto-Discovery**: Automatically finds OpenAPI files in repositories
- 📈 **Repository Metadata**: Get repository information and statistics

## Usage

### Single OpenAPI File Analysis

```yaml
name: Analyze OpenAPI Spec
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
      uses: actions/checkout@v3
      
    - name: Analyze OpenAPI Specification
      uses: ApyGuard/openapi_analyzer@v1
      with:
        spec_url: 'https://api.example.com/openapi.json'
```

### Repository Analysis

```yaml
name: Analyze Repository OpenAPI
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
      uses: actions/checkout@v3
      
    - name: Analyze Repository OpenAPI Files
      uses: ApyGuard/openapi_analyzer@v1
      with:
        repository: ${{ github.repository }}
        github_token: ${{ secrets.GITHUB_TOKEN }}
        output_format: 'summary'
```

### Analyze External Repository

```yaml
name: Analyze External Repository
on:
  workflow_dispatch:
    inputs:
      repository:
        description: 'Repository to analyze (owner/repo)'
        required: true

jobs:
  analyze:
    runs-on: ubuntu-latest
    steps:
    - name: Analyze External Repository
      uses: ApyGuard/openapi_analyzer@v1
      with:
        repository: ${{ github.event.inputs.repository }}
        github_token: ${{ secrets.GITHUB_TOKEN }}
```

### Advanced Usage

```yaml
name: API Quality Check
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
      uses: actions/checkout@v3
      
    - name: Analyze OpenAPI Specification
      id: analyze
      uses: ApyGuard/openapi_analyzer@v1
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
              `**Status**: ${analysis.status}\n` +
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

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `spec_url` | URL to the OpenAPI specification (JSON or YAML) | No | - |
| `repository` | GitHub repository to analyze (format: owner/repo) | No | - |
| `github_token` | GitHub token for private repositories or higher rate limits | No | - |
| `output_format` | Output format (json or summary) | No | json |

**Note**: Either `spec_url` or `repository` must be provided.

## Outputs

| Output | Description |
|--------|-------------|
| `analysis` | JSON string containing the complete analysis results |
| `is_valid` | Boolean indicating if the spec is valid |
| `suggestions_count` | Number of suggestions found |
| `operations_count` | Number of operations in the spec |
| `paths_count` | Number of paths in the spec |
| `schemas_count` | Number of schemas in the spec |
| `repository_name` | Repository name (when analyzing repositories) |
| `repository_full_name` | Full repository name (owner/repo) |
| `repository_url` | Repository URL |
| `repository_stars` | Number of repository stars |
| `repository_forks` | Number of repository forks |

## What the Analyzer Checks

### 📋 Basic Validation
- ✅ Valid JSON/YAML format
- ✅ OpenAPI specification compliance
- ✅ Required fields (title, description, version)

### 🔐 Security Analysis
- 🔒 Global security requirements
- 🔒 Operation-level security definitions
- 🔒 Authentication scheme documentation

### 📝 Documentation Quality
- 📖 Operation descriptions and summaries
- 📖 Parameter descriptions
- 📖 Response descriptions and schemas
- 📖 Schema definitions and types

### 🛠️ Best Practices
- 🎯 Unique operation IDs
- 🎯 Proper HTTP status codes
- 🎯 Server definitions
- 🎯 Request/response content types
- 🎯 Schema composition and inheritance

## Example Output

### Single File Analysis
```json
{
  "status": "success",
  "is_valid": true,
  "summary": {
    "openapi_version": "3.0.0",
    "paths_count": 5,
    "operations_count": 12,
    "schemas_count": 8
  },
  "suggestions": [
    "Operation GET /users missing operationId.",
    "Parameter userId in path of GET /users/{userId} missing description.",
    "Response 200 of GET /users missing description.",
    "Schema User missing description."
  ]
}
```

### Repository Analysis
```json
{
  "status": "success",
  "repository": {
    "name": "my-api",
    "full_name": "owner/my-api",
    "description": "My API project",
    "url": "https://github.com/owner/my-api",
    "language": "TypeScript",
    "stars": 150,
    "forks": 25
  },
  "openapi_files": [
    {
      "file_info": {
        "name": "openapi.json",
        "path": "docs/api/openapi.json",
        "url": "https://github.com/owner/my-api/blob/main/docs/api/openapi.json",
        "size": 15420
      },
      "status": "success",
      "is_valid": true,
      "summary": {
        "openapi_version": "3.0.0",
        "paths_count": 5,
        "operations_count": 12,
        "schemas_count": 8
      },
      "suggestions": [
        "Operation GET /users missing operationId.",
        "Parameter userId in path of GET /users/{userId} missing description."
      ]
    }
  ]
}
```

## Requirements

- OpenAPI 3.0+ or Swagger 2.0 specifications
- For single file analysis: Publicly accessible URL to the specification
- For repository analysis: Public repository or GitHub token for private repositories
- Valid JSON or YAML format

## Support

For support and questions, please use the GitHub Issues or Discussions.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- 📧 **Issues**: [GitHub Issues](https://github.com/ApyGuard/openapi_analyzer/issues)
- 📖 **Documentation**: [GitHub Wiki](https://github.com/ApyGuard/openapi_analyzer/wiki)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/ApyGuard/openapi_analyzer/discussions)

## Changelog

### v2.0.0
- 🆕 **Repository Analysis**: Analyze entire repositories for OpenAPI files
- 🆕 **Auto-Discovery**: Automatically finds OpenAPI files in repositories
- 🆕 **Repository Metadata**: Get repository information and statistics
- 🆕 **Multiple File Support**: Analyze multiple OpenAPI files in one run
- 🆕 **Enhanced CLI**: Support for repository analysis via command line
- 🆕 **GitHub Token Support**: Support for private repositories
- 🆕 **Output Formats**: JSON and summary output formats
- 🆕 **Rate Limit Management**: Built-in GitHub API rate limit handling

### v1.0.0
- Initial release
- Basic OpenAPI validation
- Comprehensive best practice checks
- Security analysis
- Documentation quality assessment

---

Made with ❤️ by [ApyGuard](https://github.com/ApyGuard)