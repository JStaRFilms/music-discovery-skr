import os

import pytest

pytestmark = pytest.mark.integration


@pytest.mark.skipif(
    os.environ.get("MUSIC_DISCOVERY_RUN_INTEGRATION") != "1",
    reason="set MUSIC_DISCOVERY_RUN_INTEGRATION=1 to load the real checkpoint",
)
def test_primary_model_text_vectors_are_distinct():
    from music_discovery import config
    from music_discovery.health import MAX_PAIRWISE_COSINE, check_model

    result = check_model(config.PRIMARY_MODEL_ID, config.PRIMARY_MODEL_REVISION)
    assert result["max_pairwise_cosine"] < MAX_PAIRWISE_COSINE, result
