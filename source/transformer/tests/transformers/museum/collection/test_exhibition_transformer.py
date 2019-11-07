import pytest

from app.transformers import *


def test_exhibition_transformer_dummy_pass():
    at = ExhibitionTransformer()
    print(type(at))

    assert True
