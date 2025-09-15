import pytest
from flask import Flask, request
from flaskapp.conneg import determine_requested_format_and_profile

app = Flask(__name__)


@pytest.mark.parametrize(
    "query_string, headers, expected",
    [
        (
            {"_mediatype": "application/n-triples"},
            {},
            {
                "preferred_mimetype": "application/n-triples",
                "accepted_mimetypes": [("application/n-triples", 1.0, "nt11")],
                "requested_profiles": [],
            },
        ),
        (
            {"_mediatype": "application/json"},
            {},
            {
                "preferred_mimetype": "application/json",
                "accepted_mimetypes": [("application/json", 1.0, "jsonld")],
                "requested_profiles": [],
            },
        ),
        (
            {"format": "nt"},
            {},
            {
                "preferred_mimetype": "application/n-triples; charset=UTF-8",
                "accepted_mimetypes": [
                    ("application/n-triples; charset=UTF-8", 1.0, "nt11")
                ],
                "requested_profiles": [],
            },
        ),
        (
            {},
            {"Accept": "text/turtle;q=0.9, application/ld+json;charset=UTF-16;q=1.0"},
            {
                "preferred_mimetype": "application/ld+json; charset=UTF-16",
                "accepted_mimetypes": [
                    ("application/ld+json; charset=UTF-16", 1.0, "json-ld"),
                    ("text/turtle", 0.9, "turtle"),
                ],
                "requested_profiles": [],
            },
        ),
        (
            {"_profile": "<http://example.org/profile>"},
            {},
            {
                "preferred_mimetype": "application/ld+json; charset=UTF-8",
                "accepted_mimetypes": [
                    ("application/ld+json; charset=UTF-8", 1.0, "json-ld")
                ],
                "requested_profiles": [("<http://example.org/profile>", 1)],
            },
        ),
        (
            {},
            {"Accept-Profile": "<http://example.org/p1>, <http://example.org/p2>"},
            {
                "preferred_mimetype": "application/ld+json; charset=UTF-8",
                "accepted_mimetypes": [
                    ("application/ld+json; charset=UTF-8", 1.0, "json-ld")
                ],
                "requested_profiles": [
                    ("<http://example.org/p1>", 1),
                    ("<http://example.org/p2>", 1),
                ],
            },
        ),
        (
            {},
            {
                "Accept-Profile": "<http://example.org/p1>;q=1.0, <http://example.org/p2>;q=0.7"
            },
            {
                "preferred_mimetype": "application/ld+json; charset=UTF-8",
                "accepted_mimetypes": [
                    ("application/ld+json; charset=UTF-8", 1.0, "json-ld")
                ],
                "requested_profiles": [
                    ("<http://example.org/p1>", 1.0),
                    ("<http://example.org/p2>", 0.7),
                ],
            },
        ),
        (
            {},
            {"Accept-Profile": "<http://example.org/only>"},
            {
                "preferred_mimetype": "application/ld+json; charset=UTF-8",
                "accepted_mimetypes": [
                    ("application/ld+json; charset=UTF-8", 1.0, "json-ld")
                ],
                "requested_profiles": [("<http://example.org/only>", 1)],
            },
        ),
    ],
)
def test_determine_requested_format_and_profile(query_string, headers, expected):
    with app.test_request_context(query_string=query_string, headers=headers):
        result = determine_requested_format_and_profile(request)

        assert result["preferred_mimetype"] == expected["preferred_mimetype"]
        for a, b in zip(result["accepted_mimetypes"], expected["accepted_mimetypes"]):
            assert a[0] == b[0] and float(a[1]) == float(b[1]) and a[2] == b[2]
        for a, b in zip(result["requested_profiles"], expected["requested_profiles"]):
            assert a[0] == b[0] and float(a[1]) == float(b[1])
