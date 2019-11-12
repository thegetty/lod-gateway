import pytest

from app.transformers import *


class SampleTransformer(BaseTransformer):
    pass


def test_base_transformer_dummy_pass():
    transformer = SampleTransformer()

    print(type(transformer))

    assert True
