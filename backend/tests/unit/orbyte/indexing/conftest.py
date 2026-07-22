import pytest

from orbyte.indexing.embedder import DefaultIndexingEmbedder
from orbyte.indexing.indexing_heartbeat import IndexingHeartbeatInterface


class MockHeartbeat(IndexingHeartbeatInterface):
    def __init__(self) -> None:
        self.call_count = 0

    def should_stop(self) -> bool:
        return False

    def progress(self, tag: str, amount: int) -> None:  # noqa: ARG002
        self.call_count += 1


@pytest.fixture
def mock_heartbeat() -> MockHeartbeat:
    return MockHeartbeat()


@pytest.fixture
def embedder() -> DefaultIndexingEmbedder:
    return DefaultIndexingEmbedder(
        model_name="intfloat/e5-base-v2",
        normalize=True,
        query_prefix=None,
        passage_prefix=None,
    )
