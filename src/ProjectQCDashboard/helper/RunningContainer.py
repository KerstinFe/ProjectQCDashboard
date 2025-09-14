import os
import sys  

def _is_running_in_container() -> bool:
    """Detect if we're running in a Docker/Podman container
    :return: True if running in a container, False otherwise
    :rtype: bool
    """
    # Primary check: explicit environment variable
    if os.environ.get('RUNNING_IN_CONTAINER', '').lower() == 'true':
        return True
    
    # Fallback checks for other container indicators
    indicators = [
        os.path.exists('/.dockerenv'),  # Docker
        os.path.exists('/run/.containerenv'),  # Podman
        os.environ.get('container') is not None,  # General container env
        os.environ.get('HOSTNAME', '').startswith(('podman-', 'docker-')),  # Container hostname patterns
        'KUBERNETES_SERVICE_HOST' in os.environ,  # Kubernetes
    ]
    
    # Additional check for cgroup (safely)
    try:
        if os.path.exists('/proc/1/cgroup'):
            with open('/proc/1/cgroup', 'r') as f:
                cgroup_content = f.read()
                if any(indicator in cgroup_content for indicator in ['docker', 'containerd', 'podman']):
                    indicators.append(True)
    except (IOError, OSError):
        pass  # Ignore if we can't read the file
    
    # If any indicator is True, we're likely in a container
    return any(indicators)