import yaml
from pathlib import Path
from typing import Any, Dict

PACKAGE_LOCATION = Path(__file__).resolve().parents[3]

def load_params() -> Dict[str, Any]:
    """Load parameters from params.yaml
    :return: Parameters as a dictionary
    :rtype: Dict[str, Any]
    """
    params_file = PACKAGE_LOCATION / "params.yaml"
    
    if params_file.exists():
        with open(params_file, 'r') as f:
            return yaml.safe_load(f)
    return {}


def load_dockercompose() -> Dict[str, Any]:
    """Load docker-compose.yml from the project root and return as dict.

    Returns empty dict if file not found or cannot be parsed.
    """
    compose_file = PACKAGE_LOCATION / "docker-compose.yml"
    if compose_file.exists():
        try:
            with open(compose_file, "r") as fh:
                return yaml.safe_load(fh) or {}
        except Exception:
            # If parsing fails, return empty dict
            return {}
    return {}
