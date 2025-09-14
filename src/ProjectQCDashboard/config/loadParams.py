import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

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
    """Load parameters from docker-compose.yml
    :return: Parameters as a dictionary
    :rtype: Dict[str, Any]
    """
    docker_compose_file = PACKAGE_LOCATION / "docker-compose.yml"

    if docker_compose_file.exists():
        with open(docker_compose_file, 'r') as f:
            return yaml.safe_load(f)
    return {}

