from collections.abc import Generator

from ee.orbyte.external_permissions.perm_sync_types import FetchAllDocumentsFunction
from ee.orbyte.external_permissions.perm_sync_types import FetchAllDocumentsIdsFunction
from ee.orbyte.external_permissions.utils import credential_json
from ee.orbyte.external_permissions.utils import generic_doc_sync
from orbyte.access.models import ElementExternalAccess
from orbyte.configs.constants import DocumentSource
from orbyte.connectors.sharepoint.connector import SharepointConnector
from orbyte.db.models import ConnectorCredentialPair
from orbyte.indexing.indexing_heartbeat import IndexingHeartbeatInterface
from orbyte.utils.logger import setup_logger

logger = setup_logger()

SHAREPOINT_DOC_SYNC_TAG = "sharepoint_doc_sync"


def sharepoint_doc_sync(
    cc_pair: ConnectorCredentialPair,
    fetch_all_existing_docs_fn: FetchAllDocumentsFunction,  # noqa: ARG001
    fetch_all_existing_docs_ids_fn: FetchAllDocumentsIdsFunction,
    callback: IndexingHeartbeatInterface | None = None,
) -> Generator[ElementExternalAccess, None, None]:
    sharepoint_connector = SharepointConnector(
        **cc_pair.connector.connector_specific_config,
    )
    sharepoint_connector.load_credentials(credential_json(cc_pair))

    yield from generic_doc_sync(
        cc_pair=cc_pair,
        fetch_all_existing_docs_ids_fn=fetch_all_existing_docs_ids_fn,
        callback=callback,
        doc_source=DocumentSource.SHAREPOINT,
        slim_connector=sharepoint_connector,
        label=SHAREPOINT_DOC_SYNC_TAG,
    )
