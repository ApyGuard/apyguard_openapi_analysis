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
- 📁 **Local File Support**: Analyze local OpenAPI files in your repository

## Quick Start

### Option 1: Self-Contained Workflow (Recommended)

Add this workflow to your repository (`.github/workflows/openapi-analysis.yml`):

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
      
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
        
    - name: Install dependencies
      run: |
        pip install requests PyYAML openapi-spec-validator
        
    - name: Create analyzer script
      run: |
        cat > analyzer.py << 'EOF'
        import json
        import os
        import sys
        import requests
        import yaml
        import argparse
        from typing import Any, Dict, List, Optional, Tuple
        from urllib.parse import urljoin

        def _load_openapi_from_bytes(data: bytes) -> Tuple[Optional[dict], List[str]]:
            suggestions: List[str] = []
            text = data.decode("utf-8", errors="replace").strip()

            loaded: Optional[dict] = None
            try:
                loaded = json.loads(text)
            except json.JSONDecodeError:
                try:
                    loaded = yaml.safe_load(text)
                except yaml.YAMLError as e:
                    suggestions.append(f"Failed to parse as JSON or YAML: {e}")
                    loaded = None

            if not isinstance(loaded, dict):
                suggestions.append("OpenAPI content is not a valid JSON/YAML object.")
                return None, suggestions

            return loaded, suggestions

        def analyze_openapi_spec(spec: dict) -> Dict[str, Any]:
            suggestions: List[str] = []
            
            info = spec.get("info", {})
            if not info.get("title"):
                suggestions.append("Spec is missing an API title.")
            if not info.get("description"):
                suggestions.append("Spec should include a description.")
            if not info.get("version"):
                suggestions.append("Spec should define an API version.")

            openapi_version = spec.get("openapi") or spec.get("swagger")
            paths = spec.get("paths") or {}
            components = spec.get("components", {})
            schemas = components.get("schemas", {}) if isinstance(components, dict) else {}

            servers = spec.get("servers", [])
            if not servers:
                suggestions.append("No servers defined. Consider specifying servers for clarity.")

            security = spec.get("security", [])
            if not security:
                suggestions.append("No global security requirements defined. Consider adding authentication info.")
            
            security_schemes = components.get("securitySchemes", {})
            if isinstance(security_schemes, dict):
                if not security_schemes:
                    suggestions.append("No security schemes defined in components.")

            operations_count = sum(
                1 for path, methods in (paths or {}).items() if isinstance(methods, dict)
                for method in methods.keys() if method.lower() in [
                    "get", "post", "put", "delete", "patch", "options", "head", "trace"
                ]
            )

            for path, methods in paths.items():
                if not isinstance(methods, dict):
                    continue
                for method, details in methods.items():
                    if method.lower() not in [
                        "get", "post", "put", "delete", "patch", "options", "head", "trace"
                    ]:
                        continue
                    if not isinstance(details, dict):
                        continue

                    opid = details.get("operationId")
                    if not opid:
                        suggestions.append(f"Operation {method.upper()} {path} missing operationId.")

                    if not details.get("summary"):
                        suggestions.append(f"Operation {method.upper()} {path} missing summary.")
                    if not details.get("description"):
                        suggestions.append(f"Operation {method.upper()} {path} missing description.")
                    
                    if not details.get("tags"):
                        suggestions.append(f"Operation {method.upper()} {path} missing tags for grouping.")

                    method_lower = method.lower()
                    if method_lower == "get" and "requestBody" in details:
                        suggestions.append(f"GET operation {path} should not have requestBody.")
                    elif method_lower in ["post", "put", "patch"] and "requestBody" not in details:
                        suggestions.append(f"{method.upper()} operation {path} should have requestBody.")
                    elif method_lower == "delete" and "requestBody" in details:
                        suggestions.append(f"DELETE operation {path} typically should not have requestBody.")

                    responses = details.get("responses", {})
                    if not responses:
                        suggestions.append(f"Operation {method.upper()} {path} has no responses defined.")
                    else:
                        if "200" not in responses and "201" not in responses:
                            suggestions.append(
                                f"Operation {method.upper()} {path} missing 200/201 success response."
                            )
                        
                        has_4xx = any(code.startswith("4") for code in responses.keys())
                        has_5xx = any(code.startswith("5") for code in responses.keys())
                        if not has_4xx:
                            suggestions.append(f"Operation {method.upper()} {path} missing 4xx error responses.")
                        if not has_5xx:
                            suggestions.append(f"Operation {method.upper()} {path} missing 5xx error responses.")

            return {
                "status": "success",
                "is_valid": True,
                "summary": {
                    "openapi_version": str(openapi_version) if openapi_version else None,
                    "paths_count": len(paths) if isinstance(paths, dict) else 0,
                    "operations_count": operations_count,
                    "schemas_count": len(schemas) if isinstance(schemas, dict) else 0,
                },
                "suggestions": suggestions,
            }

        def analyze_local_file(file_path: str) -> Dict[str, Any]:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                spec, parse_suggestions = _load_openapi_from_bytes(content.encode('utf-8'))
                
                if spec:
                    result = analyze_openapi_spec(spec)
                    result["file_path"] = file_path
                    return result
                else:
                    return {
                        "status": "error",
                        "message": "Failed to parse OpenAPI spec",
                        "suggestions": parse_suggestions,
                        "file_path": file_path
                    }
            except FileNotFoundError:
                return {
                    "status": "error",
                    "message": f"File not found: {file_path}",
                    "file_path": file_path
                }
            except Exception as e:
                return {
                    "status": "error",
                    "message": f"Error reading file: {e}",
                    "file_path": file_path
                }

        def main():
            if len(sys.argv) < 2:
                print("Usage: python analyzer.py <file-path>")
                sys.exit(1)
            
            file_path = sys.argv[1]
            result = analyze_local_file(file_path)
            print(json.dumps(result, indent=2))

        if __name__ == "__main__":
            main()
        EOF
        
    - name: Run OpenAPI Analysis
      id: analyze
      run: |
        python analyzer.py your-openapi-file.json > analysis-results.json
        echo "analysis<<EOF" >> $GITHUB_OUTPUT
        cat analysis-results.json >> $GITHUB_OUTPUT
        echo "EOF" >> $GITHUB_OUTPUT
        
        # Extract individual values for outputs
        is_valid=$(python -c "import json; data=json.load(open('analysis-results.json')); print(data.get('is_valid', False))")
        suggestions_count=$(python -c "import json; data=json.load(open('analysis-results.json')); print(len(data.get('suggestions', [])))")
        operations_count=$(python -c "import json; data=json.load(open('analysis-results.json')); print(data.get('summary', {}).get('operations_count', 0))")
        paths_count=$(python -c "import json; data=json.load(open('analysis-results.json')); print(data.get('summary', {}).get('paths_count', 0))")
        schemas_count=$(python -c "import json; data=json.load(open('analysis-results.json')); print(data.get('summary', {}).get('schemas_count', 0))")
        
        echo "is_valid=$is_valid" >> $GITHUB_OUTPUT
        echo "suggestions_count=$suggestions_count" >> $GITHUB_OUTPUT
        echo "operations_count=$operations_count" >> $GITHUB_OUTPUT
        echo "paths_count=$paths_count" >> $GITHUB_OUTPUT
        echo "schemas_count=$schemas_count" >> $GITHUB_OUTPUT
        
    - name: Upload analysis results
      uses: actions/upload-artifact@v4
      if: always()
      with:
        name: openapi-analysis-results
        path: analysis-results.json
        retention-days: 30
        
    - name: Comment on PR
      if: github.event_name == 'pull_request'
      uses: actions/github-script@v7
      with:
        script: |
          const analysis = JSON.parse('${{ steps.analyze.outputs.analysis }}');
          const comment = `## 🔍 OpenAPI Analysis Results
          
          **Valid**: ${analysis.is_valid ? '✅' : '❌'}
          **Suggestions**: ${analysis.suggestions ? analysis.suggestions.length : 0}
          **Operations**: ${analysis.summary ? analysis.summary.operations_count : 0}
          **Paths**: ${analysis.summary ? analysis.summary.paths_count : 0}
          **Schemas**: ${analysis.summary ? analysis.summary.schemas_count : 0}
          
          ${analysis.suggestions && analysis.suggestions.length > 0 ? 
            `### 📋 Top Suggestions:\n\n${analysis.suggestions.slice(0, 5).map(s => `- ${s}`).join('\n')}` : 
            '### ✅ No suggestions found! Your OpenAPI specification looks great! 🎉'
          }
          
          Detailed results are available in the workflow artifacts.`;
            
          github.rest.issues.createComment({
            issue_number: context.issue.number,
            owner: context.repo.owner,
            repo: context.repo.repo,
            body: comment
          });
```

### Option 2: Using the GitHub Action (Alternative)

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
    - name: Analyze OpenAPI
      uses: ApyGuard/apyguard_openapi_analysis@main
      with:
        file: your-openapi-file.json
        output_format: json
```

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
If you encounter Docker-related issues, use the self-contained workflow (Option 1) which doesn't rely on Docker images.

## Requirements

- OpenAPI 3.0+ or Swagger 2.0 specifications
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

### v2.0.0
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