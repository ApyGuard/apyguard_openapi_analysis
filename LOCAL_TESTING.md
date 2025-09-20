# Local Testing Guide

This guide explains how to test the OpenAPI Analyzer GitHub Action locally with different scenarios.

## 🚀 Quick Start

### 1. Test with Local Script
```bash
# Make the test script executable
chmod +x test-action-local.sh

# Run all test scenarios
./test-action-local.sh
```

### 2. Test with GitHub Workflow
1. Go to Actions tab in your repository
2. Select "Test Action Locally" workflow
3. Click "Run workflow"
4. Choose test type and parameters
5. Click "Run workflow"

## 📋 Test Scenarios

### Scenario 1: Local Swagger 2.0 File
```bash
python analyzer.py file://$(pwd)/test-swagger.json
```
**Expected**: Should find suggestions for Swagger 2.0 spec

### Scenario 2: Public OpenAPI 3.0 URL
```bash
python analyzer.py https://petstore.swagger.io/v2/swagger.json
```
**Expected**: Should analyze public OpenAPI spec and find suggestions

### Scenario 3: Another Public OpenAPI URL
```bash
python analyzer.py https://api.apis.guru/v2/specs/amazonaws.com/accessanalyzer/2019-11-01/openapi.json
```
**Expected**: Should analyze AWS API spec and find suggestions

### Scenario 4: Invalid URL
```bash
python analyzer.py https://invalid-url-that-does-not-exist.com/openapi.json
```
**Expected**: Should fail gracefully with error message

### Scenario 5: Repository Analysis (with token)
```bash
export GITHUB_TOKEN=your_token_here
python analyzer.py --repo github/rest-api-description --output summary
```
**Expected**: Should analyze repository and find OpenAPI files

### Scenario 6: Repository Analysis (without token)
```bash
python analyzer.py --repo github/rest-api-description --output summary
```
**Expected**: Should analyze public repository (may hit rate limits)

### Scenario 7: CLI Help
```bash
python analyzer.py --help
```
**Expected**: Should show help message

### Scenario 8: Invalid Arguments
```bash
python analyzer.py --invalid-flag
```
**Expected**: Should show usage message

## 🧪 Test Files

### test-swagger.json
A comprehensive Swagger 2.0 specification with:
- ✅ Complete API definition
- ✅ User management endpoints
- ✅ Proper schemas and responses
- ✅ Security definitions
- ✅ Tags and descriptions

**Purpose**: Test local file analysis and Swagger 2.0 support

## 🔧 Manual Testing

### Test Single File Analysis
```bash
# Test with local file
python analyzer.py file://$(pwd)/test-swagger.json

# Test with public URL
python analyzer.py https://petstore.swagger.io/v2/swagger.json

# Test with summary output
python analyzer.py https://petstore.swagger.io/v2/swagger.json --output summary
```

### Test Repository Analysis
```bash
# Test public repository
python analyzer.py --repo github/rest-api-description --output summary

# Test with token (for private repos)
export GITHUB_TOKEN=your_token_here
python analyzer.py --repo owner/private-repo --output summary
```

### Test Environment Variables
```bash
# Set GitHub Actions environment
export GITHUB_ACTIONS=true
export GITHUB_ACTOR=test-user
export GITHUB_REPOSITORY=test/repo
export GITHUB_WORKFLOW=test-workflow
export GITHUB_RUN_ID=123456

# Test with environment variables
export INPUT_SPEC_URL="https://petstore.swagger.io/v2/swagger.json"
python analyzer.py
```

## 📊 Expected Results

### Single File Analysis
- **Status**: "success"
- **Valid**: true/false
- **Suggestions**: Array of improvement suggestions
- **Summary**: Operations, paths, schemas count

### Repository Analysis
- **Status**: "success"
- **Repository**: Repository metadata
- **OpenAPI Files**: Array of found files with analysis
- **Valid**: true/false for each file

### Error Cases
- **Status**: "error"
- **Message**: Error description
- **Suggestions**: Empty array

## 🐛 Troubleshooting

### Common Issues

1. **Python not found**
   ```bash
   # Install Python 3.x
   brew install python3  # macOS
   sudo apt-get install python3  # Ubuntu
   ```

2. **Missing dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Rate limit exceeded**
   ```bash
   # Wait for rate limit to reset or use token
   export GITHUB_TOKEN=your_token_here
   ```

4. **File not found**
   ```bash
   # Make sure you're in the project directory
   cd /path/to/openapi_analyzer
   ```

### Debug Mode
```bash
# Enable debug output
export DEBUG=1
python analyzer.py https://petstore.swagger.io/v2/swagger.json
```

## 📈 Performance Testing

### Test Rate Limits
```bash
# Check GitHub API rate limit
curl -H "Accept: application/vnd.github.v3+json" https://api.github.com/rate_limit
```

### Test Large Files
```bash
# Test with large OpenAPI spec
python analyzer.py https://api.apis.guru/v2/specs/amazonaws.com/accessanalyzer/2019-11-01/openapi.json
```

## 🔍 What Gets Tested

### Core Functionality
- ✅ OpenAPI specification parsing
- ✅ JSON/YAML format support
- ✅ Swagger 2.0 and OpenAPI 3.0 support
- ✅ Suggestion generation
- ✅ Error handling

### Repository Features
- ✅ Repository information gathering
- ✅ OpenAPI file discovery
- ✅ Multiple file analysis
- ✅ GitHub API integration
- ✅ Rate limit handling

### CLI Features
- ✅ Command line arguments
- ✅ Output formatting
- ✅ Help system
- ✅ Error messages

### GitHub Actions Integration
- ✅ Environment variables
- ✅ Outputs
- ✅ Error handling
- ✅ Docker execution

## 📝 Test Results

After running tests, you should see:
- ✅ All core functionality working
- ✅ Repository analysis working
- ✅ File discovery working
- ✅ Suggestion generation working
- ✅ Error handling working

If any tests fail, check the error messages and ensure you have the required dependencies installed.
