"""
Validation script for generated HEDIS measure calculation code.

Reads a JSON payload from stdin with the following fields:
  - "code": The generated Python code as a string.
  - "measure_abbreviation": The HEDIS measure abbreviation (e.g., "CBP").

Performs structural and semantic validation to ensure the generated code:
  1. Is valid Python that can be parsed.
  2. Contains required functions (eligible population, exclusions, numerator, main entry).
  3. Produces a valid FHIR MeasureReport structure.
  4. Handles the basic test case (empty bundle returns not-in-population).

Outputs JSON with:
  - "valid": true/false
  - "errors": list of error messages (if any)
  - "warnings": list of warning messages (if any)
"""

import ast
import json
import sys
import tempfile
import importlib.util
import os
from typing import Any


def validate_syntax(code: str) -> list[str]:
    """Check that the code is valid Python."""
    errors = []
    try:
        ast.parse(code)
    except SyntaxError as e:
        errors.append(f"Syntax error at line {e.lineno}: {e.msg}")
    return errors


def validate_structure(code: str) -> tuple[list[str], list[str]]:
    """Check that the code contains required functions and patterns."""
    errors = []
    warnings = []

    tree = ast.parse(code)
    function_names = [
        node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
    ]

    # Must have a main calculation function
    has_main_calc = any(
        "calculate" in name or "measure" in name.lower() for name in function_names
    )
    if not has_main_calc:
        errors.append(
            "Missing main calculation function. Expected a function with 'calculate' "
            "or 'measure' in its name that accepts a FHIR Bundle and returns a MeasureReport."
        )

    # Should have eligible population check
    has_eligible = any(
        "eligible" in name.lower() or "population" in name.lower()
        for name in function_names
    )
    if not has_eligible:
        warnings.append(
            "No function found for eligible population check. "
            "Consider adding a dedicated function like 'check_eligible_population()'."
        )

    # Should have exclusions check
    has_exclusions = any(
        "exclusion" in name.lower() or "exclude" in name.lower()
        for name in function_names
    )
    if not has_exclusions:
        warnings.append(
            "No function found for exclusion checks. "
            "Consider adding a dedicated function like 'check_exclusions()'."
        )

    # Should have numerator check
    has_numerator = any(
        "numerator" in name.lower() or "complian" in name.lower()
        for name in function_names
    )
    if not has_numerator:
        warnings.append(
            "No function found for numerator check. "
            "Consider adding a dedicated function like 'check_numerator()'."
        )

    # Check for MeasureReport construction
    if "MeasureReport" not in code:
        errors.append(
            "Code does not contain 'MeasureReport'. "
            "The output must be a FHIR MeasureReport resource."
        )

    # Check for required population codes
    required_populations = [
        "initial-population",
        "denominator",
        "denominator-exclusion",
        "numerator",
    ]
    for pop in required_populations:
        if pop not in code:
            errors.append(
                f"Missing population code '{pop}' in MeasureReport construction."
            )

    # Check for measure-population code system
    if "http://terminology.hl7.org/CodeSystem/measure-population" not in code:
        warnings.append(
            "Missing standard measure-population code system URI. "
            "Use 'http://terminology.hl7.org/CodeSystem/measure-population'."
        )

    return errors, warnings


def validate_execution(
    code: str, measure_abbreviation: str
) -> tuple[list[str], list[str]]:
    """Try to execute the code with an empty bundle and validate the output."""
    errors = []
    warnings = []

    # Write code to a temp file and import it
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        temp_path = f.name

    try:
        spec = importlib.util.spec_from_file_location("measure_module", temp_path)
        if spec is None or spec.loader is None:
            errors.append("Could not load the generated code as a Python module.")
            return errors, warnings

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Find the main calculation function
        calc_func = None
        for name in dir(module):
            obj = getattr(module, name)
            if callable(obj) and (
                "calculate" in name.lower() or "measure" in name.lower()
            ):
                # Prefer functions that take a bundle parameter
                import inspect

                sig = inspect.signature(obj)
                params = list(sig.parameters.keys())
                if len(params) >= 1 and "bundle" in params[0].lower():
                    calc_func = obj
                    break
                elif len(params) >= 1:
                    calc_func = calc_func or obj

        if not calc_func:
            errors.append("Could not find a callable main calculation function.")
            return errors, warnings

        # Test with empty bundle
        empty_bundle: dict[str, Any] = {
            "resourceType": "Bundle",
            "type": "collection",
            "entry": [
                {
                    "resource": {
                        "resourceType": "Patient",
                        "id": "test-patient",
                        "birthDate": "2000-01-01",
                    }
                }
            ],
        }

        try:
            result = calc_func(empty_bundle)
        except Exception as e:
            errors.append(
                f"Execution error with minimal bundle: {type(e).__name__}: {e}"
            )
            return errors, warnings

        # Validate the MeasureReport structure
        if not isinstance(result, dict):
            errors.append(f"Expected dict output, got {type(result).__name__}.")
            return errors, warnings

        if result.get("resourceType") != "MeasureReport":
            errors.append(
                f"Expected resourceType 'MeasureReport', got '{result.get('resourceType')}'."
            )

        if result.get("type") != "individual":
            warnings.append(f"Expected type 'individual', got '{result.get('type')}'.")

        if result.get("status") != "complete":
            warnings.append(
                f"Expected status 'complete', got '{result.get('status')}'."
            )

        groups = result.get("group", [])
        if not groups:
            errors.append("MeasureReport has no 'group' entries.")
        else:
            populations = groups[0].get("population", [])
            pop_codes = [
                p.get("code", {}).get("coding", [{}])[0].get("code")
                for p in populations
                if p.get("code", {}).get("coding")
            ]
            for required in [
                "initial-population",
                "denominator",
                "denominator-exclusion",
                "numerator",
            ]:
                if required not in pop_codes:
                    errors.append(
                        f"Missing population '{required}' in MeasureReport group."
                    )

            # For an empty bundle, initial-population should be 0
            for pop in populations:
                pop_code = pop.get("code", {}).get("coding", [{}])[0].get("code")
                if pop_code == "initial-population" and pop.get("count", 0) != 0:
                    warnings.append(
                        "A minimal patient bundle (no conditions/encounters) should "
                        "result in initial-population count of 0."
                    )

        if "subject" not in result:
            errors.append("MeasureReport is missing 'subject' field.")

        if "period" not in result:
            errors.append("MeasureReport is missing 'period' field.")

    except Exception as e:
        errors.append(f"Unexpected validation error: {type(e).__name__}: {e}")
    finally:
        os.unlink(temp_path)

    return errors, warnings


def main() -> None:
    """Read input from stdin, validate, and output results."""
    try:
        input_data = json.loads(sys.stdin.read())
    except json.JSONDecodeError as e:
        print(
            json.dumps(
                {"valid": False, "errors": [f"Invalid JSON input: {e}"], "warnings": []}
            )
        )
        sys.exit(1)

    code = input_data.get("code", "")
    measure_abbreviation = input_data.get("measure_abbreviation", "UNKNOWN")

    if not code.strip():
        print(
            json.dumps(
                {"valid": False, "errors": ["No code provided."], "warnings": []}
            )
        )
        sys.exit(1)

    all_errors: list[str] = []
    all_warnings: list[str] = []

    # Step 1: Syntax validation
    syntax_errors = validate_syntax(code)
    all_errors.extend(syntax_errors)

    if syntax_errors:
        print(
            json.dumps({"valid": False, "errors": all_errors, "warnings": all_warnings})
        )
        sys.exit(0)

    # Step 2: Structure validation
    struct_errors, struct_warnings = validate_structure(code)
    all_errors.extend(struct_errors)
    all_warnings.extend(struct_warnings)

    if struct_errors:
        print(
            json.dumps({"valid": False, "errors": all_errors, "warnings": all_warnings})
        )
        sys.exit(0)

    # Step 3: Execution validation
    exec_errors, exec_warnings = validate_execution(code, measure_abbreviation)
    all_errors.extend(exec_errors)
    all_warnings.extend(exec_warnings)

    is_valid = len(all_errors) == 0

    print(
        json.dumps(
            {"valid": is_valid, "errors": all_errors, "warnings": all_warnings},
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
