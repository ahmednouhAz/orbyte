# Named `platform_utils` (not `platform`) because `supervisord_watchdog.py` in this
# same directory is launched as a script (`python orbyte/utils/supervisord_watchdog.py`),
# which puts this directory on `sys.path[0]`. A module named `platform.py` here would
# then shadow the stdlib `platform`, breaking `uuid` (which calls `platform.system()`)
# and any transitive import of it (e.g. `redis`). See issue #10975.
import os
import warnings

_ORBYTE_DOCKER_ENV_STR = "ORBYTE_RUNNING_IN_DOCKER"
_DANSWER_DOCKER_ENV_STR = "DANSWER_RUNNING_IN_DOCKER"


def _resolve_container_flag() -> bool:
    orbyte_val = os.getenv(_ORBYTE_DOCKER_ENV_STR)
    if orbyte_val is not None:
        return orbyte_val.lower() == "true"

    danswer_val = os.getenv(_DANSWER_DOCKER_ENV_STR)
    if danswer_val is not None:
        warnings.warn(
            f"{_DANSWER_DOCKER_ENV_STR} is deprecated and will be ignored in a "
            f"future release. Use {_ORBYTE_DOCKER_ENV_STR} instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return danswer_val.lower() == "true"

    return False


_IS_RUNNING_IN_CONTAINER: bool = _resolve_container_flag()
_IS_RUNNING_IN_KUBERNETES: bool = os.getenv("KUBERNETES_SERVICE_HOST") is not None


def is_running_in_container() -> bool:
    return _IS_RUNNING_IN_CONTAINER


def is_running_in_kubernetes() -> bool:
    return _IS_RUNNING_IN_KUBERNETES
