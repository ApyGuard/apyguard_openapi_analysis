# OpenAPI Analyzer

A comprehensive GitHub Action that analyzes OpenAPI specifications and provides detailed feedback on best practices, validation, and documentation quality. Supports both single file analysis and entire repository scanning.

## Features

### 🔍 **Core Analysis**
- **Comprehensive Validation**: Validates OpenAPI specs against best practices
- **Detailed Reporting**: Provides actionable suggestions for improvement
- **Version-Aware**: Supports OpenAPI 3.x and Swagger 2.0 (v2) specs
- **Easy Integration**: Simple one-step setup in your GitHub workflows

### 🛡️ **Advanced Security Analysis**
- **OWASP API Security Top 10**: Complete compliance checking
- **Authentication Analysis**: OAuth2, API keys, JWT token validation
- **Authorization Checks**: Function-level and object-level authorization
- **Data Exposure Analysis**: Identifies sensitive data exposure risks
- **Injection Vulnerability Detection**: SQL injection and XSS pattern detection
- **Security Misconfiguration**: HTTPS, CORS, and security header analysis

### ⚡ **Performance & Optimization**
- **Response Complexity Analysis**: Identifies overly complex response schemas
## Features

### 🔍 **Core Analysis**
- **Comprehensive Validation**: Validates OpenAPI specs against general best practices and checks for schema validity.
- **Detailed Reporting**: Provides actionable suggestions for improvement grouped by category (e.g., Security, Performance).
- **Version-Aware**: Supports OpenAPI 3.x and Swagger 2.0 (v2) specifications. (v2 specs are automatically normalized to a v3-like structure for consistent analysis).

### 🛡️ **Advanced Security Analysis**
- **OWASP API Security Top 10 Checks**: Identifies common vulnerabilities based on the Top 10 list.
- **Authentication Analysis**: Checks for proper definition of API keys, Basic, Bearer, and OAuth2 security schemes.
- **Authorization Checks**: Identifies privileged operations and ID-based endpoints lacking explicit security requirements.
- **Data Exposure Analysis**: Scans response schemas for sensitive data field names (e.g., `password`, `ssn`).

### ⚡ **Performance & Optimization**
- **Response Complexity Analysis**: Calculates schema complexity to flag potentially large responses that may need pagination or field selection.
- **Caching Recommendations**: Checks for and recommends appropriate caching headers (`Cache-Control`, `ETag`) for `GET` operations.
- **Rate Limiting Analysis**: Checks for and recommends rate limiting headers in responses.
- **Pagination Detection**: Identifies list operations that should support pagination parameters.

### 🏗️ **API Design & Patterns**
- **RESTful Compliance**: Analyzes paths for CRUD operation completeness per resource.
- **HTTP Method Usage**: Validates proper method selection (e.g., GET/DELETE should generally not have a request body) and suggests documenting idempotent behavior for `PUT`/`DELETE`.
- **Naming Conventions**: Checks for consistent path and property naming styles.

### 📊 **Advanced Analytics**
- **Complexity Scoring**: Calculates an API **Complexity Score** based on paths, operations, and schema nesting.
- **Maintainability Score**: Derives a **Maintainability Score** (0-100 scale) to provide an estimate of how easy the API is to maintain.

### 🛡️ **Compliance & Standards**
- **GDPR Check**: Identifies endpoints handling personal data and recommends GDPR adherence.
- **Industry Compliance**: Identifies healthcare (HIPAA) and payment (PCI-DSS) related endpoints and recommends compliance measures.

### 🧪 **Quality Assurance & Testing**
- **Test Scenario Recommendations**: Generates suggested test scenarios, including security and functional testing.
- **Testing Strategy**: Recommends implementing mock data generation, contract testing, and load testing.

### 📈 **Monitoring & Observability**
- **Health/Metrics Endpoints**: Checks for and recommends standard health check and metrics endpoints.
- **Logging Strategies**: Recommends implementing structured logging with correlation IDs and error tracking.

### 🏛️ **API Governance**
- **Versioning Strategy**: Checks for versioning information in the `info` block and server URLs.
- **Operation ID Check**: Ensures all operation IDs are present and unique.

### 🏢 **Repository Analysis**
- **Multi-File Support**: Analyzes multiple OpenAPI files found within a repository.
- **Auto-Discovery**: Automatically finds OpenAPI files using common patterns.
- **Repository Metadata**: Retrieves and reports GitHub repository statistics like stars and forks.

## Quick Start

### Example Usage

```yaml
name: OpenAPI Analysis

on:
  push:
    branches: [ main, develop ]
    paths:
      - '**/*.json'
      - '**/*.yaml'
      - '**/*.yml'
  pull_request:
    branches: [ main, develop ]
    paths:
      - '**/*.json'
      - '**/*.yaml'
      - '**/*.yml'
  workflow_dispatch:

jobs:
  analyze-openapi:
    runs-on: ubuntu-latest
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v4
      
    - name: Analyze OpenAPI
      id: analyze
      uses: ApyGuard/apyguard_openapi_analysis@main
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

### Option 1: Using the GitHub Action (Recommended)

The action is now fully tested and works reliably with all repository types. Add this workflow to your repository (`.github/workflows/openapi-analysis.yml`):

```yaml
name: OpenAPI Analysis

on:
  push:
    branches: [ main, develop ]
    paths:
      - '**/*.json'
      - '**/*.yaml'
      - '**/*.yml'
  pull_request:
    branches: [ main, develop ]
    paths:
      - '**/*.json'
      - '**/*.yaml'
      - '**/*.yml'
  workflow_dispatch:

jobs:
  analyze-openapi:
    runs-on: ubuntu-latest
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v4
      
    - name: Analyze OpenAPI
      id: analyze
      uses: ApyGuard/apyguard_openapi_analysis@main
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

### Option 2: Analyze from URL

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
    - uses: actions/checkout@v4
    - name: Analyze OpenAPI from URL
      uses: ApyGuard/apyguard_openapi_analysis@main
      with:
        spec_url: 'https://api.example.com/openapi.json'
        output_format: json
```

### Option 3: Analyze Repository

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
    - uses: actions/checkout@v4
    - name: Analyze Repository OpenAPI Files
      uses: ApyGuard/apyguard_openapi_analysis@main
      with:
        repository: ${{ github.repository }}
        github_token: ${{ secrets.GITHUB_TOKEN }}
        output_format: summary
```

## How to Use in Other Repositories

### 1. **Copy the Workflow**
Copy one of the workflow examples above to your repository's `.github/workflows/` directory.

### 2. **Customize the File Path**
Replace `your-openapi-file.json` with your actual OpenAPI file path:
```yaml
with:
  file: api/openapi.json  # Your OpenAPI file path
```

### 3. **Set Up Triggers**
Configure when the analysis should run:
```yaml
on:
  push:
    branches: [ main ]           # Run on pushes to main
    paths: [ '**/*.json' ]      # Only when JSON files change
  pull_request:
    branches: [ main ]          # Run on PRs to main
  workflow_dispatch:            # Allow manual triggering
```

### 4. **Commit and Push**
The workflow will run automatically when you push changes to your OpenAPI files.

## Workflow Templates

We provide ready-to-use workflow templates that you can copy to your repository:

### 📁 **Available Workflow Templates**

| Workflow Template | Purpose | Best For | Triggers | Input | Output |
|------------------|---------|----------|----------|-------|--------|
| **`analyze-single-openapi-file.yml`** | Analyze one OpenAPI file from URL | External APIs, single file analysis | Push, PR, Manual | OpenAPI URL | Analysis results with suggestions |
| **`analyze-repository-openapi-files.yml`** | Find and analyze all OpenAPI files in repository | Multi-file repositories, comprehensive analysis | Push, PR, Manual | Repository name | All files + repository metadata |
| **`analyze-openapi-advanced.yml`** | Advanced multi-type analysis with scheduling | Enterprise use, automated monitoring | Push, PR, Schedule, Manual | Analysis type | Reports + artifacts + PR comments |
| **`test-openapi-analyzer.yml`** | Test the analyzer in different scenarios | Development, debugging | Manual only | Test type | Test results and validation |

### 🚀 **Quick Setup with Templates**

1. **Copy a workflow template** from `.github/workflows/` to your repository's `.github/workflows/` directory
2. **Rename the file** to something like `openapi-analysis.yml`
3. **Customize the triggers** (branches, events) as needed
4. **Commit and push** - the workflow will run automatically

### 📋 **Template Comparison**

| Feature | Single File | Repository | Advanced |
|---------|-------------|------------|----------|
| **File Analysis** | ✅ One file | ✅ Multiple files | ✅ Multiple types |
| **URL Support** | ✅ Yes | ❌ No | ✅ Yes |
| **Local Files** | ❌ No | ❌ No | ✅ Yes |
| **Repository Metadata** | ❌ No | ✅ Yes | ✅ Yes |
| **Scheduled Runs** | ❌ No | ❌ No | ✅ Daily |
| **Report Generation** | ❌ No | ❌ No | ✅ Yes |
| **Artifact Upload** | ❌ No | ❌ No | ✅ Yes |
| **PR Comments** | ✅ Basic | ✅ Detailed | ✅ Advanced |
| **Manual Dispatch** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Complexity** | 🟢 Simple | 🟡 Medium | 🔴 Advanced |

## What This Workflow Does

### 🔍 **Analysis Features**
- **Validates** your OpenAPI specification
- **Counts** operations, paths, and schemas
- **Provides suggestions** for improvements
- **Checks** for missing documentation
- **Validates** security configurations
- **Reviews** response definitions

### 📊 **Outputs**
- **Valid**: Whether the spec is valid
- **Suggestions**: Number of improvement suggestions
- **Operations**: Number of API operations
- **Paths**: Number of API paths
- **Schemas**: Number of data schemas

### 🎯 **Triggers**
- **Push**: Runs when you push to main/develop branches
- **Pull Request**: Runs on PRs to main/develop branches
- **Manual**: Can be triggered manually via GitHub Actions UI
- **File Changes**: Only runs when OpenAPI files are modified

## Example Output

The workflow will generate a comment like this on your PRs:

```markdown
## 🔍 OpenAPI Analysis Results

**Valid**: ✅
**Suggestions**: 5
**Operations**: 10
**Paths**: 2
**Schemas**: 3

### 📋 Top Suggestions:

- Spec is missing an API title.
- No servers defined. Consider specifying servers for clarity.
- Operation GET /users missing security definition.
- POST operation /users should have requestBody.
- Operation POST /users missing security definition.

Detailed results are available in the workflow artifacts.
```

## Customization

### Change the File Path
Replace `your-openapi-file.json` with your actual OpenAPI file:

```yaml
- name: Run OpenAPI Analysis
  run: |
    python analyzer.py api/openapi.json > analysis-results.json
```

### Multiple Files
To analyze multiple OpenAPI files, create separate steps:

```yaml
- name: Analyze API v1
  run: |
    python analyzer.py api-v1.json > analysis-v1.json
    
- name: Analyze API v2  
  run: |
    python analyzer.py api-v2.json > analysis-v2.json
```

### Different File Formats
The analyzer supports both JSON and YAML:

```yaml
# For JSON files
python analyzer.py api.json

# For YAML files  
python analyzer.py api.yaml
```

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

## Advanced Usage

### Repository Analysis
Analyze all OpenAPI files in a repository:

```yaml
- name: Analyze Repository
  uses: ApyGuard/apyguard_openapi_analysis@main
  with:
    repository: ${{ github.repository }}
    github_token: ${{ secrets.GITHUB_TOKEN }}
    output_format: summary
```

### URL Analysis
Analyze OpenAPI specs from URLs:

```yaml
- name: Analyze from URL
  uses: ApyGuard/apyguard_openapi_analysis@main
  with:
    spec_url: 'https://api.example.com/openapi.json'
    output_format: json
```

### Custom Analysis Rules
You can modify the analyzer script to add custom validation rules by editing the `analyze_openapi_spec` function.

## Troubleshooting

### File Not Found Error
Make sure your OpenAPI file exists in the repository root or update the file path in the workflow.

### Permission Issues
Ensure the workflow has permission to read your OpenAPI files.

### Analysis Not Running
Check that your file has a `.json`, `.yaml`, or `.yml` extension and is in the repository.

### Docker Issues
The action uses Docker containers to ensure consistent execution across different environments. If you encounter Docker-related issues:

1. **Check GitHub Actions logs** for specific error messages
2. **Verify file paths** are correct relative to your repository root
3. **Ensure proper permissions** for the workflow to access your files
4. **Check network connectivity** if analyzing from URLs

The Docker container is configured to work with GitHub Actions' working directory (`/github/workspace`) and will automatically find your OpenAPI files.

## Requirements

- OpenAPI 3.0+ or Swagger 2.0 specifications (v2 is automatically normalized to v3-like structure)
- For single file analysis: Publicly accessible URL to the specification
- For repository analysis: Public repository or GitHub token for private repositories
- Valid JSON or YAML format

## Support

For support and questions:
- 📧 **Issues**: [GitHub Issues](https://github.com/ApyGuard/openapi_analyzer/issues)
- 📖 **Documentation**: [GitHub Wiki](https://github.com/ApyGuard/openapi_analyzer/wiki)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/ApyGuard/openapi_analyzer/discussions)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Changelog

### v1.0.2
- 🔧 **Docker Fix**: Fixed Docker container to work correctly with GitHub Actions working directory
- 🔧 **Path Resolution**: Improved file path handling for local OpenAPI files
- 🔧 **Container Stability**: Enhanced Docker container reliability across different environments
- ✅ **Verified Compatibility**: Tested with multiple repository types and file structures

### v1.0.1
- 🆕 **Repository Analysis**: Analyze entire repositories for OpenAPI files
- 🆕 **Auto-Discovery**: Automatically finds OpenAPI files in repositories
- 🆕 **Repository Metadata**: Get repository information and statistics
- 🆕 **Multiple File Support**: Analyze multiple OpenAPI files in one run
- 🆕 **Enhanced CLI**: Support for repository analysis via command line
- 🆕 **GitHub Token Support**: Support for private repositories
- 🆕 **Output Formats**: JSON and summary output formats
- 🆕 **Rate Limit Management**: Built-in GitHub API rate limit handling
- 🆕 **Local File Support**: Analyze local OpenAPI files in repositories

### v1.0.0
- Initial release
- Basic OpenAPI validation
- Comprehensive best practice checks
- Security analysis
- Documentation quality assessment

---

Made with ❤️ by [ApyGuard](https://github.com/ApyGuard)
