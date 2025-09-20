#!/bin/bash

# Test script for OpenAPI Analyzer GitHub Action
# This script tests the action locally with different scenarios

set -e

echo "🧪 Testing OpenAPI Analyzer GitHub Action Locally"
echo "=================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    local status=$1
    local message=$2
    case $status in
        "SUCCESS")
            echo -e "${GREEN}✅ $message${NC}"
            ;;
        "ERROR")
            echo -e "${RED}❌ $message${NC}"
            ;;
        "WARNING")
            echo -e "${YELLOW}⚠️  $message${NC}"
            ;;
        "INFO")
            echo -e "${BLUE}ℹ️  $message${NC}"
            ;;
    esac
}

# Function to test a scenario
test_scenario() {
    local scenario_name=$1
    local spec_url=$2
    local expected_suggestions=$3
    
    echo ""
    echo "🔍 Testing Scenario: $scenario_name"
    echo "----------------------------------------"
    echo "Spec URL: $spec_url"
    echo "Expected suggestions: $expected_suggestions"
    echo ""
    
    # Set environment variables for the action
    export INPUT_SPEC_URL="$spec_url"
    export INPUT_OUTPUT_FORMAT="json"
    export GITHUB_ACTIONS="true"
    export GITHUB_ACTOR="test-user"
    export GITHUB_REPOSITORY="test/repo"
    export GITHUB_WORKFLOW="test-workflow"
    export GITHUB_RUN_ID="123456"
    
    # Run the analyzer
    if python3 analyzer.py "$spec_url"; then
        print_status "SUCCESS" "Analysis completed successfully"
        
        # Check if we got suggestions
        local suggestions_count=$(python3 -c "
import json
import sys
try:
    result = json.loads(sys.stdin.read())
    print(len(result.get('suggestions', [])))
except:
    print(0)
" < <(python3 analyzer.py "$spec_url" 2>/dev/null))
        
        echo "Suggestions found: $suggestions_count"
        
        if [ "$expected_suggestions" = "some" ] && [ "$suggestions_count" -gt 0 ]; then
            print_status "SUCCESS" "Found expected suggestions"
        elif [ "$expected_suggestions" = "none" ] && [ "$suggestions_count" -eq 0 ]; then
            print_status "SUCCESS" "No suggestions as expected"
        else
            print_status "WARNING" "Unexpected suggestion count"
        fi
    else
        print_status "ERROR" "Analysis failed"
        return 1
    fi
}

# Function to test repository analysis
test_repository_scenario() {
    local scenario_name=$1
    local repository=$2
    
    echo ""
    echo "🔍 Testing Repository Scenario: $scenario_name"
    echo "----------------------------------------"
    echo "Repository: $repository"
    echo ""
    
    # Set environment variables for the action
    export INPUT_REPOSITORY="$repository"
    export INPUT_OUTPUT_FORMAT="summary"
    export GITHUB_ACTIONS="true"
    export GITHUB_ACTOR="test-user"
    export GITHUB_REPOSITORY="test/repo"
    export GITHUB_WORKFLOW="test-workflow"
    export GITHUB_RUN_ID="123456"
    
    # Run the analyzer
    if python3 analyzer.py --repo "$repository" --output summary; then
        print_status "SUCCESS" "Repository analysis completed successfully"
    else
        print_status "ERROR" "Repository analysis failed"
        return 1
    fi
}

# Check if analyzer.py exists
if [ ! -f "analyzer.py" ]; then
    print_status "ERROR" "analyzer.py not found. Please run this script from the project directory."
    exit 1
fi

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    print_status "ERROR" "Python3 not found. Please install Python 3.x"
    exit 1
fi

print_status "INFO" "Starting local testing..."

# Test 1: Local file (Swagger 2.0)
print_status "INFO" "Test 1: Local Swagger 2.0 file"
test_scenario "Local Swagger 2.0" "file://$(pwd)/test-swagger.json" "some"

# Test 2: Public OpenAPI 3.0 URL
print_status "INFO" "Test 2: Public OpenAPI 3.0 URL"
test_scenario "Public OpenAPI 3.0" "https://petstore.swagger.io/v2/swagger.json" "some"

# Test 3: Another public OpenAPI URL
print_status "INFO" "Test 3: Another public OpenAPI URL"
test_scenario "Public OpenAPI" "https://api.apis.guru/v2/specs/amazonaws.com/accessanalyzer/2019-11-01/openapi.json" "some"

# Test 4: Invalid URL (should fail gracefully)
print_status "INFO" "Test 4: Invalid URL (should fail gracefully)"
test_scenario "Invalid URL" "https://invalid-url-that-does-not-exist.com/openapi.json" "none"

# Test 5: Repository analysis (if GitHub token is available)
if [ -n "$GITHUB_TOKEN" ]; then
    print_status "INFO" "Test 5: Repository analysis with token"
    test_repository_scenario "Repository with token" "github/rest-api-description"
else
    print_status "WARNING" "Test 5: Skipping repository analysis (no GITHUB_TOKEN)"
    print_status "INFO" "To test repository analysis, set GITHUB_TOKEN environment variable"
fi

# Test 6: Repository analysis without token (public repo)
print_status "INFO" "Test 6: Public repository analysis (no token)"
test_repository_scenario "Public repository" "github/rest-api-description"

# Test 7: CLI help
print_status "INFO" "Test 7: CLI help"
echo "Testing CLI help..."
if python3 analyzer.py --help; then
    print_status "SUCCESS" "CLI help works"
else
    print_status "ERROR" "CLI help failed"
fi

# Test 8: Invalid arguments
print_status "INFO" "Test 8: Invalid arguments (should show usage)"
echo "Testing invalid arguments..."
if ! python3 analyzer.py --invalid-flag; then
    print_status "SUCCESS" "Invalid arguments handled correctly"
else
    print_status "ERROR" "Invalid arguments not handled correctly"
fi

echo ""
echo "🎉 Local testing completed!"
echo "=========================="
print_status "INFO" "All tests completed. Check the output above for any issues."
print_status "INFO" "To test with a GitHub token, set the GITHUB_TOKEN environment variable:"
print_status "INFO" "export GITHUB_TOKEN=your_token_here"
print_status "INFO" "Then run this script again."
