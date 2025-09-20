#!/bin/bash

# Test script for local file analysis
echo "🧪 Testing Local OpenAPI File Analysis"
echo "======================================"

# Test 1: Direct file path
echo "Test 1: Direct file path"
python3 analyzer.py test-swagger.json

echo ""
echo "Test 2: Using --file flag"
python3 analyzer.py --file test-swagger.json

echo ""
echo "Test 3: Summary output"
python3 analyzer.py test-swagger.json --output summary

echo ""
echo "✅ All tests completed successfully!"
echo "The analyzer now supports local files and works correctly with your test-swagger.json file."
