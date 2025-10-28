# OpenAPI Analyzer

A comprehensive GitHub Action that analyzes OpenAPI specifications and provides detailed feedback on best practices, validation, and documentation quality. Supports both single file analysis and entire repository scanning.

## Features

### 🔍 **Core Analysis**

- **Comprehensive Validation**: Validates OpenAPI specs against general best practices and checks for schema validity.
- **Detailed Reporting**: Provides actionable suggestions for improvement grouped by category (e.g., Security, Performance).
- **Version-Aware**: Supports OpenAPI 3.x and Swagger 2.0 (v2) specifications. (v2 specs are automatically normalized to a v3-like structure for consistent analysis).

### 🛡️ **Advanced Security Analysis**

- **OWASP API Security Top 10 Checks**: Implementation of key OWASP API Security Top 10 checks:
  - **API2:2019** - Broken User Authentication: Validates security schemes for missing authentication, insecure API keys in query parameters, basic auth usage, missing OAuth2 flows, and undefined bearer token formats
  - **API3:2019** - Excessive Data Exposure: Scans response schemas for sensitive field patterns (password, secret, ssn, credit card, email, etc.) and flags potential data leaks
  - **API4:2019** - Lack of Resources & Rate Limiting: Checks for missing rate limiting headers (rate-limit, quota, throttle) in API responses to prevent abuse
  - **API5:2019** - Broken Function Level Authorization: Identifies privileged operations (admin, delete, update, create, manage, config) without explicit security requirements
  - **API6:2019** - Mass Assignment: Detects request body schemas that allow additional properties, which could enable mass assignment attacks
  - **API7:2019** - Security Misconfiguration: Flags HTTP URLs (non-localhost), overly permissive CORS configurations allowing all origins (\*)
  > **Note**: API1:2019 (Broken Object Level Authorization), API8:2019 (Injection), API9:2019 (Improper Assets Management), and API10:2019 (Insufficient Logging & Monitoring) checks are not fully covered in this implementation. For comprehensive security analysis and further investigation of all OWASP checks, visit [apyguard.com](https://apyguard.com).

### ⚡ **Performance & Optimization**

- **Response Complexity Analysis**: Calculates schema complexity to flag potentially large responses that may need pagination or field selection.
- **Caching Recommendations**: Checks for and recommends appropriate caching headers for `GET` operations.
- **Rate Limiting Analysis**: Checks for and recommends rate limiting headers in responses.

### 🏗️ **API Design & Patterns**

- **RESTful Compliance**: Analyzes paths for CRUD operation completeness per resource.
- **HTTP Method Usage**: Validates proper method selection and suggests documenting idempotent behavior for `PUT`/`DELETE`.
- **Naming Conventions**: Checks for consistent path and property naming styles.

### 📊 **Advanced Analytics**

- **Complexity Scoring**: Calculates an API **Complexity Score** (0-1000+) based on paths, operations, and schema nesting.
- **Maintainability Score**: Derives a **Maintainability Score** (0-100 scale).

### 🏛️ **API Governance**

- **Versioning Strategy**: Checks for versioning information in the `info` block and server URLs.
- **Operation ID Check**: Ensures all operation IDs are present and unique.
- **Deprecation Management**: Identifies deprecated operations and suggests adding migration documentation.
- **Naming Consistency**: Analyzes path naming styles and method consistency across the API.

### 🛡️ **Compliance & Standards**

- **GDPR Compliance**: Identifies endpoints handling personal data and recommends GDPR adherence.
- **Industry Compliance**: Checks for healthcare (HIPAA) and payment (PCI-DSS) related endpoints and recommends compliance measures.
- **Accessibility**: Analyzes API design for accessibility considerations and inclusive design patterns.

### 📈 **Monitoring & Observability**

- **Health Check Detection**: Identifies missing health check endpoints (/health, /status, /ping) for system monitoring.
- **Metrics Endpoint Recommendations**: Suggests adding metrics endpoints for Prometheus-style monitoring.
- **Error Response Validation**: Ensures proper error response definitions (4xx, 5xx) for better observability.

### 🏢 **Repository Analysis**

- **Multi-File Support**: Analyzes multiple OpenAPI files found within a repository.
- **Auto-Discovery**: Automatically finds OpenAPI files using common patterns.
- **Repository Metadata**: Retrieves and reports GitHub repository statistics like stars and forks.

---

## Quick Start

### Example Usage

The example below shows how to run the analysis, display core metrics, and automatically comment on a Pull Request with the top suggestions.

```yaml
name: OpenAPI Analysis

on:
  push:
    branches: [main, develop]
    paths:
      - "**/*.json"
      - "**/*.yaml"
      - "**/*.yml"
  pull_request:
    branches: [main, develop]
    paths:
      - "**/*.json"
      - "**/*.yaml"
      - "**/*.yml"
  workflow_dispatch:

jobs:
  analyze-openapi:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Analyze OpenAPI
        id: analyze
        uses: ApyGuard/apyguard_openapi_analysis@v1.0.5
        with:
          # Change this to your OpenAPI file path
          file: your-openapi-file.json
          output_format: json

      - name: Display Results
        run: |
          echo "OpenAPI Analysis Results:"
          echo "========================="
          echo "Valid: ${{ steps.analyze.outputs.is_valid }}"
          echo "Suggestions: ${{ steps.analyze.outputs.suggestions_count }}"
          echo "Operations: ${{ steps.analyze.outputs.operations_count }}"
          echo "Paths: ${{ steps.analyze.outputs.paths_count }}"
          echo "Schemas: ${{ steps.analyze.outputs.schemas_count }}"

      - name: Comment on PR
        if: github.event_name == 'pull_request'
        uses: actions/github-script@v7
        with:
          script: |
            const analysis = JSON.parse('${{ steps.analyze.outputs.analysis }}');
            const comment = `## 🔍 OpenAPI Analysis Results

            **Valid**: ${analysis.is_valid ? '✅' : '❌'}
            **Total Suggestions**: ${analysis.suggestions ? Object.values(analysis.suggestions).reduce((total, suggestions) => total + suggestions.length, 0) : 0}
            **Operations**: ${analysis.summary ? analysis.summary.operations_count : 0}
            **Paths**: ${analysis.summary ? analysis.summary.paths_count : 0}
            **Schemas**: ${analysis.summary ? analysis.summary.schemas_count : 0}

            ${analysis.suggestions && Object.keys(analysis.suggestions).length > 0 ? 
              Object.entries(analysis.suggestions).map(([category, suggestions]) => 
                `### ${category} (${suggestions.length} issues)\n\n${suggestions.slice(0, 3).map(s => `- ${s}`).join('\n')}${suggestions.length > 3 ? `\n- ... and ${suggestions.length - 3} more` : ''}\n`
              ).join('\n') : 
              '### ✅ No suggestions found! Your OpenAPI specification looks great! 🎉'
            }`;
              
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: comment
            });
```

### Option 1: Using a Local File (Recommended)

To analyze a file checked into your repository, set the `file` input.

```yaml
- name: Analyze OpenAPI
  uses: ApyGuard/apyguard_openapi_analysis@main
  with:
    file: api/openapi.yaml # Specify your file path here
```

### Option 2: Analyze from URL

To analyze a specification hosted externally:

```yaml
- name: Analyze OpenAPI from URL
  uses: ApyGuard/apyguard_openapi_analysis@main
  with:
    spec_url: "https://api.example.com/v1/openapi.json"
    output_format: json
```

### Option 3: Analyze Entire Repository

To automatically discover and analyze all OpenAPI files (`*.json`, `*.yaml`, `*.yml`) in a repository:

```yaml
- name: Analyze Repository OpenAPI Files
  uses: ApyGuard/apyguard_openapi_analysis@main
  with:
    repository: ${{ github.repository }}
    github_token: ${{ secrets.GITHUB_TOKEN }} # Required for private repos or higher limits
    output_format: summary
```

---

## Outputs and Metrics

The action provides granular outputs for integration with status checks, dashboards, and advanced reporting. All output names are available in the `action.yml` file.

| Output Name                     | Description                                          |
| :------------------------------ | :--------------------------------------------------- |
| `analysis`                      | Complete analysis results as JSON string             |
| `is_valid`                      | Boolean indicating if the spec is structurally valid |
| `suggestions_count`             | **Total** number of suggestions found                |
| **`operations_count`**          | Number of operations in the spec                     |
| **`paths_count`**               | Number of paths in the spec                          |
| **`schemas_count`**             | Number of schemas in the spec                        |
| **`complexity_score`**          | API complexity score (0-1000+)                       |
| **`maintainability_score`**     | API maintainability score (0-100)                    |
| `security_issues`               | Count of security-related suggestions                |
| `performance_issues`            | Count of performance-related suggestions             |
| `design_pattern_issues`         | Count of design pattern suggestions                  |
| `versioning_issues`             | Count of versioning-related suggestions              |
| `documentation_issues`          | Count of documentation quality suggestions           |
| `compliance_issues`             | Count of compliance-related suggestions              |
| `testing_recommendations`       | Count of testing strategy suggestions                |
| `monitoring_recommendations`    | Count of monitoring/observability suggestions        |
| `code_generation_opportunities` | Count of code generation suggestions                 |
| `governance_issues`             | Count of API governance suggestions                  |
| `repository_name`               | Repository name (when analyzing repositories)        |
| `repository_full_name`          | Full repository name (owner/repo)                    |
| `repository_url`                | Repository URL                                       |
| `repository_stars`              | Number of repository stars (for repo analysis)       |
| `repository_forks`              | Number of repository forks (for repo analysis)       |
| `user_actor`                    | GitHub username who triggered the action             |
| `user_repository`               | Repository where the action was triggered            |
| `user_workflow`                 | Workflow name that triggered the action              |
| `user_run_id`                   | Unique run ID for this action execution              |

---

## Example Output on PR Comment

The PR comment example uses a template that categorizes results and provides a summary:

```markdown
## 🔍 OpenAPI Analysis Results

**Valid**: ✅
**Total Suggestions**: 5
**Operations**: 10
**Paths**: 2
**Schemas**: 3

### 📋 Analysis Categories

- **Security Issues**: 1
- **Performance Issues**: 2
- **Design Pattern Issues**: 1
- **Versioning Issues**: 0
- **Documentation Issues**: 2
- **Compliance Issues**: 0
- **Testing Recommendations**: 1
- **Monitoring Recommendations**: 1
- **Code Generation Opportunities**: 0
- **Governance Issues**: 0
- **Complexity Score**: 85
- **Maintainability Score**: 87.5/100

### 📋 Top Suggestions:

- Operation GET /users missing summary.
- Operation GET /users should include caching headers (Cache-Control, ETag, Last-Modified) for better performance.
- ID-based endpoint GET /users/{id} should have explicit security requirements to prevent unauthorized access to other users' data.
- ... and 2 more
```

---

## Technical Requirements

### **Runtime Environment**

- **Python Version**: 3.11+ (containerized)
- **Dependencies**:
  - `requests` - HTTP client for API calls
  - `PyYAML` - YAML parsing support
  - `openapi-spec-validator` - OpenAPI specification validation

### **GitHub Actions Integration**

- **Environment Variables**: Automatically reads GitHub Actions inputs:
  - `INPUT_SPEC_URL` - OpenAPI specification URL
  - `INPUT_REPOSITORY` - GitHub repository (owner/repo)
  - `INPUT_FILE` - Local file path
  - `INPUT_GITHUB_TOKEN` - GitHub token for private repos
  - `INPUT_OUTPUT_FORMAT` - Output format (json/summary)
- **Context Variables**: Provides GitHub Actions context:
  - `GITHUB_ACTIONS` - Detects GitHub Actions environment
  - `GITHUB_TOKEN` - Default GitHub token

### **Supported File Formats**

- **OpenAPI Specifications**: 3.0+, 3.1+
- **Swagger Specifications**: 2.0 (automatically normalized)
- **File Extensions**: `.json`, `.yaml`, `.yml`
- **Auto-Discovery Patterns**: `openapi.*`, `swagger.*`, `api.*`, `spec.*`

---

## Support and Documentation

| Area                        | Link / Contact                                                                                                            |
| :-------------------------- | :------------------------------------------------------------------------------------------------------------------------ |
| **General Issues**          | [GitHub Issues](https://github.com/ApyGuard/openapi_analyzer/issues)                                                      |
| **Discussions & Questions** | [GitHub Discussions](https://github.com/ApyGuard/openapi_analyzer/discussions)                                            |
| **Security Reporting**      | Use [GitHub Security Advisories](https://github.com/ApyGuard/openapi_analyzer/security) or email `security@apyguard.com`. |
| **Privacy Policy**          | See the [PRIVACY.md](PRIVACY.md) file for details on data collection and usage.                                           |

---

## License

This project is licensed under the **MIT License**.

Copyright (c) 2025 ApyGuard.

---

## Changelog

### v1.0.5 - 2025-09-27

- 🚀 **Latest Release**: Enhanced OpenAPI specification analysis
- 🛡️ **Security**: Improved security checks and OWASP API Security Top 10 implementation
- 📚 **Documentation**: Better documentation quality assessment
- ✅ **Validation**: Comprehensive best practice validation
- 🔧 **Docker**: Updated Docker image with latest improvements

### v1.0.4

- 🔧 **Bug Fixes**: Various stability improvements
- 📊 **Analytics**: Enhanced complexity and maintainability scoring

### v1.0.3

- 🛡️ **Security**: Enhanced OWASP API Security Top 10 checks
- 📈 **Performance**: Improved performance analysis

### v1.0.2

- 🔧 **Docker Fix**: Fixed Docker container to work correctly with GitHub Actions working directory.
- 🔧 **Path Resolution**: Improved file path handling for local OpenAPI files.
- 🔧 **Container Stability**: Enhanced Docker container reliability across different environments.
- 📚 **Documentation**: Updated README with comprehensive feature documentation and accurate output descriptions.
- 🛡️ **Security**: Enhanced OWASP API Security Top 10 implementation with all 10 checks.
- 📊 **Analytics**: Added comprehensive analysis categories and improved scoring algorithms.

### v1.0.1

- 🆕 **Repository Analysis**: Analyze entire repositories for OpenAPI files.
- 🆕 **Auto-Discovery**: Automatically finds OpenAPI files in repositories.
- 🆕 **Output Formats**: JSON and summary output formats.
- 🆕 **Compliance Checks**: Added GDPR, HIPAA, and PCI-DSS compliance analysis.
- 🆕 **Advanced Analytics**: Implemented complexity and maintainability scoring.

### v1.0.0 - 2025-01-XX

- Initial release of OpenAPI Analyzer.
- Basic OpenAPI specification validation.
- Comprehensive best practice checks.
- OWASP API Security Top 10 analysis.
- Performance and optimization recommendations.

---

Made with ❤️ by ApyGuard
