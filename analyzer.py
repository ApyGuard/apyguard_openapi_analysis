import json
import os
import sys
import requests
import yaml
import argparse
import re
import hashlib
import math
from typing import Any, Dict, List, Optional, Tuple, Set
from urllib.parse import urljoin, urlparse
from datetime import datetime, timedelta
from collections import defaultdict, Counter

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
    
    repo_info = get_repository_info(owner, repo, token)
    if "error" in repo_info:
        return {"status": "error", "message": repo_info["error"]}
    
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
    
    analysis_results = []
    for file_info in openapi_files:
        print(f"Analyzing: {file_info['path']}")
        
        try:
            response = requests.get(file_info["download_url"], timeout=30)
            response.raise_for_status()
            
            spec, parse_suggestions = _load_openapi_from_bytes(response.content, file_path=file_info.get("path"))
            
            if spec:
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

def _load_openapi_from_bytes(data: bytes, file_path: Optional[str] = None) -> Tuple[Optional[dict], List[str]]:
    """Load OpenAPI spec from bytes, supporting both JSON and YAML formats.
    
    Args:
        data: The file content as bytes
        file_path: Optional file path to help determine format from extension
    
    Returns:
        Tuple of (parsed_spec_dict, suggestions_list)
    """
    suggestions: List[str] = []
    text = data.decode("utf-8", errors="replace").strip()

    # Determine format preference based on file extension if provided
    prefer_yaml = False
    if file_path:
        file_lower = file_path.lower()
        if file_lower.endswith(('.yaml', '.yml')):
            prefer_yaml = True
        elif file_lower.endswith('.json'):
            prefer_yaml = False
        else:
            # Content-based detection: check if it looks like YAML
            # YAML files often start with --- or contain YAML-specific syntax
            if text.startswith('---') or (not text.startswith('{') and not text.startswith('[')):
                prefer_yaml = True
    else:
        # Content-based detection when no file path provided
        if text.startswith('---') or (not text.startswith('{') and not text.startswith('[')):
            prefer_yaml = True

    loaded: Optional[dict] = None
    
    # Try parsing based on detected/preferred format
    if prefer_yaml:
        try:
            loaded = yaml.safe_load(text)
            if loaded is None:
                # Empty YAML file or only comments
                suggestions.append("YAML file appears to be empty or contains only comments.")
        except yaml.YAMLError as e:
            # If YAML fails, try JSON as fallback
            try:
                loaded = json.loads(text)
            except json.JSONDecodeError:
                suggestions.append(f"Failed to parse as YAML: {e}")
                loaded = None
    else:
        try:
            loaded = json.loads(text)
        except json.JSONDecodeError:
            # If JSON fails, try YAML as fallback
            try:
                loaded = yaml.safe_load(text)
            except yaml.YAMLError as e:
                suggestions.append(f"Failed to parse as JSON or YAML: {e}")
                loaded = None

    if not isinstance(loaded, dict):
        suggestions.append("OpenAPI content is not a valid JSON/YAML object.")
        return None, suggestions

    return loaded, suggestions


def _is_openapi_v2(spec: dict) -> bool:
    """Return True if spec looks like Swagger/OpenAPI v2.0."""
    swagger = spec.get("swagger")
    if isinstance(swagger, str) and swagger.startswith("2."):
        return True
    return False


def _normalize_v2_to_v3ish(spec: dict) -> dict:
    """Normalize a Swagger 2.0 spec into a v3-like shape so downstream rules work.

    This does not attempt full fidelity conversion; it maps common fields used by
    our analyzer: components.schemas, components.securitySchemes, servers,
    requestBody/content, and response.content schemas.
    """
    import copy

    v2 = copy.deepcopy(spec)
    normalized: Dict[str, Any] = copy.deepcopy(spec)

    # Mark original version and normalized hint
    normalized.setdefault("x-original-version", v2.get("swagger", "2.0"))
    normalized["x-normalized"] = True

    # components
    components: Dict[str, Any] = normalized.get("components") or {}
    if not isinstance(components, dict):
        components = {}
    # definitions -> components.schemas
    if isinstance(v2.get("definitions"), dict):
        components.setdefault("schemas", v2.get("definitions", {}))
    # securityDefinitions -> components.securitySchemes
    if isinstance(v2.get("securityDefinitions"), dict):
        components.setdefault("securitySchemes", v2.get("securityDefinitions", {}))
    normalized["components"] = components

    # servers from host/basePath/schemes
    if not normalized.get("servers"):
        host = v2.get("host")
        base_path = v2.get("basePath", "")
        schemes = v2.get("schemes") or ["https"]
        servers: List[Dict[str, Any]] = []
        if host:
            for sch in schemes:
                url = f"{sch}://{host}{base_path}"
                servers.append({"url": url})
        elif base_path:
            servers.append({"url": base_path})
        if servers:
            normalized["servers"] = servers

    # paths: map body/formData parameters -> requestBody; map responses.schema -> content
    paths = normalized.get("paths") or {}
    if isinstance(paths, dict):
        for path_item, methods in list(paths.items()):
            if not isinstance(methods, dict):
                continue
            for method, details in list(methods.items()):
                if not isinstance(details, dict):
                    continue

                # Request body from parameters (in: body or formData)
                params = details.get("parameters", [])
                body_schema = None
                body_required = False
                media_types: List[str] = []

                # Derive consumes for this operation (operation consumes overrides global)
                op_consumes = details.get("consumes") or v2.get("consumes") or ["application/json"]
                if isinstance(op_consumes, list):
                    media_types = op_consumes

                new_params: List[Any] = []
                if isinstance(params, list):
                    for p in params:
                        if not isinstance(p, dict):
                            continue
                        loc = p.get("in")
                        if loc == "body":
                            body_schema = p.get("schema")
                            body_required = bool(p.get("required"))
                        elif loc == "formData":
                            # Represent formData as application/x-www-form-urlencoded if no file, else multipart/form-data
                            mt = "application/x-www-form-urlencoded"
                            if p.get("type") == "file":
                                mt = "multipart/form-data"
                            if mt not in media_types:
                                media_types.append(mt)
                            # Synthesize a schema property for this field
                            if body_schema is None:
                                body_schema = {"type": "object", "properties": {}, "required": []}
                            if isinstance(body_schema, dict):
                                props = body_schema.setdefault("properties", {})
                                if isinstance(props, dict):
                                    props[p.get("name", "field")] = {k: v for k, v in p.items() if k in ["type", "format", "description", "items"]}
                                    if p.get("required"):
                                        body_schema.setdefault("required", []).append(p.get("name", "field"))
                        else:
                            new_params.append(p)
                # Write back filtered params
                if params != new_params:
                    details["parameters"] = new_params

                # Create requestBody if we found body/formData
                if body_schema is not None and "requestBody" not in details:
                    content_obj: Dict[str, Any] = {}
                    for mt in media_types or ["application/json"]:
                        content_obj[mt] = {"schema": body_schema}
                    details["requestBody"] = {
                        "required": body_required,
                        "content": content_obj
                    }

                # Responses: map schema+produces -> content
                produces = details.get("produces") or v2.get("produces") or ["application/json"]
                responses = details.get("responses", {})
                if isinstance(responses, dict):
                    for code, resp in list(responses.items()):
                        if not isinstance(resp, dict):
                            continue
                        # If content already exists, skip
                        if "content" in resp:
                            continue
                        schema = resp.get("schema")
                        if schema is not None:
                            resp["content"] = {mt: {"schema": schema} for mt in produces}

    return normalized


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
    
    # Calculate total suggestions from grouped suggestions
    suggestions = result.get("suggestions", {})
    total_suggestions = sum(len(suggestion_list) for suggestion_list in suggestions.values())
    _set("suggestions_count", str(total_suggestions))

    summary = result.get("summary", {})
    _set("operations_count", str(summary.get("operations_count", 0)))
    _set("paths_count", str(summary.get("paths_count", 0)))
    _set("schemas_count", str(summary.get("schemas_count", 0)))

    # Advanced analytics outputs
    analytics = result.get("analytics", {})
    _set("complexity_score", str(analytics.get("complexity_score", 0)))
    _set("maintainability_score", str(analytics.get("maintainability_score", 0)))

    # Analysis categories
    categories = result.get("analysis_categories", {})
    _set("security_issues", str(categories.get("security", 0)))
    _set("performance_issues", str(categories.get("performance", 0)))
    _set("design_pattern_issues", str(categories.get("design_patterns", 0)))
    _set("versioning_issues", str(categories.get("versioning", 0)))
    _set("documentation_issues", str(categories.get("documentation", 0)))
    _set("compliance_issues", str(categories.get("compliance", 0)))
    _set("testing_recommendations", str(categories.get("testing", 0)))
    _set("monitoring_recommendations", str(categories.get("monitoring", 0)))
    _set("code_generation_opportunities", str(categories.get("code_generation", 0)))
    _set("governance_issues", str(categories.get("governance", 0)))

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

# --- Advanced Analysis Functions ---

def analyze_security_enhanced(spec: dict) -> List[str]:
    """Enhanced security analysis with OWASP API Security Top 10 checks."""
    suggestions = []
    
    # OWASP API Security Top 10 checks
    security_schemes = spec.get("components", {}).get("securitySchemes", {})
    global_security = spec.get("security", [])
    
    # API1:2019 - Broken Object Level Authorization
    suggestions.extend(_check_broken_object_authorization(spec))
    
    # API2:2019 - Broken User Authentication
    suggestions.extend(_check_broken_authentication(security_schemes, global_security))
    suggestions.extend(_check_sensitive_endpoints_without_auth(spec))
    
    # API3:2019 - Excessive Data Exposure
    suggestions.extend(_check_excessive_data_exposure(spec))
    suggestions.extend(_check_hardcoded_secrets(spec))
    
    # API4:2019 - Lack of Resources & Rate Limiting
    suggestions.extend(_check_rate_limiting(spec))
    suggestions.extend(_check_unvalidated_input_parameters(spec))
    
    # API5:2019 - Broken Function Level Authorization
    suggestions.extend(_check_function_level_authorization(spec))
    
    # API6:2019 - Mass Assignment
    suggestions.extend(_check_mass_assignment(spec))
    
    # API7:2019 - Security Misconfiguration
    suggestions.extend(_check_security_misconfiguration(spec))
    
    # API8:2019 - Injection
    suggestions.extend(_check_injection_vulnerabilities(spec))
    
    # API9:2019 - Improper Assets Management
    suggestions.extend(_check_asset_management(spec))
    
    # API10:2019 - Insufficient Logging & Monitoring
    suggestions.extend(_check_logging_monitoring(spec))
    
    return suggestions

def _check_broken_object_authorization(spec: dict) -> List[str]:
    """Check for broken object level authorization."""
    suggestions = []
    paths = spec.get("paths", {})
    
    for path, methods in paths.items():
        if not isinstance(methods, dict):
            continue
        
        for method, details in methods.items():
            if not isinstance(details, dict):
                continue
            
            # Check for ID-based endpoints without proper authorization
            if "{" in path and "id" in path.lower():
                if not details.get("security"):
                    suggestions.append(f"ID-based endpoint {method.upper()} {path} should have explicit security requirements to prevent unauthorized access to other users' data.")
    
    return suggestions

def _check_broken_authentication(security_schemes: dict, global_security: list) -> List[str]:
    """Check for broken authentication mechanisms."""
    suggestions = []
    
    if not security_schemes:
        suggestions.append("No security schemes defined. Implement proper authentication mechanisms.")
        return suggestions
    
    for scheme_name, scheme in security_schemes.items():
        if not isinstance(scheme, dict):
            continue
            
        scheme_type = scheme.get("type")
        
        if scheme_type == "http":
            scheme_name_val = scheme.get("scheme")
            if scheme_name_val == "bearer":
                if "bearerFormat" not in scheme:
                    suggestions.append(f"Bearer token scheme '{scheme_name}' should specify bearerFormat (e.g., 'JWT').")
            elif scheme_name_val == "basic":
                suggestions.append(f"Basic authentication '{scheme_name}' is insecure. Consider using OAuth2 or API keys.")
        
        elif scheme_type == "apiKey":
            if scheme.get("in") == "query":
                suggestions.append(f"API key '{scheme_name}' in query parameter is insecure. Use header or cookie instead.")
        
        elif scheme_type == "oauth2":
            flows = scheme.get("flows", {})
            if not flows:
                suggestions.append(f"OAuth2 scheme '{scheme_name}' missing flows configuration.")
            else:
                for flow_name, flow_config in flows.items():
                    if not flow_config.get("authorizationUrl") and flow_name in ["implicit", "authorizationCode"]:
                        suggestions.append(f"OAuth2 {flow_name} flow in '{scheme_name}' missing authorizationUrl.")
                    if not flow_config.get("tokenUrl"):
                        suggestions.append(f"OAuth2 {flow_name} flow in '{scheme_name}' missing tokenUrl.")
    
    if not global_security:
        suggestions.append("No global security requirements defined. Consider adding default authentication.")
    
    return suggestions

def _check_sensitive_endpoints_without_auth(spec: dict) -> List[str]:
    """Flag sensitive or destructive endpoints that lack authentication."""
    suggestions = []
    global_security = spec.get("security", [])
    paths = spec.get("paths", {})
    
    sensitive_keywords = ["user", "account", "profile", "admin", "login", "token", "password", "deleteall", "reset"]
    destructive_methods = {"delete"}
    
    for path, methods in paths.items():
        if not isinstance(methods, dict):
            continue
        for method, details in methods.items():
            if not isinstance(details, dict):
                continue
            method_lower = method.lower()
            if method_lower not in ["get", "post", "put", "delete", "patch", "options", "head", "trace"]:
                continue
            
            op_security = details.get("security")
            has_security = bool(global_security) if op_security is None else bool(op_security)
            if has_security:
                continue
            
            path_text = path.lower()
            description_text = f"{details.get('summary', '')} {details.get('description', '')}".lower()
            is_sensitive_route = any(keyword in path_text for keyword in sensitive_keywords) or any(
                keyword in description_text for keyword in sensitive_keywords
            )
            
            responses = details.get("responses", {})
            exposes_sensitive_data = False
            for response in responses.values():
                if not isinstance(response, dict):
                    continue
                content = response.get("content", {})
                for content_spec in content.values():
                    if not isinstance(content_spec, dict):
                        continue
                    schema = content_spec.get("schema")
                    if schema and isinstance(schema, dict):
                        if _find_sensitive_fields(schema):
                            exposes_sensitive_data = True
                            break
                if exposes_sensitive_data:
                    break
            
            is_destructive = method_lower in destructive_methods or "delete all" in description_text
            
            if is_sensitive_route or exposes_sensitive_data or is_destructive:
                reason_parts = []
                if is_sensitive_route:
                    reason_parts.append("is a sensitive endpoint")
                if exposes_sensitive_data:
                    reason_parts.append("returns sensitive data")
                if is_destructive:
                    reason_parts.append("performs destructive operations")
                reason_text = " and ".join(reason_parts) if reason_parts else "is sensitive"
                suggestions.append(f"{method.upper()} {path} {reason_text} but has no security requirements defined.")
    
    return suggestions

def _check_excessive_data_exposure(spec: dict) -> List[str]:
    """Check for excessive data exposure in responses."""
    suggestions = []
    paths = spec.get("paths", {})
    
    for path, methods in paths.items():
        if not isinstance(methods, dict):
            continue
        
        for method, details in methods.items():
            if not isinstance(details, dict):
                continue
            
            responses = details.get("responses", {})
            for code, response in responses.items():
                if not isinstance(response, dict):
                    continue
                
                content = response.get("content", {})
                for content_type, content_spec in content.items():
                    if not isinstance(content_spec, dict):
                        continue
                    
                    schema = content_spec.get("schema")
                    if schema and isinstance(schema, dict):
                        # Check for sensitive fields
                        sensitive_fields = _find_sensitive_fields(schema)
                        if sensitive_fields:
                            suggestions.append(f"Response {code} in {method.upper()} {path} may expose sensitive fields: {', '.join(sensitive_fields)}. Consider filtering or using separate schemas.")
    
    return suggestions

def _find_sensitive_fields(schema: dict, path: str = "") -> List[str]:
    """Recursively find potentially sensitive fields in schema."""
    sensitive_patterns = [
        r'password', r'secret', r'key', r'token', r'auth', r'credential',
        r'ssn', r'social', r'credit', r'card', r'bank', r'account',
        r'email', r'phone', r'address', r'personal', r'private'
    ]
    
    sensitive_fields = []
    
    if isinstance(schema, dict):
        properties = schema.get("properties", {})
        for prop_name, prop_schema in properties.items():
            current_path = f"{path}.{prop_name}" if path else prop_name
            
            # Check if field name matches sensitive patterns
            for pattern in sensitive_patterns:
                if re.search(pattern, prop_name, re.IGNORECASE):
                    sensitive_fields.append(current_path)
            
            # Recursively check nested objects
            if isinstance(prop_schema, dict):
                sensitive_fields.extend(_find_sensitive_fields(prop_schema, current_path))
    
    return sensitive_fields

def _check_rate_limiting(spec: dict) -> List[str]:
    """Check for rate limiting implementation."""
    suggestions = []
    paths = spec.get("paths", {})
    
    rate_limit_extension = spec.get("x-rate-limit")
    if isinstance(rate_limit_extension, str) and rate_limit_extension.lower() in ["none", "unlimited", "disabled"]:
        suggestions.append("Global x-rate-limit extension indicates rate limiting is disabled. Implement rate limiting to prevent abuse.")
    elif isinstance(rate_limit_extension, (int, float)) and rate_limit_extension <= 0:
        suggestions.append("Global x-rate-limit value is non-positive, effectively disabling rate limiting. Configure a realistic limit.")
    
    has_rate_limiting = False
    
    for path, methods in paths.items():
        if not isinstance(methods, dict):
            continue
        
        for method, details in methods.items():
            if not isinstance(details, dict):
                continue
            
            responses = details.get("responses", {})
            for code, response in responses.items():
                if not isinstance(response, dict):
                    continue
                
                headers = response.get("headers", {})
                for header_name in headers.keys():
                    if any(keyword in header_name.lower() for keyword in ["rate", "limit", "quota", "throttle"]):
                        has_rate_limiting = True
                        break
    
    if not has_rate_limiting:
        suggestions.append("No rate limiting headers found. Implement rate limiting to prevent abuse and ensure fair usage.")
    
    return suggestions

def _check_hardcoded_secrets(spec: dict) -> List[str]:
    """Detect hardcoded tokens or secrets in examples."""
    suggestions = []
    sensitive_keywords = ["token", "secret", "password", "apikey", "api_key", "credential"]
    suspicious_markers = ["hardcoded", "changeme", "static", "dummy", "sample"]
    
    def example_is_suspicious(value: str, context: str) -> bool:
        lowered_value = value.lower()
        if not any(marker in lowered_value for marker in suspicious_markers):
            return False
        lowered_context = context.lower()
        return any(keyword in lowered_context for keyword in sensitive_keywords)
    
    def scan_schema(schema: dict, context: str):
        if not isinstance(schema, dict):
            return
        example = schema.get("example")
        if isinstance(example, str) and example_is_suspicious(example, context):
            suggestions.append(f"{context} uses a hardcoded example value '{example}'. Replace with a placeholder to avoid leaking secrets.")
        default = schema.get("default")
        if isinstance(default, str) and example_is_suspicious(default, context):
            suggestions.append(f"{context} uses a hardcoded default value '{default}'. Avoid embedding secrets in specifications.")
        
        examples = schema.get("examples", {})
        if isinstance(examples, dict):
            for ex_name, ex_value in examples.items():
                if isinstance(ex_value, dict):
                    value = ex_value.get("value")
                    if isinstance(value, str) and example_is_suspicious(value, context):
                        suggestions.append(f"{context} example '{ex_name}' contains a hardcoded secret-like value '{value}'.")
        
        properties = schema.get("properties", {})
        if isinstance(properties, dict):
            for prop_name, prop_schema in properties.items():
                scan_schema(prop_schema, f"{context}.{prop_name}")
        
        items = schema.get("items")
        if items:
            scan_schema(items, f"{context}.items")
    
    paths = spec.get("paths", {})
    for path, methods in paths.items():
        if not isinstance(methods, dict):
            continue
        for method, details in methods.items():
            if not isinstance(details, dict):
                continue
            request_body = details.get("requestBody", {})
            if isinstance(request_body, dict):
                content = request_body.get("content", {})
                for ctype, content_spec in content.items():
                    if not isinstance(content_spec, dict):
                        continue
                    schema = content_spec.get("schema")
                    if schema:
                        scan_schema(schema, f"{method.upper()} {path} requestBody {ctype}")
            responses = details.get("responses", {})
            for code, response in responses.items():
                if not isinstance(response, dict):
                    continue
                content = response.get("content", {})
                for ctype, content_spec in content.items():
                    if not isinstance(content_spec, dict):
                        continue
                    schema = content_spec.get("schema")
                    if schema:
                        scan_schema(schema, f"{method.upper()} {path} response {code} {ctype}")
    
    return suggestions

def _check_unvalidated_input_parameters(spec: dict) -> List[str]:
    """Detect parameters that allow unvalidated or weakly validated input."""
    suggestions = []
    paths = spec.get("paths", {})
    wildcard_patterns = {".*", "^.*$", "^.+$", ".+"}
    
    for path, methods in paths.items():
        if not isinstance(methods, dict):
            continue
        for method, details in methods.items():
            if not isinstance(details, dict):
                continue
            parameters = details.get("parameters", [])
            if not isinstance(parameters, list):
                continue
            for param in parameters:
                if not isinstance(param, dict):
                    continue
                schema = param.get("schema") or {}
                if not isinstance(schema, dict):
                    schema = {}
                param_name = param.get("name", "unnamed")
                param_in = param.get("in", "unknown")
                param_type = schema.get("type")
                pattern = schema.get("pattern")
                
                if isinstance(pattern, str) and pattern.strip() in wildcard_patterns:
                    suggestions.append(f"Parameter '{param_name}' in {param_in} for {method.upper()} {path} uses overly permissive pattern '{pattern}'. Provide a stricter pattern or validation rules.")
                
                if param_name.lower().endswith("id"):
                    if param_type and param_type != "integer":
                        suggestions.append(f"Parameter '{param_name}' in {param_in} for {method.upper()} {path} should be an integer but is defined as {param_type}.")
                    elif not param_type:
                        suggestions.append(f"Parameter '{param_name}' in {param_in} for {method.upper()} {path} is missing a type declaration.")
                
                if param_in == "path" and param_type == "string":
                    has_constraints = any(schema.get(key) is not None for key in ["pattern", "format", "minLength", "maxLength", "enum"])
                    if not has_constraints:
                        suggestions.append(f"Path parameter '{param_name}' in {method.upper()} {path} is a free-form string without validation constraints. Add pattern, format, or length restrictions.")
    
    return suggestions

def _check_function_level_authorization(spec: dict) -> List[str]:
    """Check for function level authorization."""
    suggestions = []
    paths = spec.get("paths", {})
    
    for path, methods in paths.items():
        if not isinstance(methods, dict):
            continue
        
        for method, details in methods.items():
            if not isinstance(details, dict):
                continue
            
            # Check for admin/privileged operations
            admin_keywords = ["admin", "delete", "update", "create", "manage", "config"]
            if any(keyword in path.lower() or keyword in method.lower() for keyword in admin_keywords):
                if not details.get("security"):
                    suggestions.append(f"Privileged operation {method.upper()} {path} should have explicit security requirements.")
    
    return suggestions

def _check_mass_assignment(spec: dict) -> List[str]:
    """Check for mass assignment vulnerabilities."""
    suggestions = []
    paths = spec.get("paths", {})
    
    for path, methods in paths.items():
        if not isinstance(methods, dict):
            continue
        
        for method, details in methods.items():
            if not isinstance(details, dict):
                continue
            
            if method.lower() in ["post", "put", "patch"]:
                request_body = details.get("requestBody", {})
                if isinstance(request_body, dict):
                    content = request_body.get("content", {})
                    for content_type, content_spec in content.items():
                        if isinstance(content_spec, dict):
                            schema = content_spec.get("schema")
                            if schema and isinstance(schema, dict):
                                # Check for overly permissive schemas
                                if not schema.get("additionalProperties", True) is False:
                                    suggestions.append(f"Request body for {method.upper()} {path} allows additional properties. Consider restricting to prevent mass assignment attacks.")
    
    return suggestions

def _check_security_misconfiguration(spec: dict) -> List[str]:
    """Check for security misconfigurations."""
    suggestions = []
    
    # Check for HTTP instead of HTTPS
    servers = spec.get("servers", [])
    for server in servers:
        if isinstance(server, dict):
            url = server.get("url", "")
            if url.startswith("http://") and not url.startswith("http://localhost"):
                suggestions.append(f"Server URL '{url}' uses HTTP instead of HTTPS. This is insecure for production APIs.")
    
    # Check for overly permissive CORS
    if "x-cors" in spec:
        cors_config = spec["x-cors"]
        if isinstance(cors_config, dict):
            if cors_config.get("allowOrigin") == "*":
                suggestions.append("CORS configuration allows all origins (*). Consider restricting to specific domains.")
    
    return suggestions

def _check_injection_vulnerabilities(spec: dict) -> List[str]:
    """Check for potential injection vulnerabilities."""
    suggestions = []
    paths = spec.get("paths", {})
    
    for path, methods in paths.items():
        if not isinstance(methods, dict):
            continue
        
        for method, details in methods.items():
            if not isinstance(details, dict):
                continue
            
            parameters = details.get("parameters", [])
            for param in parameters:
                if not isinstance(param, dict):
                    continue
                
                param_name = param.get("name", "")
                param_type = param.get("schema", {}).get("type", "")
                
                # Check for SQL injection patterns
                if any(keyword in param_name.lower() for keyword in ["query", "sql", "search", "filter"]):
                    if param_type == "string":
                        suggestions.append(f"Parameter '{param_name}' in {method.upper()} {path} appears to accept SQL-like queries. Ensure proper input validation and parameterized queries.")
    
    return suggestions

def _check_asset_management(spec: dict) -> List[str]:
    """Check for improper asset management."""
    suggestions = []
    
    # Check for version information
    info = spec.get("info", {})
    version = info.get("version")
    if not version:
        suggestions.append("API version not specified. Proper versioning is crucial for asset management.")
    
    # Check for deprecated operations
    paths = spec.get("paths", {})
    deprecated_ops = []
    
    for path, methods in paths.items():
        if not isinstance(methods, dict):
            continue
        
        for method, details in methods.items():
            if not isinstance(details, dict):
                continue
            
            if details.get("deprecated"):
                deprecated_ops.append(f"{method.upper()} {path}")
    
    if deprecated_ops:
        suggestions.append(f"Deprecated operations found: {', '.join(deprecated_ops)}. Ensure proper deprecation timeline and migration path.")
    
    return suggestions

def _check_logging_monitoring(spec: dict) -> List[str]:
    """Check for logging and monitoring capabilities."""
    suggestions = []
    
    # Check for health check endpoints
    paths = spec.get("paths", {})
    has_health_check = False
    
    for path in paths.keys():
        if any(keyword in path.lower() for keyword in ["health", "status", "ping", "ready", "live"]):
            has_health_check = True
            break
    
    if not has_health_check:
        suggestions.append("No health check endpoint found. Add /health or /status endpoint for monitoring.")
    
    # Check for proper error responses
    has_proper_errors = False
    for path, methods in paths.items():
        if not isinstance(methods, dict):
            continue
        
        for method, details in methods.items():
            if not isinstance(details, dict):
                continue
            
            responses = details.get("responses", {})
            if "500" in responses or "4xx" in responses:
                has_proper_errors = True
                break
    
    if not has_proper_errors:
        suggestions.append("Missing proper error response definitions. Add 4xx and 5xx error responses for better monitoring.")
    
    return suggestions

def analyze_performance(spec: dict) -> List[str]:
    """Analyze API performance characteristics."""
    suggestions = []
    paths = spec.get("paths", {})
    
    # Analyze response complexity
    for path, methods in paths.items():
        if not isinstance(methods, dict):
            continue
        
        for method, details in methods.items():
            if not isinstance(details, dict):
                continue
            
            # Check for large response schemas
            responses = details.get("responses", {})
            for code, response in responses.items():
                if not isinstance(response, dict):
                    continue
                
                content = response.get("content", {})
                for content_type, content_spec in content.items():
                    if isinstance(content_spec, dict):
                        schema = content_spec.get("schema")
                        if schema:
                            complexity = _calculate_schema_complexity(schema)
                            if complexity > 50:  # Threshold for complex schemas
                                suggestions.append(f"Response {code} in {method.upper()} {path} has high complexity ({complexity}). Consider pagination or field selection.")
            
            # Check for missing caching headers
            if method.lower() == "get":
                has_cache_headers = False
                for code, response in responses.items():
                    if isinstance(response, dict):
                        headers = response.get("headers", {})
                        for header_name in headers.keys():
                            if any(keyword in header_name.lower() for keyword in ["cache", "etag", "last-modified"]):
                                has_cache_headers = True
                                break
                
                if not has_cache_headers:
                    suggestions.append(f"GET operation {path} should include caching headers (Cache-Control, ETag, Last-Modified) for better performance.")
    
    return suggestions

def _calculate_schema_complexity(schema: dict, depth: int = 0) -> int:
    """Calculate schema complexity score."""
    if depth > 10:  # Prevent infinite recursion
        return 0
    
    if not isinstance(schema, dict):
        return 1
    
    complexity = 1
    
    # Count properties
    properties = schema.get("properties", {})
    if isinstance(properties, dict):
        complexity += len(properties)
        for prop_schema in properties.values():
            if isinstance(prop_schema, dict):
                complexity += _calculate_schema_complexity(prop_schema, depth + 1)
    
    # Count array items
    items = schema.get("items")
    if isinstance(items, dict):
        complexity += _calculate_schema_complexity(items, depth + 1)
    
    # Count composition schemas
    for comp_type in ["allOf", "oneOf", "anyOf"]:
        comp_schemas = schema.get(comp_type, [])
        if isinstance(comp_schemas, list):
            for comp_schema in comp_schemas:
                if isinstance(comp_schema, dict):
                    complexity += _calculate_schema_complexity(comp_schema, depth + 1)
    
    return complexity

def analyze_api_design_patterns(spec: dict) -> List[str]:
    """Analyze API design patterns and RESTful compliance."""
    suggestions = []
    paths = spec.get("paths", {})
    
    # Check for RESTful patterns
    resource_patterns = defaultdict(list)
    
    for path in paths.keys():
        if not isinstance(path, str):
            continue
        
        # Extract resource name from path
        path_parts = [p for p in path.split("/") if p and not p.startswith("{")]
        if path_parts:
            resource = path_parts[0]
            resource_patterns[resource].append(path)
    
    # Check for CRUD completeness
    for resource, resource_paths in resource_patterns.items():
        methods_found = set()
        
        for path in resource_paths:
            methods = paths.get(path, {})
            if isinstance(methods, dict):
                methods_found.update(methods.keys())
        
        # Check for standard CRUD operations
        expected_operations = {
            "get": f"GET /{resource} (list)",
            "post": f"POST /{resource} (create)",
            "get_id": f"GET /{resource}/{{id}} (read)",
            "put": f"PUT /{resource}/{{id}} (update)",
            "delete": f"DELETE /{resource}/{{id}} (delete)"
        }
        
        for op_type, description in expected_operations.items():
            if op_type == "get_id":
                has_get_by_id = any(f"/{resource}/{{" in path for path in resource_paths)
                if not has_get_by_id:
                    suggestions.append(f"Missing {description} for resource '{resource}'.")
            elif op_type not in methods_found:
                if op_type == "get" and f"/{resource}" in resource_paths:
                    continue  # List endpoint exists
                suggestions.append(f"Missing {description} for resource '{resource}'.")
    
    # Check for consistent naming
    naming_issues = _check_naming_consistency(paths)
    suggestions.extend(naming_issues)
    
    # Check for proper HTTP methods
    method_issues = _check_http_method_usage(paths)
    suggestions.extend(method_issues)
    
    return suggestions

def _check_naming_consistency(paths: dict) -> List[str]:
    """Check for consistent naming conventions."""
    suggestions = []
    
    # Check for consistent path naming
    path_styles = set()
    for path in paths.keys():
        if not isinstance(path, str):
            continue
        
        if "-" in path:
            path_styles.add("kebab-case")
        elif "_" in path:
            path_styles.add("snake_case")
        elif any(c.isupper() for c in path):
            path_styles.add("camelCase")
        else:
            path_styles.add("lowercase")
    
    if len(path_styles) > 1:
        suggestions.append(f"Inconsistent path naming styles detected: {', '.join(path_styles)}. Choose one style and apply consistently.")
    
    return suggestions

def _check_http_method_usage(paths: dict) -> List[str]:
    """Check for proper HTTP method usage."""
    suggestions = []
    
    for path, methods in paths.items():
        if not isinstance(methods, dict):
            continue
        
        for method, details in methods.items():
            if not isinstance(details, dict):
                continue
            
            method_lower = method.lower()
            
            # Check for inappropriate method usage
            if method_lower == "get" and details.get("requestBody"):
                suggestions.append(f"GET operation {path} should not have a request body.")
            
            if method_lower == "delete" and details.get("requestBody"):
                suggestions.append(f"DELETE operation {path} typically should not have a request body.")
            
            # Check for idempotent operations
            if method_lower in ["put", "delete"]:
                description = details.get("description", "").lower()
                if "idempotent" not in description:
                    suggestions.append(f"{method.upper()} operation {path} should document idempotent behavior.")
    
    return suggestions

def analyze_versioning(spec: dict) -> List[str]:
    """Analyze API versioning strategy."""
    suggestions = []
    
    # Check version in info
    info = spec.get("info", {})
    version = info.get("version")
    if not version:
        suggestions.append("API version not specified in info.version.")
    else:
        # Check version format
        if not re.match(r'^\d+\.\d+(\.\d+)?(-[a-zA-Z0-9]+)?$', version):
            suggestions.append(f"Version '{version}' should follow semantic versioning (e.g., '1.0.0', '2.1.0-beta').")
    
    # Check for version in URL
    servers = spec.get("servers", [])
    has_version_in_url = False
    
    for server in servers:
        if isinstance(server, dict):
            url = server.get("url", "")
            if "/v" in url or "/version" in url:
                has_version_in_url = True
                break
    
    if not has_version_in_url:
        suggestions.append("Consider including version in server URLs (e.g., 'https://api.example.com/v1').")
    
    # Check for deprecated operations
    paths = spec.get("paths", {})
    deprecated_count = 0
    
    for path, methods in paths.items():
        if not isinstance(methods, dict):
            continue
        
        for method, details in methods.items():
            if not isinstance(details, dict):
                continue
            
            if details.get("deprecated"):
                deprecated_count += 1
    
    if deprecated_count > 0:
        suggestions.append(f"Found {deprecated_count} deprecated operations. Ensure proper deprecation timeline and migration documentation.")
    
    return suggestions

def analyze_documentation_quality(spec: dict) -> List[str]:
    """Analyze documentation quality and completeness."""
    suggestions = []
    
    # Check info section
    info = spec.get("info", {})
    if not info.get("title"):
        suggestions.append("API title is missing. Add a clear, descriptive title.")
    
    if not info.get("description"):
        suggestions.append("API description is missing. Add a comprehensive description of the API's purpose and functionality.")
    
    if not info.get("version"):
        suggestions.append("API version is missing. Specify the current version.")
    
    # Check for contact information
    if not info.get("contact"):
        suggestions.append("Contact information is missing. Add contact details for API support.")
    
    if not info.get("license"):
        suggestions.append("License information is missing. Specify the API license.")
    
    # Check operation documentation
    paths = spec.get("paths", {})
    for path, methods in paths.items():
        if not isinstance(methods, dict):
            continue
        
        for method, details in methods.items():
            if not isinstance(details, dict):
                continue
            
            # Check operation documentation
            if not details.get("summary"):
                suggestions.append(f"Operation {method.upper()} {path} missing summary.")
            
            if not details.get("description"):
                suggestions.append(f"Operation {method.upper()} {path} missing description.")
            
            # Check for examples
            if not details.get("examples") and not details.get("example"):
                suggestions.append(f"Operation {method.upper()} {path} missing examples.")
            
            # Check parameter documentation
            parameters = details.get("parameters", [])
            for param in parameters:
                if not isinstance(param, dict):
                    continue
                
                if not param.get("description"):
                    suggestions.append(f"Parameter {param.get('name', 'unknown')} in {method.upper()} {path} missing description.")
                
                if not param.get("example") and not param.get("examples"):
                    suggestions.append(f"Parameter {param.get('name', 'unknown')} in {method.upper()} {path} missing example.")
    
    return suggestions

def analyze_compliance(spec: dict) -> List[str]:
    """Analyze compliance with various standards and regulations."""
    suggestions = []
    
    # GDPR compliance checks
    gdpr_issues = _check_gdpr_compliance(spec)
    suggestions.extend(gdpr_issues)
    
    # Accessibility checks
    accessibility_issues = _check_accessibility(spec)
    suggestions.extend(accessibility_issues)
    
    # Industry-specific compliance
    industry_issues = _check_industry_compliance(spec)
    suggestions.extend(industry_issues)
    
    return suggestions

def _check_gdpr_compliance(spec: dict) -> List[str]:
    """Check GDPR compliance."""
    suggestions = []
    
    # Check for personal data handling
    paths = spec.get("paths", {})
    personal_data_endpoints = []
    
    for path, methods in paths.items():
        if not isinstance(methods, dict):
            continue
        
        for method, details in methods.items():
            if not isinstance(details, dict):
                continue
            
            # Check for personal data keywords
            personal_keywords = ["user", "profile", "account", "personal", "email", "phone", "address"]
            if any(keyword in path.lower() for keyword in personal_keywords):
                personal_data_endpoints.append(f"{method.upper()} {path}")
    
    if personal_data_endpoints:
        suggestions.append(f"Endpoints handling personal data found: {', '.join(personal_data_endpoints)}. Ensure GDPR compliance for data processing, consent, and data subject rights.")
    
    return suggestions

def _check_accessibility(spec: dict) -> List[str]:
    """Check accessibility compliance."""
    suggestions = []
    
    # Check for error message accessibility
    paths = spec.get("paths", {})
    for path, methods in paths.items():
        if not isinstance(methods, dict):
            continue
        
        for method, details in methods.items():
            if not isinstance(details, dict):
                continue
            
            responses = details.get("responses", {})
            for code, response in responses.items():
                if not isinstance(response, dict):
                    continue
                
                if code.startswith("4") or code.startswith("5"):
                    description = response.get("description", "")
                    if not description or len(description) < 10:
                        suggestions.append(f"Error response {code} in {method.upper()} {path} should have clear, accessible error descriptions.")
    
    return suggestions

def _check_industry_compliance(spec: dict) -> List[str]:
    """Check industry-specific compliance."""
    suggestions = []
    
    # Check for healthcare-related endpoints (HIPAA)
    paths = spec.get("paths", {})
    healthcare_keywords = ["patient", "medical", "health", "diagnosis", "treatment", "pharmacy"]
    
    has_healthcare_data = False
    for path in paths.keys():
        if any(keyword in path.lower() for keyword in healthcare_keywords):
            has_healthcare_data = True
            break
    
    if has_healthcare_data:
        suggestions.append("Healthcare-related endpoints detected. Ensure HIPAA compliance for protected health information (PHI).")
    
    # Check for payment-related endpoints (PCI-DSS)
    payment_keywords = ["payment", "card", "billing", "invoice", "transaction", "charge"]
    
    has_payment_data = False
    for path in paths.keys():
        if any(keyword in path.lower() for keyword in payment_keywords):
            has_payment_data = True
            break
    
    if has_payment_data:
        suggestions.append("Payment-related endpoints detected. Ensure PCI-DSS compliance for payment card data.")
    
    return suggestions

def analyze_testing_recommendations(spec: dict) -> List[str]:
    """Generate testing strategy recommendations."""
    suggestions = []
    
    paths = spec.get("paths", {})
    operations_count = 0
    test_scenarios = []
    
    for path, methods in paths.items():
        if not isinstance(methods, dict):
            continue
        
        for method, details in methods.items():
            if not isinstance(details, dict):
                continue
            
            operations_count += 1
            
            # Generate test scenarios
            test_scenarios.append(f"Test {method.upper()} {path} with valid data")
            test_scenarios.append(f"Test {method.upper()} {path} with invalid data")
            test_scenarios.append(f"Test {method.upper()} {path} with missing required fields")
            
            # Check for authentication requirements
            if details.get("security"):
                test_scenarios.append(f"Test {method.upper()} {path} with invalid authentication")
                test_scenarios.append(f"Test {method.upper()} {path} with expired tokens")
    
    if test_scenarios:
        suggestions.append(f"Recommended test scenarios ({len(test_scenarios)} total): {', '.join(test_scenarios[:5])}{'...' if len(test_scenarios) > 5 else ''}")
    
    # Mock data recommendations
    suggestions.append("Generate mock data for all request/response schemas to enable comprehensive testing.")
    
    # Contract testing
    suggestions.append("Implement contract testing to ensure API compatibility across versions.")
    
    # Load testing
    suggestions.append("Perform load testing to validate performance under expected traffic.")
    
    return suggestions

def analyze_monitoring_observability(spec: dict) -> List[str]:
    """Analyze monitoring and observability requirements."""
    suggestions = []
    
    # Check for health check endpoints
    paths = spec.get("paths", {})
    has_health_check = False
    
    for path in paths.keys():
        if any(keyword in path.lower() for keyword in ["health", "status", "ping", "ready", "live"]):
            has_health_check = True
            break
    
    if not has_health_check:
        suggestions.append("Add health check endpoint (e.g., /health, /status) for monitoring system health.")
    
    # Check for metrics endpoints
    has_metrics = any("metrics" in path.lower() for path in paths.keys())
    if not has_metrics:
        suggestions.append("Consider adding metrics endpoint (e.g., /metrics) for Prometheus-style monitoring.")
    
    # Check for proper error responses
    has_error_responses = False
    for path, methods in paths.items():
        if not isinstance(methods, dict):
            continue
        
        for method, details in methods.items():
            if not isinstance(details, dict):
                continue
            
            responses = details.get("responses", {})
            if "500" in responses or any(code.startswith("4") for code in responses.keys()):
                has_error_responses = True
                break
    
    if not has_error_responses:
        suggestions.append("Add proper error response definitions (4xx, 5xx) for better error tracking and monitoring.")
    
    # Logging recommendations
    suggestions.append("Implement structured logging with correlation IDs for request tracing.")
    suggestions.append("Add performance metrics collection (response times, throughput, error rates).")
    suggestions.append("Set up alerting for error rates, response times, and system health.")
    
    return suggestions

def analyze_code_generation(spec: dict) -> List[str]:
    """Analyze code generation opportunities."""
    suggestions = []
    
    # Check for client SDK generation
    suggestions.append("Generate client SDKs for popular languages (JavaScript, Python, Java, C#).")
    
    # Check for server stub generation
    suggestions.append("Generate server stubs for common frameworks (Express.js, Flask, Spring Boot).")
    
    # TypeScript types
    suggestions.append("Generate TypeScript type definitions for better developer experience.")
    
    # Database models
    schemas = spec.get("components", {}).get("schemas", {})
    if schemas:
        suggestions.append(f"Generate database models from {len(schemas)} schemas for ORM frameworks.")
    
    # API documentation
    suggestions.append("Generate interactive API documentation (Swagger UI, ReDoc).")
    
    # Mock servers
    suggestions.append("Generate mock server implementations for testing and development.")
    
    return suggestions

def analyze_api_governance(spec: dict) -> List[str]:
    """Analyze API governance and consistency."""
    suggestions = []
    
    # Check naming consistency
    paths = spec.get("paths", {})
    path_styles = set()
    method_consistency = defaultdict(list)
    
    for path, methods in paths.items():
        if not isinstance(path, str):
            continue
        
        # Check path naming style
        if "-" in path:
            path_styles.add("kebab-case")
        elif "_" in path:
            path_styles.add("snake_case")
        elif any(c.isupper() for c in path):
            path_styles.add("camelCase")
        else:
            path_styles.add("lowercase")
        
        # Check method consistency
        if isinstance(methods, dict):
            for method in methods.keys():
                method_consistency[method].append(path)
    
    if len(path_styles) > 1:
        suggestions.append(f"Inconsistent path naming styles: {', '.join(path_styles)}. Standardize on one style.")
    
    # Check for operation ID consistency
    operation_ids = []
    for path, methods in paths.items():
        if not isinstance(methods, dict):
            continue
        
        for method, details in methods.items():
            if not isinstance(details, dict):
                continue
            
            op_id = details.get("operationId")
            if op_id:
                operation_ids.append(op_id)
    
    if len(set(operation_ids)) != len(operation_ids):
        suggestions.append("Duplicate operation IDs found. Ensure all operation IDs are unique.")
    
    # Check for consistent response patterns
    response_patterns = defaultdict(list)
    for path, methods in paths.items():
        if not isinstance(methods, dict):
            continue
        
        for method, details in methods.items():
            if not isinstance(details, dict):
                continue
            
            responses = details.get("responses", {})
            for code in responses.keys():
                response_patterns[code].append(f"{method.upper()} {path}")
    
    # Check for consistent error handling
    common_error_codes = ["400", "401", "403", "404", "500"]
    for code in common_error_codes:
        if code not in response_patterns:
            suggestions.append(f"Consider adding consistent {code} error responses across all operations.")
    
    return suggestions

def analyze_advanced_analytics(spec: dict) -> Dict[str, Any]:
    """Perform advanced analytics and generate insights."""
    analytics = {
        "complexity_score": 0,
        "complexity_level": "",
        "complexity_description": "",
        "maintainability_score": 0,
        "maintainability_level": "",
        "maintainability_description": "",
        "technical_debt": [],
        "refactoring_recommendations": [],
        "architecture_insights": []
    }
    
    paths = spec.get("paths", {})
    schemas = spec.get("components", {}).get("schemas", {})
    
    # Calculate complexity score
    total_operations = 0
    total_paths = len(paths)
    total_schemas = len(schemas)
    
    for path, methods in paths.items():
        if isinstance(methods, dict):
            total_operations += len(methods)
    
    # Complexity factors
    complexity_factors = {
        "operations": total_operations * 2,
        "paths": total_paths * 1,
        "schemas": total_schemas * 3,
        "nested_schemas": _count_nested_schemas(schemas) * 2
    }
    
    complexity_score = sum(complexity_factors.values())
    analytics["complexity_score"] = complexity_score
    
    # Interpret complexity score
    if complexity_score <= 50:
        analytics["complexity_level"] = "Very Low"
        analytics["complexity_description"] = "Simple API with minimal complexity. Easy to understand and maintain."
    elif complexity_score <= 100:
        analytics["complexity_level"] = "Low"
        analytics["complexity_description"] = "Simple to moderate complexity. Well-structured and manageable."
    elif complexity_score <= 200:
        analytics["complexity_level"] = "Moderate"
        analytics["complexity_description"] = "Moderate complexity. Some areas may need attention but generally manageable."
    elif complexity_score <= 400:
        analytics["complexity_level"] = "High"
        analytics["complexity_description"] = "High complexity. Consider breaking down into smaller components."
    elif complexity_score <= 600:
        analytics["complexity_level"] = "Very High"
        analytics["complexity_description"] = "Very high complexity. Significant refactoring recommended."
    else:
        analytics["complexity_level"] = "Extreme"
        analytics["complexity_description"] = "Extreme complexity. Major architectural changes needed."
    
    # Calculate maintainability score (inverse of complexity)
    max_complexity = 1000  # Arbitrary max
    maintainability_score = max(0, 100 - (complexity_score / max_complexity * 100))
    analytics["maintainability_score"] = round(maintainability_score, 1)
    
    # Interpret maintainability score
    if maintainability_score >= 90:
        analytics["maintainability_level"] = "Excellent"
        analytics["maintainability_description"] = "Very easy to maintain. Well-structured and documented."
    elif maintainability_score >= 80:
        analytics["maintainability_level"] = "Good"
        analytics["maintainability_description"] = "Easy to maintain with minor improvements needed."
    elif maintainability_score >= 70:
        analytics["maintainability_level"] = "Fair"
        analytics["maintainability_description"] = "Some complexity but manageable. Consider improvements."
    elif maintainability_score >= 60:
        analytics["maintainability_level"] = "Poor"
        analytics["maintainability_description"] = "Difficult to maintain. Refactoring recommended."
    elif maintainability_score >= 50:
        analytics["maintainability_level"] = "Bad"
        analytics["maintainability_description"] = "Very difficult to maintain. Significant refactoring needed."
    else:
        analytics["maintainability_level"] = "Terrible"
        analytics["maintainability_description"] = "Extremely difficult to maintain. Major architectural changes required."
    
    # Identify technical debt
    if complexity_score > 500:
        analytics["technical_debt"].append("High complexity detected. Consider breaking down into smaller, focused APIs.")
    
    if total_operations > 50:
        analytics["technical_debt"].append("Large number of operations. Consider API versioning and modularization.")
    
    # Refactoring recommendations
    if maintainability_score < 50:
        analytics["refactoring_recommendations"].append("Low maintainability score. Focus on reducing complexity and improving documentation.")
    
    # Architecture insights
    if total_schemas > 20:
        analytics["architecture_insights"].append("Large schema count suggests complex domain model. Consider domain-driven design principles.")
    
    return analytics

def _count_nested_schemas(schemas: dict) -> int:
    """Count nested schema references."""
    count = 0
    for schema in schemas.values():
        if isinstance(schema, dict):
            count += _count_refs_in_schema(schema)
    return count

def _count_refs_in_schema(schema: dict) -> int:
    """Recursively count $ref references in schema."""
    count = 0
    if isinstance(schema, dict):
        if "$ref" in schema:
            count += 1
        for value in schema.values():
            if isinstance(value, dict):
                count += _count_refs_in_schema(value)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        count += _count_refs_in_schema(item)
    return count

# --- Analyzer Core ---

def analyze_openapi_spec(spec: dict) -> Dict[str, Any]:
    """Analyze an OpenAPI specification dictionary with comprehensive best practices analysis."""
    suggestions: List[str] = []
    
    # Normalize v2 specs to v3-like structure for consistent checks
    original_version = spec.get("openapi") or spec.get("swagger")
    if _is_openapi_v2(spec):
        spec = _normalize_v2_to_v3ish(spec)
    
    suggestions.extend(_validate_with_openapi_spec_validator(spec))

    info = spec.get("info", {})
    if not info.get("title"):
        suggestions.append("Spec is missing an API title.")
    if not info.get("description"):
        suggestions.append("Spec should include a description.")
    if not info.get("version"):
        suggestions.append("Spec should define an API version.")

    openapi_version = spec.get("openapi") or original_version
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

    # Count operations once while iterating
    operations_count = 0
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

    # === ADVANCED ANALYSIS FEATURES ===
    
    # Enhanced Security Analysis (OWASP API Security Top 10)
    security_suggestions = analyze_security_enhanced(spec)
    suggestions.extend(security_suggestions)
    
    # Performance Analysis
    performance_suggestions = analyze_performance(spec)
    suggestions.extend(performance_suggestions)
    
    # API Design Pattern Analysis
    design_suggestions = analyze_api_design_patterns(spec)
    suggestions.extend(design_suggestions)
    
    # Versioning Analysis
    versioning_suggestions = analyze_versioning(spec)
    suggestions.extend(versioning_suggestions)
    
    # Documentation Quality Analysis
    doc_suggestions = analyze_documentation_quality(spec)
    suggestions.extend(doc_suggestions)
    
    # Compliance Analysis
    compliance_suggestions = analyze_compliance(spec)
    suggestions.extend(compliance_suggestions)
    
    # Testing Recommendations
    testing_suggestions = analyze_testing_recommendations(spec)
    suggestions.extend(testing_suggestions)
    
    # Monitoring & Observability
    monitoring_suggestions = analyze_monitoring_observability(spec)
    suggestions.extend(monitoring_suggestions)
    
    # Code Generation Opportunities
    codegen_suggestions = analyze_code_generation(spec)
    suggestions.extend(codegen_suggestions)
    
    # API Governance
    governance_suggestions = analyze_api_governance(spec)
    suggestions.extend(governance_suggestions)
    
    # Advanced Analytics
    analytics = analyze_advanced_analytics(spec)

    # Group suggestions by category
    suggestions = {
        "Security": security_suggestions,
        "Performance": performance_suggestions,
        "Design Patterns": design_suggestions,
        "Versioning": versioning_suggestions,
        "Documentation": doc_suggestions,
        "Compliance": compliance_suggestions,
        "Testing": testing_suggestions,
        "Monitoring": monitoring_suggestions,
        "Code Generation": codegen_suggestions,
        "Governance": governance_suggestions,
        "Basic Validation": [s for s in [s for s in suggestions if s not in security_suggestions + performance_suggestions + design_suggestions + versioning_suggestions + doc_suggestions + compliance_suggestions + testing_suggestions + monitoring_suggestions + codegen_suggestions + governance_suggestions] if len(s) < 500 and not any(indicator in s for indicator in ["Spec validation:", "Failed validating", "do not match any of the regexes", "additionalProperties", "patternProperties", "Proxy at 0x", "functools.partial", "get_schema_content"])]
    }
    
    # Remove empty categories
    suggestions = {k: v for k, v in suggestions.items() if v}

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
        "analytics": analytics,
        "analysis_categories": {
            "security": len([s for s in security_suggestions]),
            "performance": len([s for s in performance_suggestions]),
            "design_patterns": len([s for s in design_suggestions]),
            "versioning": len([s for s in versioning_suggestions]),
            "documentation": len([s for s in doc_suggestions]),
            "compliance": len([s for s in compliance_suggestions]),
            "testing": len([s for s in testing_suggestions]),
            "monitoring": len([s for s in monitoring_suggestions]),
            "code_generation": len([s for s in codegen_suggestions]),
            "governance": len([s for s in governance_suggestions])
        }
    }

def analyze_openapi_url(url: str) -> Dict[str, Any]:
    errors: List[str] = []
    suggestions: List[str] = []

    try:
        resp = requests.get(url, timeout=30, allow_redirects=True)
        resp.raise_for_status()
        # Extract filename from URL if possible to help with format detection
        url_path = urlparse(url).path
        file_path_from_url = url_path.split('/')[-1] if url_path else None
        spec, parse_suggestions = _load_openapi_from_bytes(resp.content, file_path=file_path_from_url)
        suggestions.extend(parse_suggestions)
    except requests.RequestException as e:
        return {"status": "error", "errors": [f"Failed to fetch URL: {e}"], "is_valid": False}

    if not spec:
        return {"status": "error", "errors": errors, "is_valid": False}

    # Normalize v2 specs to v3-like structure for consistent checks
    original_version = spec.get("openapi") or spec.get("swagger")
    if _is_openapi_v2(spec):
        spec = _normalize_v2_to_v3ish(spec)

    suggestions.extend(_validate_with_openapi_spec_validator(spec))

    info = spec.get("info", {})
    if not info.get("title"):
        suggestions.append("Spec is missing an API title.")
    if not info.get("description"):
        suggestions.append("Spec should include a description.")
    if not info.get("version"):
        suggestions.append("Spec should define an API version.")

    openapi_version = spec.get("openapi") or original_version
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

    operations_count = 0
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

    # === ADVANCED ANALYSIS FEATURES ===
    
    # Enhanced Security Analysis (OWASP API Security Top 10)
    security_suggestions = analyze_security_enhanced(spec)
    suggestions.extend(security_suggestions)
    
    # Performance Analysis
    performance_suggestions = analyze_performance(spec)
    suggestions.extend(performance_suggestions)
    
    # API Design Pattern Analysis
    design_suggestions = analyze_api_design_patterns(spec)
    suggestions.extend(design_suggestions)
    
    # Versioning Analysis
    versioning_suggestions = analyze_versioning(spec)
    suggestions.extend(versioning_suggestions)
    
    # Documentation Quality Analysis
    doc_suggestions = analyze_documentation_quality(spec)
    suggestions.extend(doc_suggestions)
    
    # Compliance Analysis
    compliance_suggestions = analyze_compliance(spec)
    suggestions.extend(compliance_suggestions)
    
    # Testing Recommendations
    testing_suggestions = analyze_testing_recommendations(spec)
    suggestions.extend(testing_suggestions)
    
    # Monitoring & Observability
    monitoring_suggestions = analyze_monitoring_observability(spec)
    suggestions.extend(monitoring_suggestions)
    
    # Code Generation Opportunities
    codegen_suggestions = analyze_code_generation(spec)
    suggestions.extend(codegen_suggestions)
    
    # API Governance
    governance_suggestions = analyze_api_governance(spec)
    suggestions.extend(governance_suggestions)
    
    # Advanced Analytics
    analytics = analyze_advanced_analytics(spec)

    # Group suggestions by category
    suggestions = {
        "Security": security_suggestions,
        "Performance": performance_suggestions,
        "Design Patterns": design_suggestions,
        "Versioning": versioning_suggestions,
        "Documentation": doc_suggestions,
        "Compliance": compliance_suggestions,
        "Testing": testing_suggestions,
        "Monitoring": monitoring_suggestions,
        "Code Generation": codegen_suggestions,
        "Governance": governance_suggestions,
        "Basic Validation": [s for s in [s for s in suggestions if s not in security_suggestions + performance_suggestions + design_suggestions + versioning_suggestions + doc_suggestions + compliance_suggestions + testing_suggestions + monitoring_suggestions + codegen_suggestions + governance_suggestions] if len(s) < 500 and not any(indicator in s for indicator in ["Spec validation:", "Failed validating", "do not match any of the regexes", "additionalProperties", "patternProperties", "Proxy at 0x", "functools.partial", "get_schema_content"])]
    }
    
    # Remove empty categories
    suggestions = {k: v for k, v in suggestions.items() if v}

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
        "analytics": analytics,
        "analysis_categories": {
            "security": len([s for s in security_suggestions]),
            "performance": len([s for s in performance_suggestions]),
            "design_patterns": len([s for s in design_suggestions]),
            "versioning": len([s for s in versioning_suggestions]),
            "documentation": len([s for s in doc_suggestions]),
            "compliance": len([s for s in compliance_suggestions]),
            "testing": len([s for s in testing_suggestions]),
            "monitoring": len([s for s in monitoring_suggestions]),
            "code_generation": len([s for s in codegen_suggestions]),
            "governance": len([s for s in governance_suggestions])
        }
    }


# --- CLI Entrypoint ---

def analyze_local_file(file_path: str) -> Dict[str, Any]:
    """Analyze a local OpenAPI file."""
    if os.getenv("GITHUB_WORKSPACE"):
        if not os.path.isabs(file_path):
            file_path = os.path.join(os.getenv("GITHUB_WORKSPACE"), file_path)
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        spec, parse_suggestions = _load_openapi_from_bytes(content.encode('utf-8'), file_path=file_path)
        
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
    parser = argparse.ArgumentParser(description="OpenAPI Analyzer - Analyze OpenAPI specifications")
    parser.add_argument("input", nargs="?", help="OpenAPI URL, repository (owner/repo), or local file path")
    parser.add_argument("--url", help="OpenAPI specification URL")
    parser.add_argument("--repo", help="GitHub repository (owner/repo)")
    parser.add_argument("--file", help="Local OpenAPI file path")
    parser.add_argument("--token", help="GitHub token for private repositories")
    parser.add_argument("--output", choices=["json", "summary"], default="json", help="Output format")
    
    args = parser.parse_args()
    
    url = os.getenv("INPUT_SPEC_URL")
    repo = os.getenv("INPUT_REPOSITORY")
    file_path = os.getenv("INPUT_FILE")
    token = os.getenv("INPUT_GITHUB_TOKEN")
    
    if args.url:
        url = args.url
    if args.repo:
        repo = args.repo
    if args.file:
        file_path = args.file
    if args.token:
        token = args.token
    
    if args.input and not url and not repo and not file_path:
        if "/" in args.input and not args.input.startswith("http") and not os.path.exists(args.input):
            repo = args.input
        elif os.path.exists(args.input):
            file_path = args.input
        else:
            url = args.input
    
    if not url and not repo and not file_path:
        print("Usage: python analyzer.py <openapi-url>")
        print("       python analyzer.py --repo owner/repo")
        print("       python analyzer.py --url <openapi-url>")
        print("       python analyzer.py --file <local-file-path>")
        print("       python analyzer.py <local-file-path>")
        print("Or set INPUT_SPEC_URL or INPUT_REPOSITORY environment variable for GitHub Actions")
        sys.exit(1)
    
    if url:
        result = analyze_openapi_url(url)
    elif repo:
        if "/" not in repo:
            print("Repository must be in format 'owner/repo'")
            sys.exit(1)
        
        owner, repo_name = repo.split("/", 1)
        result = analyze_repository_openapi(owner, repo_name, token)
    elif file_path:
        result = analyze_local_file(file_path)
    else:
        print("No input provided")
        sys.exit(1)
    
    if os.getenv("GITHUB_ACTIONS"):
        def set_output(name: str, value: str):
            print(f"::set-output name={name}::{value}")
        
        set_output("analysis", json.dumps(result))
        set_output("is_valid", str(result.get("is_valid", False)).lower())
        
        # Calculate total suggestions from grouped suggestions
        suggestions = result.get("suggestions", {})
        total_suggestions = sum(len(suggestion_list) for suggestion_list in suggestions.values())
        set_output("suggestions_count", str(total_suggestions))
        
        if "summary" in result:
            summary = result.get("summary", {})
            set_output("operations_count", str(summary.get("operations_count", 0)))
            set_output("paths_count", str(summary.get("paths_count", 0)))
            set_output("schemas_count", str(summary.get("schemas_count", 0)))
        
        # Advanced analytics outputs
        analytics = result.get("analytics", {})
        set_output("complexity_score", str(analytics.get("complexity_score", 0)))
        set_output("maintainability_score", str(analytics.get("maintainability_score", 0)))

        # Analysis categories
        categories = result.get("analysis_categories", {})
        set_output("security_issues", str(categories.get("security", 0)))
        set_output("performance_issues", str(categories.get("performance", 0)))
        set_output("design_pattern_issues", str(categories.get("design_patterns", 0)))
        set_output("versioning_issues", str(categories.get("versioning", 0)))
        set_output("documentation_issues", str(categories.get("documentation", 0)))
        set_output("compliance_issues", str(categories.get("compliance", 0)))
        set_output("testing_recommendations", str(categories.get("testing", 0)))
        set_output("monitoring_recommendations", str(categories.get("monitoring", 0)))
        set_output("code_generation_opportunities", str(categories.get("code_generation", 0)))
        set_output("governance_issues", str(categories.get("governance", 0)))
        
        if "repository" in result:
            repo_info = result["repository"]
            set_output("repository_name", repo_info.get("name", ""))
            set_output("repository_full_name", repo_info.get("full_name", ""))
            set_output("repository_url", repo_info.get("url", ""))
            set_output("repository_stars", str(repo_info.get("stars", 0)))
            set_output("repository_forks", str(repo_info.get("forks", 0)))
    
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
