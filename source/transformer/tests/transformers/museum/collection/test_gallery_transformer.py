import pytest

from app.transformers import *


def test_gallery_transformer_dummy_pass():
    at = GalleryTransformer()
    print(type(at))

    assert True
