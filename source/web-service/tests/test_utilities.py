import pytest

from flaskapp.utilities import generate_url


class TestGenerateURL:
    def test_without_params(self, current_app, base_url):
        assert generate_url() == f"{base_url}/activity-stream"

    def test_with_base(self, current_app, base_url):
        url = generate_url(base=True)
        assert url == f"{base_url}"

    def test_with_sub(self, current_app, base_url):
        url = generate_url(sub=["a", "b"])
        assert url == f"{base_url}/activity-stream/a/b"

    def test_with_both(self, current_app, base_url):
        url = generate_url(base=True, sub=["a", "b"])
        assert url == f"{base_url}/a/b"
