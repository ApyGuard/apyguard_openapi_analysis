import json
import os
import sys
import requests
import yaml
import argparse
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin

# --- Repository Information ---

def get_repository_info(owner: str, repo: str, token: Optional[str] = None) -> Dict[str, Any]:
    """Get repository information from GitHub API."""
    headers = {}
    if token:
        headers["Authorization"] = f"token {token}"
    
    api_url = f"https://api.github.com/repos/{owner}/{repo}"
    
    try:
        response = requests.get(api_url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        return {"error": f"Failed to fetch repository info: {e}"}

def find_openapi_files(owner: str, repo: str, token: Optional[str] = None) -> List[Dict[str, Any]]:
    """Find OpenAPI files in a GitHub repository."""
    headers = {}
    if token:
        headers["Authorization"] = f"token {token}"
    
    # Common OpenAPI file patterns
    openapi_patterns = [
        "**/openapi.json",
        "**/openapi.yaml", 
        "**/openapi.yml",
        "**/swagger.json",
        "**/swagger.yaml",
        "**/swagger.yml",
        "**/api.json",
        "**/api.yaml",
        "**/api.yml",
        "**/spec.json",
        "**/spec.yaml",
        "**/spec.yml"
    ]
    
    found_files = []
    
    for pattern in openapi_patterns:
        search_url = f"https://api.github.com/search/code"
        params = {
            "q": f"repo:{owner}/{repo} filename:{pattern}",
            "per_page": 100
        }
        
        try:
            response = requests.get(search_url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            for item in data.get("items", []):
                file_info = {
                    "name": item["name"],
                    "path": item["path"],
                    "url": item["html_url"],
                    "download_url": item["download_url"],
                    "size": item.get("size", 0),
                    "type": "file"
                }
                found_files.append(file_info)
                
        except requests.RequestException as e:
            print(f"Warning: Failed to search for {pattern}: {e}")
            continue
    
    return found_files

def get_repository_contents(owner: str, repo: str, path: str = "", token: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get repository contents from a specific path."""
    headers = {}
    if token:
        headers["Authorization"] = f"token {token}"
    
    api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    
    try:
        response = requests.get(api_url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        return []

def analyze_repository_openapi(owner: str, repo: str, token: Optional[str] = None) -> Dict[str, Any]:
    """Analyze all OpenAPI files found in a repository."""
    print(f"Analyzing repository: {owner}/{repo}")
    
    # Get repository info
    repo_info = get_repository_info(owner, repo, token)
    if "error" in repo_info:
        return {"status": "error", "message": repo_info["error"]}
    
    # Find OpenAPI files
    openapi_files = find_openapi_files(owner, repo, token)
    
    if not openapi_files:
        return {
            "status": "success",
            "repository": {
                "name": repo_info["name"],
                "full_name": repo_info["full_name"],
                "description": repo_info.get("description", ""),
                "url": repo_info["html_url"],
                "language": repo_info.get("language", ""),
                "stars": repo_info.get("stargazers_count", 0),
                "forks": repo_info.get("forks_count", 0)
            },
            "openapi_files": [],
            "message": "No OpenAPI files found in repository"
        }
    
    # Analyze each OpenAPI file
    analysis_results = []
    for file_info in openapi_files:
        print(f"Analyzing: {file_info['path']}")
        
        try:
            # Download and analyze the file
            response = requests.get(file_info["download_url"], timeout=30)
            response.raise_for_status()
            
            spec, parse_suggestions = _load_openapi_from_bytes(response.content)
            
            if spec:
                # Perform full analysis
                result = analyze_openapi_spec(spec)
                result["file_info"] = file_info
                analysis_results.append(result)
            else:
                analysis_results.append({
                    "file_info": file_info,
                    "status": "error",
                    "message": "Failed to parse OpenAPI spec",
                    "suggestions": parse_suggestions
                })
                
        except requests.RequestException as e:
            analysis_results.append({
                "file_info": file_info,
                "status": "error",
                "message": f"Failed to download file: {e}"
            })
    
    return {
        "status": "success",
        "repository": {
            "name": repo_info["name"],
            "full_name": repo_info["full_name"],
            "description": repo_info.get("description", ""),
            "url": repo_info["html_url"],
            "language": repo_info.get("language", ""),
            "stars": repo_info.get("stargazers_count", 0),
            "forks": repo_info.get("forks_count", 0)
        },
        "openapi_files": analysis_results
    }

# --- Helpers ---

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


def _validate_with_openapi_spec_validator(spec: dict) -> List[str]:
    suggestions: List[str] = []
    try:
        from openapi_spec_validator import validate_spec
        validate_spec(spec)
    except ImportError:
        suggestions.append("Could not import openapi-spec-validator, skipping validation.")
    except Exception as e:
        suggestions.append(f"Spec validation: {e}")
    return suggestions


def set_github_outputs(result: dict):
    """Set GitHub Action outputs."""
    def _set(name: str, value: str):
        print(f"::set-output name={name}::{value}")

    _set("analysis", json.dumps(result))
    _set("is_valid", str(result.get("is_valid", False)).lower())
    _set("suggestions_count", str(len(result.get("suggestions", []))))

    summary = result.get("summary", {})
    _set("operations_count", str(summary.get("operations_count", 0)))
    _set("paths_count", str(summary.get("paths_count", 0)))
    _set("schemas_count", str(summary.get("schemas_count", 0)))

    # GitHub metadata
    _set("user_actor", os.getenv("GITHUB_ACTOR", ""))
    _set("user_repository", os.getenv("GITHUB_REPOSITORY", ""))
    _set("user_workflow", os.getenv("GITHUB_WORKFLOW", ""))
    _set("user_run_id", os.getenv("GITHUB_RUN_ID", ""))


def send_to_server(result: dict):
    """Send analysis + GitHub metadata to external server if configured."""
    server_url = os.getenv("SERVER_URL")
    token = os.getenv("SERVER_TOKEN")

    if not server_url or not token:
        print("Skipping server reporting (SERVER_URL or SERVER_TOKEN not set).")
        return

    payload = {
        "actor": os.getenv("GITHUB_ACTOR"),
        "repository": os.getenv("GITHUB_REPOSITORY"),
        "commit_sha": os.getenv("GITHUB_SHA"),
        "workflow": os.getenv("GITHUB_WORKFLOW"),
        "run_id": os.getenv("GITHUB_RUN_ID"),
        "result": result,
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }

    try:
        resp = requests.post(server_url, headers=headers, json=payload, timeout=20)
        resp.raise_for_status()
        print("Successfully sent data to server.")
    except Exception as e:
        print(f"Failed to send data to server: {e}")

# --- Analyzer Core ---

def analyze_openapi_spec(spec: dict) -> Dict[str, Any]:
    """Analyze an OpenAPI specification dictionary."""
    suggestions: List[str] = []
    
    suggestions.extend(_validate_with_openapi_spec_validator(spec))

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
    else:
        for server in servers:
            if isinstance(server, dict):
                url_val = server.get("url")
                if url_val and "{" in url_val:
                    suggestions.append(f"Server URL '{url_val}' uses variables. Document them properly.")

    security = spec.get("security", [])
    if not security:
        suggestions.append("No global security requirements defined. Consider adding authentication info.")
    
    security_schemes = components.get("securitySchemes", {})
    if isinstance(security_schemes, dict):
        if not security_schemes:
            suggestions.append("No security schemes defined in components.")
        else:
            for scheme_name, scheme_def in security_schemes.items():
                if not isinstance(scheme_def, dict):
                    continue
                if "type" not in scheme_def:
                    suggestions.append(f"Security scheme '{scheme_name}' missing type.")
                if "description" not in scheme_def:
                    suggestions.append(f"Security scheme '{scheme_name}' missing description.")
                
                scheme_type = scheme_def.get("type")
                if scheme_type == "oauth2":
                    if "flows" not in scheme_def:
                        suggestions.append(f"OAuth2 security scheme '{scheme_name}' missing flows.")
                elif scheme_type == "apiKey":
                    if "in" not in scheme_def:
                        suggestions.append(f"API Key security scheme '{scheme_name}' missing 'in' field.")
                    if "name" not in scheme_def:
                        suggestions.append(f"API Key security scheme '{scheme_name}' missing 'name' field.")

    for path in paths.keys():
        if not isinstance(path, str):
            continue
        if path != "/" and path.endswith("/"):
            suggestions.append(f"Path '{path}' has trailing slash - consider removing for consistency.")
        if "/" in path and not path.startswith("/"):
            suggestions.append(f"Path '{path}' should start with '/'.")
        if "{" in path and "}" in path:
            import re
            path_params = re.findall(r'\{([^}]+)\}', path)
            for param in path_params:
                if not param.replace("_", "").replace("-", "").isalnum():
                    suggestions.append(f"Path parameter '{param}' in '{path}' should use alphanumeric characters only.")

    operations_count = sum(
        1 for path, methods in (paths or {}).items() if isinstance(methods, dict)
        for method in methods.keys() if method.lower() in [
            "get", "post", "put", "delete", "patch", "options", "head", "trace"
        ]
    )
    seen_operation_ids = set()
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
            operations_count += 1

            opid = details.get("operationId")
            if not opid:
                suggestions.append(f"Operation {method.upper()} {path} missing operationId.")
            else:
                if opid in seen_operation_ids:
                    suggestions.append(f"Duplicate operationId '{opid}' found.")
                seen_operation_ids.add(opid)

            if not details.get("summary"):
                suggestions.append(f"Operation {method.upper()} {path} missing summary.")
            if not details.get("description"):
                suggestions.append(f"Operation {method.upper()} {path} missing description.")
            
            if not details.get("tags"):
                suggestions.append(f"Operation {method.upper()} {path} missing tags for grouping.")
            
            if details.get("deprecated") is True:
                suggestions.append(f"Operation {method.upper()} {path} is deprecated - consider adding migration info.")
            
            method_lower = method.lower()
            if method_lower == "get" and "requestBody" in details:
                suggestions.append(f"GET operation {path} should not have requestBody.")
            elif method_lower in ["post", "put", "patch"] and "requestBody" not in details:
                suggestions.append(f"{method.upper()} operation {path} should have requestBody.")
            elif method_lower == "delete" and "requestBody" in details:
                suggestions.append(f"DELETE operation {path} typically should not have requestBody.")
            
            if method_lower in ["put", "delete"] and not details.get("description", "").lower().find("idempotent") == -1:
                suggestions.append(f"{method.upper()} operation {path} should document idempotent behavior.")

            params = details.get("parameters", [])
            if isinstance(params, list):
                seen = set()
                for param in params:
                    if not isinstance(param, dict):
                        continue
                    name = param.get("name")
                    loc = param.get("in")
                    if not name or not loc:
                        suggestions.append(f"Parameter in {method.upper()} {path} missing name or in.")
                    else:
                        key = (name, loc)
                        if key in seen:
                            suggestions.append(
                                f"Duplicate parameter {name} in {loc} for {method.upper()} {path}."
                            )
                        else:
                            seen.add(key)
                    if "description" not in param:
                        suggestions.append(
                            f"Parameter {name} in {loc} of {method.upper()} {path} missing description."
                        )

            if "requestBody" in details:
                rb = details.get("requestBody", {})
                if isinstance(rb, dict):
                    content = rb.get("content", {})
                    if not content:
                        suggestions.append(f"{method.upper()} {path} requestBody has no content defined.")
                    else:
                        if "application/json" not in content:
                            suggestions.append(f"{method.upper()} {path} requestBody should include application/json content type.")
                        for content_type, content_spec in content.items():
                            if isinstance(content_spec, dict) and not content_spec.get("examples") and not content_spec.get("example"):
                                suggestions.append(f"{method.upper()} {path} requestBody content {content_type} missing examples.")

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
                
                for code, resp_detail in responses.items():
                    if not isinstance(resp_detail, dict):
                        continue
                    if "description" not in resp_detail:
                        suggestions.append(
                            f"Response {code} of {method.upper()} {path} missing description."
                        )
                    content = resp_detail.get("content", {})
                    if isinstance(content, dict):
                        if "application/json" not in content and content:
                            suggestions.append(f"Response {code} of {method.upper()} {path} should include application/json content type.")
                        
                        for ctype, cval in content.items():
                            schema = cval.get("schema")
                            if not schema:
                                suggestions.append(
                                    f"Response {code} of {method.upper()} {path} with content {ctype} missing schema."
                                )
                            if isinstance(cval, dict) and not cval.get("examples") and not cval.get("example"):
                                suggestions.append(f"Response {code} of {method.upper()} {path} content {ctype} missing examples.")

            if "security" not in details:
                suggestions.append(f"Operation {method.upper()} {path} missing security definition.")

    for sname, sdef in schemas.items():
        if not isinstance(sdef, dict):
            continue
        if "type" not in sdef and "allOf" not in sdef and "oneOf" not in sdef and "anyOf" not in sdef:
            suggestions.append(f"Schema {sname} missing type or composition keyword.")
        if "description" not in sdef:
            suggestions.append(f"Schema {sname} missing description.")
        
        if "required" in sdef and isinstance(sdef["required"], list):
            for req_field in sdef["required"]:
                if req_field not in sdef.get("properties", {}):
                    suggestions.append(f"Schema {sname} has required field '{req_field}' not defined in properties.")
        
        properties = sdef.get("properties", {})
        if isinstance(properties, dict):
            for prop_name, prop_def in properties.items():
                if not isinstance(prop_def, dict):
                    continue
                if "description" not in prop_def:
                    suggestions.append(f"Schema {sname} property '{prop_name}' missing description.")
                if "type" not in prop_def and "$ref" not in prop_def:
                    suggestions.append(f"Schema {sname} property '{prop_name}' missing type or $ref.")
                if prop_def.get("nullable") is True and prop_def.get("type") == "null":
                    suggestions.append(f"Schema {sname} property '{prop_name}' should use nullable: true instead of type: null.")
        
        if "example" not in sdef and "examples" not in sdef:
            suggestions.append(f"Schema {sname} missing example or examples.")
    
    for path, methods in paths.items():
        if not isinstance(methods, dict):
            continue
        for method, details in methods.items():
            if not isinstance(details, dict):
                continue
            
            if method.lower() == "get" and ("list" in path.lower() or "s" in path.split("/")[-1]):
                has_pagination = False
                params = details.get("parameters", [])
                for param in params:
                    if isinstance(param, dict) and param.get("name", "").lower() in ["page", "limit", "offset", "size"]:
                        has_pagination = True
                        break
                if not has_pagination:
                    suggestions.append(f"List operation {method.upper()} {path} should support pagination parameters.")
            
            responses = details.get("responses", {})
            has_rate_limit = False
            for code, resp_detail in responses.items():
                if isinstance(resp_detail, dict):
                    headers = resp_detail.get("headers", {})
                    if isinstance(headers, dict):
                        for header_name in headers.keys():
                            if "rate" in header_name.lower() or "limit" in header_name.lower():
                                has_rate_limit = True
                                break
            if not has_rate_limit:
                suggestions.append(f"Operation {method.upper()} {path} should document rate limiting headers.")
            
            has_cache_headers = False
            for code, resp_detail in responses.items():
                if isinstance(resp_detail, dict):
                    headers = resp_detail.get("headers", {})
                    if isinstance(headers, dict):
                        for header_name in headers.keys():
                            if "cache" in header_name.lower() or "etag" in header_name.lower():
                                has_cache_headers = True
                                break
            if not has_cache_headers and method.lower() == "get":
                suggestions.append(f"GET operation {path} should document caching headers.")

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

def analyze_openapi_url(url: str) -> Dict[str, Any]:
    errors: List[str] = []
    suggestions: List[str] = []

    try:
        resp = requests.get(url, timeout=30, allow_redirects=True)
        resp.raise_for_status()
        spec, parse_suggestions = _load_openapi_from_bytes(resp.content)
        suggestions.extend(parse_suggestions)
    except requests.RequestException as e:
        return {"status": "error", "errors": [f"Failed to fetch URL: {e}"], "is_valid": False}

    if not spec:
        return {"status": "error", "errors": errors, "is_valid": False}

    suggestions.extend(_validate_with_openapi_spec_validator(spec))

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
    else:
        for server in servers:
            if isinstance(server, dict):
                url_val = server.get("url")
                if url_val and "{" in url_val:
                    suggestions.append(f"Server URL '{url_val}' uses variables. Document them properly.")

    security = spec.get("security", [])
    if not security:
        suggestions.append("No global security requirements defined. Consider adding authentication info.")
    
    security_schemes = components.get("securitySchemes", {})
    if isinstance(security_schemes, dict):
        if not security_schemes:
            suggestions.append("No security schemes defined in components.")
        else:
            for scheme_name, scheme_def in security_schemes.items():
                if not isinstance(scheme_def, dict):
                    continue
                if "type" not in scheme_def:
                    suggestions.append(f"Security scheme '{scheme_name}' missing type.")
                if "description" not in scheme_def:
                    suggestions.append(f"Security scheme '{scheme_name}' missing description.")
                
                scheme_type = scheme_def.get("type")
                if scheme_type == "oauth2":
                    if "flows" not in scheme_def:
                        suggestions.append(f"OAuth2 security scheme '{scheme_name}' missing flows.")
                elif scheme_type == "apiKey":
                    if "in" not in scheme_def:
                        suggestions.append(f"API Key security scheme '{scheme_name}' missing 'in' field.")
                    if "name" not in scheme_def:
                        suggestions.append(f"API Key security scheme '{scheme_name}' missing 'name' field.")

    for path in paths.keys():
        if not isinstance(path, str):
            continue
        if path != "/" and path.endswith("/"):
            suggestions.append(f"Path '{path}' has trailing slash - consider removing for consistency.")
        if "/" in path and not path.startswith("/"):
            suggestions.append(f"Path '{path}' should start with '/'.")
        if "{" in path and "}" in path:
            import re
            path_params = re.findall(r'\{([^}]+)\}', path)
            for param in path_params:
                if not param.replace("_", "").replace("-", "").isalnum():
                    suggestions.append(f"Path parameter '{param}' in '{path}' should use alphanumeric characters only.")

    operations_count = sum(
        1 for path, methods in (paths or {}).items() if isinstance(methods, dict)
        for method in methods.keys() if method.lower() in [
            "get", "post", "put", "delete", "patch", "options", "head", "trace"
        ]
    )
    seen_operation_ids = set()
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
            operations_count += 1

            opid = details.get("operationId")
            if not opid:
                suggestions.append(f"Operation {method.upper()} {path} missing operationId.")
            else:
                if opid in seen_operation_ids:
                    suggestions.append(f"Duplicate operationId '{opid}' found.")
                seen_operation_ids.add(opid)

            if not details.get("summary"):
                suggestions.append(f"Operation {method.upper()} {path} missing summary.")
            if not details.get("description"):
                suggestions.append(f"Operation {method.upper()} {path} missing description.")
            
            if not details.get("tags"):
                suggestions.append(f"Operation {method.upper()} {path} missing tags for grouping.")
            
            if details.get("deprecated") is True:
                suggestions.append(f"Operation {method.upper()} {path} is deprecated - consider adding migration info.")
            
            method_lower = method.lower()
            if method_lower == "get" and "requestBody" in details:
                suggestions.append(f"GET operation {path} should not have requestBody.")
            elif method_lower in ["post", "put", "patch"] and "requestBody" not in details:
                suggestions.append(f"{method.upper()} operation {path} should have requestBody.")
            elif method_lower == "delete" and "requestBody" in details:
                suggestions.append(f"DELETE operation {path} typically should not have requestBody.")
            
            if method_lower in ["put", "delete"] and not details.get("description", "").lower().find("idempotent") == -1:
                suggestions.append(f"{method.upper()} operation {path} should document idempotent behavior.")

            params = details.get("parameters", [])
            if isinstance(params, list):
                seen = set()
                for param in params:
                    if not isinstance(param, dict):
                        continue
                    name = param.get("name")
                    loc = param.get("in")
                    if not name or not loc:
                        suggestions.append(f"Parameter in {method.upper()} {path} missing name or in.")
                    else:
                        key = (name, loc)
                        if key in seen:
                            suggestions.append(
                                f"Duplicate parameter {name} in {loc} for {method.upper()} {path}."
                            )
                        else:
                            seen.add(key)
                    if "description" not in param:
                        suggestions.append(
                            f"Parameter {name} in {loc} of {method.upper()} {path} missing description."
                        )

            if "requestBody" in details:
                rb = details.get("requestBody", {})
                if isinstance(rb, dict):
                    content = rb.get("content", {})
                    if not content:
                        suggestions.append(f"{method.upper()} {path} requestBody has no content defined.")
                    else:
                        if "application/json" not in content:
                            suggestions.append(f"{method.upper()} {path} requestBody should include application/json content type.")
                        for content_type, content_spec in content.items():
                            if isinstance(content_spec, dict) and not content_spec.get("examples") and not content_spec.get("example"):
                                suggestions.append(f"{method.upper()} {path} requestBody content {content_type} missing examples.")

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
                
                for code, resp_detail in responses.items():
                    if not isinstance(resp_detail, dict):
                        continue
                    if "description" not in resp_detail:
                        suggestions.append(
                            f"Response {code} of {method.upper()} {path} missing description."
                        )
                    content = resp_detail.get("content", {})
                    if isinstance(content, dict):
                        if "application/json" not in content and content:
                            suggestions.append(f"Response {code} of {method.upper()} {path} should include application/json content type.")
                        
                        for ctype, cval in content.items():
                            schema = cval.get("schema")
                            if not schema:
                                suggestions.append(
                                    f"Response {code} of {method.upper()} {path} with content {ctype} missing schema."
                                )
                            if isinstance(cval, dict) and not cval.get("examples") and not cval.get("example"):
                                suggestions.append(f"Response {code} of {method.upper()} {path} content {ctype} missing examples.")

            if "security" not in details:
                suggestions.append(f"Operation {method.upper()} {path} missing security definition.")

    for sname, sdef in schemas.items():
        if not isinstance(sdef, dict):
            continue
        if "type" not in sdef and "allOf" not in sdef and "oneOf" not in sdef and "anyOf" not in sdef:
            suggestions.append(f"Schema {sname} missing type or composition keyword.")
        if "description" not in sdef:
            suggestions.append(f"Schema {sname} missing description.")
        
        if "required" in sdef and isinstance(sdef["required"], list):
            for req_field in sdef["required"]:
                if req_field not in sdef.get("properties", {}):
                    suggestions.append(f"Schema {sname} has required field '{req_field}' not defined in properties.")
        
        properties = sdef.get("properties", {})
        if isinstance(properties, dict):
            for prop_name, prop_def in properties.items():
                if not isinstance(prop_def, dict):
                    continue
                if "description" not in prop_def:
                    suggestions.append(f"Schema {sname} property '{prop_name}' missing description.")
                if "type" not in prop_def and "$ref" not in prop_def:
                    suggestions.append(f"Schema {sname} property '{prop_name}' missing type or $ref.")
                if prop_def.get("nullable") is True and prop_def.get("type") == "null":
                    suggestions.append(f"Schema {sname} property '{prop_name}' should use nullable: true instead of type: null.")
        
        if "example" not in sdef and "examples" not in sdef:
            suggestions.append(f"Schema {sname} missing example or examples.")
    
    for path, methods in paths.items():
        if not isinstance(methods, dict):
            continue
        for method, details in methods.items():
            if not isinstance(details, dict):
                continue
            
            if method.lower() == "get" and ("list" in path.lower() or "s" in path.split("/")[-1]):
                has_pagination = False
                params = details.get("parameters", [])
                for param in params:
                    if isinstance(param, dict) and param.get("name", "").lower() in ["page", "limit", "offset", "size"]:
                        has_pagination = True
                        break
                if not has_pagination:
                    suggestions.append(f"List operation {method.upper()} {path} should support pagination parameters.")
            
            responses = details.get("responses", {})
            has_rate_limit = False
            for code, resp_detail in responses.items():
                if isinstance(resp_detail, dict):
                    headers = resp_detail.get("headers", {})
                    if isinstance(headers, dict):
                        for header_name in headers.keys():
                            if "rate" in header_name.lower() or "limit" in header_name.lower():
                                has_rate_limit = True
                                break
            if not has_rate_limit:
                suggestions.append(f"Operation {method.upper()} {path} should document rate limiting headers.")
            
            has_cache_headers = False
            for code, resp_detail in responses.items():
                if isinstance(resp_detail, dict):
                    headers = resp_detail.get("headers", {})
                    if isinstance(headers, dict):
                        for header_name in headers.keys():
                            if "cache" in header_name.lower() or "etag" in header_name.lower():
                                has_cache_headers = True
                                break
            if not has_cache_headers and method.lower() == "get":
                suggestions.append(f"GET operation {path} should document caching headers.")

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


# --- CLI Entrypoint ---

def main():
    parser = argparse.ArgumentParser(description="OpenAPI Analyzer - Analyze OpenAPI specifications")
    parser.add_argument("input", nargs="?", help="OpenAPI URL or repository (owner/repo)")
    parser.add_argument("--url", help="OpenAPI specification URL")
    parser.add_argument("--repo", help="GitHub repository (owner/repo)")
    parser.add_argument("--token", help="GitHub token for private repositories")
    parser.add_argument("--output", choices=["json", "summary"], default="json", help="Output format")
    
    args = parser.parse_args()
    
    # Handle environment variables for GitHub Actions
    url = os.getenv("INPUT_SPEC_URL")
    repo = os.getenv("INPUT_REPOSITORY")
    token = os.getenv("INPUT_GITHUB_TOKEN")
    
    # Override with command line arguments
    if args.url:
        url = args.url
    if args.repo:
        repo = args.repo
    if args.token:
        token = args.token
    
    # Handle positional argument
    if args.input and not url and not repo:
        if "/" in args.input and not args.input.startswith("http"):
            repo = args.input
        else:
            url = args.input
    
    if not url and not repo:
        print("Usage: python analyzer.py <openapi-url>")
        print("       python analyzer.py --repo owner/repo")
        print("       python analyzer.py --url <openapi-url>")
        print("Or set INPUT_SPEC_URL or INPUT_REPOSITORY environment variable for GitHub Actions")
        sys.exit(1)
    
    if url:
        # Analyze single OpenAPI URL
        result = analyze_openapi_url(url)
    elif repo:
        # Analyze repository
        if "/" not in repo:
            print("Repository must be in format 'owner/repo'")
            sys.exit(1)
        
        owner, repo_name = repo.split("/", 1)
        result = analyze_repository_openapi(owner, repo_name, token)
    else:
        print("No input provided")
        sys.exit(1)
    
    # Set GitHub Actions outputs if running in GitHub Actions
    if os.getenv("GITHUB_ACTIONS"):
        def set_output(name: str, value: str):
            print(f"::set-output name={name}::{value}")
        
        set_output("analysis", json.dumps(result))
        set_output("is_valid", str(result.get("is_valid", False)).lower())
        set_output("suggestions_count", str(len(result.get("suggestions", []))))
        
        if "summary" in result:
            summary = result.get("summary", {})
            set_output("operations_count", str(summary.get("operations_count", 0)))
            set_output("paths_count", str(summary.get("paths_count", 0)))
            set_output("schemas_count", str(summary.get("schemas_count", 0)))
        
        # Repository information
        if "repository" in result:
            repo_info = result["repository"]
            set_output("repository_name", repo_info.get("name", ""))
            set_output("repository_full_name", repo_info.get("full_name", ""))
            set_output("repository_url", repo_info.get("url", ""))
            set_output("repository_stars", str(repo_info.get("stars", 0)))
            set_output("repository_forks", str(repo_info.get("forks", 0)))
    
    # Output results
    if args.output == "summary":
        if "repository" in result:
            repo_info = result["repository"]
            print(f"\nRepository: {repo_info.get('full_name', 'Unknown')}")
            print(f"Description: {repo_info.get('description', 'No description')}")
            print(f"Stars: {repo_info.get('stars', 0)} | Forks: {repo_info.get('forks', 0)}")
            print(f"Language: {repo_info.get('language', 'Unknown')}")
            print(f"URL: {repo_info.get('url', '')}")
            
            if "openapi_files" in result:
                print(f"\nFound {len(result['openapi_files'])} OpenAPI files:")
                for i, file_result in enumerate(result["openapi_files"], 1):
                    file_info = file_result.get("file_info", {})
                    print(f"  {i}. {file_info.get('path', 'Unknown')}")
                    if "summary" in file_result:
                        summary = file_result["summary"]
                        print(f"     Operations: {summary.get('operations_count', 0)}")
                        print(f"     Paths: {summary.get('paths_count', 0)}")
                        print(f"     Schemas: {summary.get('schemas_count', 0)}")
                    if "suggestions" in file_result:
                        print(f"     Suggestions: {len(file_result['suggestions'])}")
        else:
            # Single file analysis
            if "summary" in result:
                summary = result["summary"]
                print(f"\nOpenAPI Analysis Summary:")
                print(f"  Version: {summary.get('openapi_version', 'Unknown')}")
                print(f"  Operations: {summary.get('operations_count', 0)}")
                print(f"  Paths: {summary.get('paths_count', 0)}")
                print(f"  Schemas: {summary.get('schemas_count', 0)}")
                print(f"  Suggestions: {len(result.get('suggestions', []))}")
    else:
        print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
