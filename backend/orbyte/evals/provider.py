from orbyte.evals.models import EvalProvider
from orbyte.evals.providers.braintrust import BraintrustEvalProvider
from orbyte.evals.providers.local import LocalEvalProvider


def get_provider(local_only: bool = False) -> EvalProvider:
    """
    Get the appropriate eval provider.

    Args:
        local_only: If True, use LocalEvalProvider (CLI output only, no Braintrust).
                   If False, use BraintrustEvalProvider.

    Returns:
        The appropriate EvalProvider instance.
    """
    if local_only:
        return LocalEvalProvider()
    return BraintrustEvalProvider()
