# OpenAPI Analyzer

A GitHub Action that analyzes OpenAPI specifications and provides comprehensive feedback on best practices, validation, and documentation quality.

## Features

- 🔍 **Comprehensive Analysis**: Validates OpenAPI specs against best practices
- 📊 **Detailed Reporting**: Provides actionable suggestions for improvement
- 🛡️ **Security Checks**: Identifies missing security definitions and authentication
- 📝 **Documentation Quality**: Checks for missing descriptions, examples, and proper schemas
- 🚀 **Easy Integration**: Simple one-step setup in your GitHub workflows

## Usage

### Basic Usage

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
      uses: actions/checkout@v4
      
    - name: Analyze OpenAPI Specification
      uses: ApyGuard/openapi_analyzer@v1
      with:
        spec_url: 'https://api.example.com/openapi.json'
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
      uses: actions/checkout@v4
      
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
| `spec_url` | URL to the OpenAPI specification (JSON or YAML) | Yes | - |

## Outputs

| Output | Description |
|--------|-------------|
| `analysis` | JSON string containing the complete analysis results |
| `is_valid` | Boolean indicating if the spec is valid |
| `suggestions_count` | Number of suggestions found |
| `operations_count` | Number of operations in the spec |
| `paths_count` | Number of paths in the spec |
| `schemas_count` | Number of schemas in the spec |

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

## Requirements

- OpenAPI 3.0+ or Swagger 2.0 specifications
- Publicly accessible URL to the specification
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

### v1.0.0
- Initial release
- Basic OpenAPI validation
- Comprehensive best practice checks
- Security analysis
- Documentation quality assessment

---

Made with ❤️ by [ApyGuard](https://github.com/ApyGuard)