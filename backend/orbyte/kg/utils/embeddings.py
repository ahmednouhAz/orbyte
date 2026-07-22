from typing import List

import numpy as np

from orbyte.db.engine.sql_engine import get_session_with_current_tenant
from orbyte.db.search_settings import get_current_search_settings
from orbyte.natural_language_processing.search_nlp_models import EmbeddingModel
from orbyte.natural_language_processing.search_nlp_models import EmbedTextType
from shared_configs.configs import MODEL_SERVER_HOST
from shared_configs.configs import MODEL_SERVER_PORT


def encode_string_batch(strings: List[str]) -> np.ndarray:
    with get_session_with_current_tenant() as db_session:
        current_search_settings = get_current_search_settings(db_session)
        model = EmbeddingModel.from_db_model(
            search_settings=current_search_settings,
            server_host=MODEL_SERVER_HOST,
            server_port=MODEL_SERVER_PORT,
        )
        # Get embeddings while session is still open
        embedding = model.encode(strings, text_type=EmbedTextType.QUERY)
    return np.array(embedding)
