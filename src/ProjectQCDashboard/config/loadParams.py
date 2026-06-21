import yaml
from pathlib import Path
from ProjectQCDashboard.config.schemas import Params

PACKAGE_LOCATION = Path(__file__).resolve().parents[3]

def load_params() -> Params:
    """
    Load parameters from the params.yaml file in the project root.

    This function attempts to read and parse the params.yaml file, returning its contents as a dictionary.
    If the file does not exist, an empty dictionary is returned.

    :return: Parameters as a dictionary, or an empty dict if not found
    :rtype: dict[str, Any] | Any
    """
    params_file = PACKAGE_LOCATION / "params.yaml"
    if not params_file.exists():
        raise FileNotFoundError(f"params.yaml not found at {params_file}")
    
    with open(params_file, 'r', encoding='utf-8') as f:
        raw = yaml.safe_load(f)
    
    return Params(**raw)


PARAMS = load_params()

