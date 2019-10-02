import pytest

from app.transformers import *


def test_artifact_transformer_dummy_pass():
    at = ArtifactTransformer()
    print(type(at))

    assert True
