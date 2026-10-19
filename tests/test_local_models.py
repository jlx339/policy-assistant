"""Opt-in real-model regression: requires cached weights, never calls a paid API.

Run with RUN_MODEL_TESTS=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1.
"""
import os

import numpy as np
import pytest


@pytest.mark.skipif(os.getenv('RUN_MODEL_TESTS') != '1', reason='Opt-in cached model integration')
def test_cached_reranker_returns_finite_scores_and_prefers_supporting_evidence():
    from policy_assistant.retrieval import reranker_model
    model = reranker_model()
    query = 'What device evidence must I provide to IT Ops before finishing onboarding?'
    scores = np.asarray(model.predict([
        (query, 'Before completing onboarding, provide evidence of device encryption and the device serial number to IT Ops.'),
        (query, 'The cafeteria serves bananas and oranges for lunch.'),
    ]))
    assert np.isfinite(scores).all(), f'Reranker produced non-finite scores: {scores}'
    assert scores[0] > scores[1]
