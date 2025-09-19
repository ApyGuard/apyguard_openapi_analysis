import json
import os
import sys
import requests
import yaml
from typing import Any, Dict, List, Optional, Tuple

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


# --- Analyzer Core (all your checks preserved) ---

def analyze_openapi_url(url: str) -> Dict[str, Any]:
    errors: List[str] = []
    suggestions: List[str] = []

    # fetch spec
    try:
        resp = requests.get(url, timeout=30, allow_redirects=True)
        resp.raise_for_status()
        spec, parse_suggestions = _load_openapi_from_bytes(resp.content)
        suggestions.extend(parse_suggestions)
    except requests.RequestException as e:
        return {"status": "error", "errors": [f"Failed to fetch URL: {e}"], "is_valid": False}

    if not spec:
        return {"status": "error", "errors": suggestions, "is_valid": False}

    # validate with spec validator
    suggestions.extend(_validate_with_openapi_spec_validator(spec))

    # --- Your original detailed rules ---
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

    # servers
    servers = spec.get("servers", [])
    if not servers:
        suggestions.append("No servers defined. Consider specifying servers for clarity.")
    else:
        for server in servers:
            if isinstance(server, dict):
                url_val = server.get("url")
                if url_val and "{" in url_val:
                    suggestions.append(f"Server URL '{url_val}' uses variables. Document them properly.")

    # global security
    security = spec.get("security", [])
    if not security:
        suggestions.append("No global security requirements defined. Consider adding authentication info.")

    # operations
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

            # operationId
            opid = details.get("operationId")
            if not opid:
                suggestions.append(f"Operation {method.upper()} {path} missing operationId.")
            else:
                if opid in seen_operation_ids:
                    suggestions.append(f"Duplicate operationId '{opid}' found.")
                seen_operation_ids.add(opid)

            # parameters
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

            # requestBody
            if "requestBody" in details:
                rb = details.get("requestBody", {})
                if isinstance(rb, dict):
                    content = rb.get("content", {})
                    if not content:
                        suggestions.append(f"{method.upper()} {path} requestBody has no content defined.")

            # responses
            responses = details.get("responses", {})
            if not responses:
                suggestions.append(f"Operation {method.upper()} {path} has no responses defined.")
            else:
                if "200" not in responses and "201" not in responses:
                    suggestions.append(
                        f"Operation {method.upper()} {path} missing 200/201 success response."
                    )
                for code, resp_detail in responses.items():
                    if not isinstance(resp_detail, dict):
                        continue
                    if "description" not in resp_detail:
                        suggestions.append(
                            f"Response {code} of {method.upper()} {path} missing description."
                        )
                    content = resp_detail.get("content", {})
                    if isinstance(content, dict):
                        for ctype, cval in content.items():
                            schema = cval.get("schema")
                            if not schema:
                                suggestions.append(
                                    f"Response {code} of {method.upper()} {path} with content {ctype} missing schema."
                                )

            # security per-operation
            if "security" not in details:
                suggestions.append(f"Operation {method.upper()} {path} missing security definition.")

    # schemas
    for sname, sdef in schemas.items():
        if not isinstance(sdef, dict):
            continue
        if "type" not in sdef and "allOf" not in sdef and "oneOf" not in sdef and "anyOf" not in sdef:
            suggestions.append(f"Schema {sname} missing type or composition keyword.")
        if "description" not in sdef:
            suggestions.append(f"Schema {sname} missing description.")

    # --- Final summary ---
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

if __name__ == "__main__":
    # Check for GitHub Actions environment variable first
    # GitHub Actions converts hyphens to underscores in env var names
    url = os.getenv("INPUT_SPEC_URL")
    
    # Fall back to command line argument if not in GitHub Actions
    if not url and len(sys.argv) >= 2:
        url = sys.argv[1]
    
    if not url:
        print("Usage: python analyzer.py <openapi-url>")
        print("Or set INPUT_SPEC_URL environment variable for GitHub Actions")
        print(f"Debug: Available env vars with INPUT_: {[k for k in os.environ.keys() if k.startswith('INPUT_')]}")
        sys.exit(1)

    result = analyze_openapi_url(url)
    print(json.dumps(result, indent=2))
