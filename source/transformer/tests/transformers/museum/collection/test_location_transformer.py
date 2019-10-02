import pytest

from app.transformers import *


def test_location_transformer_dummy_pass():
    at = LocationTransformer()
    print(type(at))

    assert True
