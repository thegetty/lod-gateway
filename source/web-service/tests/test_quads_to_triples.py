from flaskapp.utilities import QUADS, quads_to_triples

quads = [
    r'<urn:object/98927854-d3bb-383b-b031-d968dafcd7b6/tile/1> <http://www.cidoc-crm.org/cidoc-crm/P190_has_symbolic_content> "3T - Box BWI-001A Folder 001 Image 0007"@en _:N5d01a09902744394937f51a38e5b86e3 .',
    r"<urn:object/98927854-d3bb-383b-b031-d968dafcd7b6> <http://www.cidoc-crm.org/cidoc-crm/P46i_forms_part_of> <http://lodweb:5101/research/collections/component/1ccd7a2d-d37d-5347-a682-9c4d2c69fb55> _:N5d01a09902744394937f51a38e5b86e3 .",
    r'<urn:object/98927854-d3bb-383b-b031-d968dafcd7b6> <http://www.cidoc-crm.org/cidoc-crm/P46i_forms_part_of> "Test"^^<foo> _:N5d01a09902744394937f51a38e5b86e3 .',
    r'<http://example.org/show/218> <http://www.w3.org/2000/01/rdf-schema#label> "That Seventies Show"^^<http://www.w3.org/2001/XMLSchema#string> _:N5d01a09902744394937f51a38e5b86e3 .',
    r'<http://example.org/show/218> <http://www.w3.org/2000/01/rdf-schema#label> "That Seventies Show" _:N5d01a09902744394937f51a38e5b86e3 .',
    r'<http://example.org/show/218> <http://example.org/show/localName> "That Seventies Show"@en _:N5d01a09902744394937f51a38e5b86e3 .',
    r'<http://example.org/show/218> <http://example.org/show/localName> "Cette Série des Années Septante"@fr-be _:N5d01a09902744394937f51a38e5b86e3 .',
    r'<http://example.org/#spiderman> <http://example.org/text> "This is a multi-line\nliteral with many quotes (\"\"\"\"\")\nand two apostrophes (\'\')." _:N5d01a09902744394937f51a38e5b86e3 .',
    r'<http://en.wikipedia.org/wiki/Helium> <http://example.org/elements/atomicNumber> "2"^^<http://www.w3.org/2001/XMLSchema#integer> _:N5d01a09902744394937f51a38e5b86e3 .',
    r'<http://en.wikipedia.org/wiki/Helium> <http://example.org/elements/specificGravity> "1.663E-4"^^<http://www.w3.org/2001/XMLSchema#double> _:N5d01a09902744394937f51a38e5b86e3 .',
]

results = [
    [
        "<http://www.cidoc-crm.org/cidoc-crm/P190_has_symbolic_content> ",
        '"3T - Box BWI-001A Folder 001 Image 0007"@en',
        "@en",
        None,
        "_:N5d01a09902744394937f51a38e5b86e3",
    ],
    [
        "<http://www.cidoc-crm.org/cidoc-crm/P46i_forms_part_of> ",
        "<http://lodweb:5101/research/collections/component/1ccd7a2d-d37d-5347-a682-9c4d2c69fb55>",
        None,
        None,
        "_:N5d01a09902744394937f51a38e5b86e3",
    ],
    [
        "<http://www.cidoc-crm.org/cidoc-crm/P46i_forms_part_of> ",
        '"Test"',
        None,
        "^^<foo>",
        "_:N5d01a09902744394937f51a38e5b86e3",
    ],
    [
        "<http://www.w3.org/2000/01/rdf-schema#label> ",
        '"That Seventies Show"',
        None,
        "^^<http://www.w3.org/2001/XMLSchema#string>",
        "_:N5d01a09902744394937f51a38e5b86e3",
    ],
    [
        "<http://www.w3.org/2000/01/rdf-schema#label> ",
        '"That Seventies Show"',
        None,
        None,
        "_:N5d01a09902744394937f51a38e5b86e3",
    ],
    [
        "<http://example.org/show/localName> ",
        '"That Seventies Show"@en',
        "@en",
        None,
        "_:N5d01a09902744394937f51a38e5b86e3",
    ],
    [
        "<http://example.org/show/localName> ",
        '"Cette Série des Années Septante"@fr-be',
        "@fr-be",
        None,
        "_:N5d01a09902744394937f51a38e5b86e3",
    ],
    [
        "<http://example.org/text> ",
        '"This is a multi-line\\nliteral with many quotes (\\"\\"\\"\\"\\")\\nand two apostrophes (\\\'\\\')."',
        None,
        None,
        "_:N5d01a09902744394937f51a38e5b86e3",
    ],
    [
        "<http://example.org/elements/atomicNumber> ",
        '"2"',
        None,
        "^^<http://www.w3.org/2001/XMLSchema#integer>",
        "_:N5d01a09902744394937f51a38e5b86e3",
    ],
    [
        "<http://example.org/elements/specificGravity> ",
        '"1.663E-4"',
        None,
        "^^<http://www.w3.org/2001/XMLSchema#double>",
        "_:N5d01a09902744394937f51a38e5b86e3",
    ],
]


def test_quads_to_triples():
    testset = zip(quads, results)

    for q, r in testset:
        m = QUADS.match(q).groups()
        for x, y in zip(m, r):
            assert x == y
