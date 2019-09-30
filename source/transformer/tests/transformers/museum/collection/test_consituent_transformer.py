import pytest

from app.transformers import *


def test_constituent_transformer_dummy_pass():
    at = ConstituentTransformer()
    print(type(at))

    assert True
