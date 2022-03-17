import json
import re
import uuid

from flask import current_app


# Example HMO record
hmo1 = {
    "@context": "https://linked.art/ns/v1/linked-art.json",
    "_label": "Negative FL3000212 from Ruscha Archive",
    "classified_as": [
        {
            "_label": "negatives (photographs)",
            "id": "http://vocab.getty.edu/aat/300127173",
            "type": "Type",
        }
    ],
    "depicts": [{"id": "place/8d48f901-21ff-4526-b803-d10d59f7f823", "type": "Place",}],
    "dimension": [
        {
            "_label": "Archival Object Sequence",
            "classified_as": [
                {
                    "_label": "sequences",
                    "id": "http://vocab.getty.edu/aat/300192339",
                    "type": "Type",
                },
                {
                    "_label": "positional attributes",
                    "id": "http://vocab.getty.edu/aat/300010269",
                    "type": "Type",
                },
                {
                    "_label": "object order",
                    "id": "https://data.getty.edu/local/thesaurus/object-order",
                    "type": "Type",
                },
            ],
            "id": "object/24f72b76-b751-42ed-b747-f368ab19b259/tile/0bd44be4-4c8e-4e05-8dfa-6e41b0dff35b/node/52d7a218-a6c4-11ea-bfdd-0a6344088a1e",
            "type": "Dimension",
            "unit": {
                "_label": "numbers",
                "id": "http://vocab.getty.edu/aat/300055665",
                "type": "MeasurementUnit",
            },
            "value": 1422,
        }
    ],
    "id": "object/24f72b76-b751-42ed-b747-f368ab19b259",
    "identified_by": [
        {
            "_label": "Generated Name",
            "content": "Sunset Boulevard, 1990 : Roll 7 : Gretna Green headed west : Image 0073",
            "id": "object/24f72b76-b751-42ed-b747-f368ab19b259/tile/8d47df5f-92b2-4224-b6a6-c9b580b0f67b/node/aca73ea8-a6c3-11ea-bfdd-0a6344088a1e",
            "type": "Name",
        },
        {
            "_label": "Rosetta file name",
            "classified_as": [
                {
                    "_label": "Rosetta file name",
                    "id": "https://data.getty.edu/local/thesaurus/rosetta-file-name",
                    "type": "Type",
                }
            ],
            "content": "gri_2012_m_1_b005_fn005_d01_r007_0073",
            "id": "object/24f72b76-b751-42ed-b747-f368ab19b259/tile/8384b41e-8819-49d1-b89a-c6d66ce84b21/node/8a6d8034-6ee4-11ea-a3ce-062e15e714ce",
            "type": "Identifier",
        },
        {
            "id": "object/24f72b76-b751-42ed-b747-f368ab19b259/slug",
            "type": "Identifier",
            "content": "1017VZ",
            "classified_as": [
                {
                    "id": "https://data.getty.edu/local/thesaurus/temporary-slug",
                    "type": "Type",
                    "_label": "generated URL slug",
                }
            ],
        },
    ],
    "produced_by": {
        "_label": "Photographing of negative FL3000212",
        "carried_out_by": [
            {
                "id": "https://data.getty.edu/research/collections/person/bad2519d-f8db-5fdd-806d-aae9fb96986e",
                "type": "Person",
            }
        ],
        "id": "object/24f72b76-b751-42ed-b747-f368ab19b259/tile/bb1db191-ebd7-4368-bdf2-3910e159e2be/node/b3456608-5502-11ea-8df1-02aad6a0ba6e",
        "referred_to_by": [
            {
                "_label": "View Cone Documentation",
                "classified_as": [
                    {
                        "_label": "view cone",
                        "id": "https://data.getty.edu/local/thesaurus/view-cone",
                        "type": "Type",
                    }
                ],
                "dimension": [
                    {
                        "classified_as": [
                            {
                                "_label": "camera bearing",
                                "id": "https://data.getty.edu/local/thesaurus/camera-bearing",
                                "type": "Type",
                            }
                        ],
                        "id": "object/24f72b76-b751-42ed-b747-f368ab19b259/tile/b02aea8d-ecac-4c10-8023-05262e626d49/node/ad36af84-a04c-11ea-bfdd-0a6344088a1e",
                        "type": "Dimension",
                        "unit": {
                            "_label": "degrees",
                            "id": "https://data.getty.edu/local/thesaurus/degrees",
                            "type": "MeasurementUnit",
                        },
                        "value": 253.64146828730074,
                    }
                ],
                "id": "object/24f72b76-b751-42ed-b747-f368ab19b259/tile/9f4f4160-8ee1-4921-8fcc-2c0baf6e24ed/node/45672286-5505-11ea-8df1-02aad6a0ba6e",
                "type": "InformationObject",
            }
        ],
        "timespan": {
            "begin_of_the_begin": "1990-01-01T00:00:00Z",
            "end_of_the_end": "1990-12-31T23:59:59Z",
            "id": "object/24f72b76-b751-42ed-b747-f368ab19b259/tile/61e2b735-dc3c-4656-a2ff-997dd947579e/node/6787a1b2-7ec0-11ea-bdf0-0aa7aa4b09bc",
            "identified_by": [
                {
                    "content": "1990",
                    "id": "object/24f72b76-b751-42ed-b747-f368ab19b259/tile/61e2b735-dc3c-4656-a2ff-997dd947579e/node/0243138c-a04d-11ea-bfdd-0a6344088a1e",
                    "type": "Name",
                }
            ],
            "type": "TimeSpan",
        },
        "took_place_at": [
            {
                "_label": "Camera location where photo was taken",
                "classified_as": [
                    {
                        "_label": "classified location ",
                        "id": "https://data.getty.edu/local/thesaurus/classified-location",
                        "type": "Type",
                    }
                ],
                "defined_by": "POINT(-118.487339355214 34.056686685495)",
                "id": "object/24f72b76-b751-42ed-b747-f368ab19b259/tile/11fa8583-2463-46af-9b33-1f95a5058a5b/node/07ec6456-7e78-11ea-8d3f-0aa7aa4b09bc",
                "part_of": {
                    "id": "place/c0380b6c-931f-11ea-9d86-068d38c13b76",
                    "type": "Place",
                },
                "type": "Place",
            }
        ],
        "type": "Production",
    },
    "referred_to_by": [
        {
            "_label": "black",
            "classified_as": [
                "https://data.getty.edu/local/thesaurus/google-vision-tag"
            ],
            "content": "black",
            "dimension": [
                {
                    "classified_as": [
                        "https://data.getty.edu/local/thesaurus/confidence-score"
                    ],
                    "id": "object/24f72b76-b751-42ed-b747-f368ab19b259/tile/3e7cd508-ce36-429c-9a29-037374141dd4/node/abf6e06e-550e-11ea-a96c-02ba3a331460",
                    "type": "Dimension",
                    "unit": "http://vocab.getty.edu/aat/300417377",
                    "value": 0.9605928063392639,
                }
            ],
            "id": "object/24f72b76-b751-42ed-b747-f368ab19b259/tile/3e7cd508-ce36-429c-9a29-037374141dd4/node/86322ece-550e-11ea-a96c-02ba3a331460",
            "type": "LinguisticObject",
        },
        {
            "_label": "white",
            "classified_as": [
                "https://data.getty.edu/local/thesaurus/google-vision-tag"
            ],
            "content": "white",
            "dimension": [
                {
                    "classified_as": [
                        "https://data.getty.edu/local/thesaurus/confidence-score"
                    ],
                    "id": "object/24f72b76-b751-42ed-b747-f368ab19b259/tile/d28ec880-6bb5-4111-99d0-91e57529461c/node/abf6e06e-550e-11ea-a96c-02ba3a331460",
                    "type": "Dimension",
                    "unit": "http://vocab.getty.edu/aat/300417377",
                    "value": 0.9609088897705078,
                }
            ],
            "id": "object/24f72b76-b751-42ed-b747-f368ab19b259/tile/d28ec880-6bb5-4111-99d0-91e57529461c/node/86322ece-550e-11ea-a96c-02ba3a331460",
            "type": "LinguisticObject",
        },
        {
            "_label": "nature",
            "classified_as": [
                "https://data.getty.edu/local/thesaurus/google-vision-tag"
            ],
            "content": "nature",
            "dimension": [
                {
                    "classified_as": [
                        "https://data.getty.edu/local/thesaurus/confidence-score"
                    ],
                    "id": "object/24f72b76-b751-42ed-b747-f368ab19b259/tile/ac1a9f6d-af87-4e94-8209-05700b7dc615/node/abf6e06e-550e-11ea-a96c-02ba3a331460",
                    "type": "Dimension",
                    "unit": "http://vocab.getty.edu/aat/300417377",
                    "value": 0.9418175220489502,
                }
            ],
            "id": "object/24f72b76-b751-42ed-b747-f368ab19b259/tile/ac1a9f6d-af87-4e94-8209-05700b7dc615/node/86322ece-550e-11ea-a96c-02ba3a331460",
            "type": "LinguisticObject",
        },
        {
            "_label": "monochrome photography",
            "classified_as": [
                "https://data.getty.edu/local/thesaurus/google-vision-tag"
            ],
            "content": "monochrome photography",
            "dimension": [
                {
                    "classified_as": [
                        "https://data.getty.edu/local/thesaurus/confidence-score"
                    ],
                    "id": "object/24f72b76-b751-42ed-b747-f368ab19b259/tile/9019c249-8a93-4d5b-a3ea-e7f2e618ebc3/node/abf6e06e-550e-11ea-a96c-02ba3a331460",
                    "type": "Dimension",
                    "unit": "http://vocab.getty.edu/aat/300417377",
                    "value": 0.9039850831031799,
                }
            ],
            "id": "object/24f72b76-b751-42ed-b747-f368ab19b259/tile/9019c249-8a93-4d5b-a3ea-e7f2e618ebc3/node/86322ece-550e-11ea-a96c-02ba3a331460",
            "type": "LinguisticObject",
        },
        {
            "_label": "Google Street View Link",
            "classified_as": [
                {
                    "_label": "Google Street View url",
                    "id": "https://data.getty.edu/local/thesaurus/streetview-url",
                    "type": "Type",
                }
            ],
            "format": "text/html",
            "id": "https://maps.google.com/maps/@?api=1&map_action=pano&viewpoint=34.056686685495,-118.487339355214&heading=343.64146828730077",
            "type": "InformationObject",
        },
        {
            "_label": "tree",
            "classified_as": [
                "https://data.getty.edu/local/thesaurus/google-vision-tag"
            ],
            "content": "tree",
            "dimension": [
                {
                    "classified_as": [
                        "https://data.getty.edu/local/thesaurus/confidence-score"
                    ],
                    "id": "object/24f72b76-b751-42ed-b747-f368ab19b259/tile/c1bcb847-24b2-458c-93b8-a84e5b0c8754/node/abf6e06e-550e-11ea-a96c-02ba3a331460",
                    "type": "Dimension",
                    "unit": "http://vocab.getty.edu/aat/300417377",
                    "value": 0.9698171019554138,
                }
            ],
            "id": "object/24f72b76-b751-42ed-b747-f368ab19b259/tile/c1bcb847-24b2-458c-93b8-a84e5b0c8754/node/86322ece-550e-11ea-a96c-02ba3a331460",
            "type": "LinguisticObject",
        },
        {
            "_label": "photograph",
            "classified_as": [
                "https://data.getty.edu/local/thesaurus/google-vision-tag"
            ],
            "content": "photograph",
            "dimension": [
                {
                    "classified_as": [
                        "https://data.getty.edu/local/thesaurus/confidence-score"
                    ],
                    "id": "object/24f72b76-b751-42ed-b747-f368ab19b259/tile/169ff0f6-6c04-4f15-9da2-e6e8b5b2997a/node/abf6e06e-550e-11ea-a96c-02ba3a331460",
                    "type": "Dimension",
                    "unit": "http://vocab.getty.edu/aat/300417377",
                    "value": 0.9505931735038757,
                }
            ],
            "id": "object/24f72b76-b751-42ed-b747-f368ab19b259/tile/169ff0f6-6c04-4f15-9da2-e6e8b5b2997a/node/86322ece-550e-11ea-a96c-02ba3a331460",
            "type": "LinguisticObject",
        },
        {
            "_label": "woody plant",
            "classified_as": [
                "https://data.getty.edu/local/thesaurus/google-vision-tag"
            ],
            "content": "woody plant",
            "dimension": [
                {
                    "classified_as": [
                        "https://data.getty.edu/local/thesaurus/confidence-score"
                    ],
                    "id": "object/24f72b76-b751-42ed-b747-f368ab19b259/tile/00dad706-3ad2-49e8-b580-18de27f76c7b/node/abf6e06e-550e-11ea-a96c-02ba3a331460",
                    "type": "Dimension",
                    "unit": "http://vocab.getty.edu/aat/300417377",
                    "value": 0.9401175379753113,
                }
            ],
            "id": "object/24f72b76-b751-42ed-b747-f368ab19b259/tile/00dad706-3ad2-49e8-b580-18de27f76c7b/node/86322ece-550e-11ea-a96c-02ba3a331460",
            "type": "LinguisticObject",
        },
        {
            "_label": "wall",
            "classified_as": [
                "https://data.getty.edu/local/thesaurus/google-vision-tag"
            ],
            "content": "wall",
            "dimension": [
                {
                    "classified_as": [
                        "https://data.getty.edu/local/thesaurus/confidence-score"
                    ],
                    "id": "object/24f72b76-b751-42ed-b747-f368ab19b259/tile/3dcc8b86-34f0-46bb-a947-fd1c69dd6391/node/abf6e06e-550e-11ea-a96c-02ba3a331460",
                    "type": "Dimension",
                    "unit": "http://vocab.getty.edu/aat/300417377",
                    "value": 0.8352271318435669,
                }
            ],
            "id": "object/24f72b76-b751-42ed-b747-f368ab19b259/tile/3dcc8b86-34f0-46bb-a947-fd1c69dd6391/node/86322ece-550e-11ea-a96c-02ba3a331460",
            "type": "LinguisticObject",
        },
        {
            "_label": "black and white",
            "classified_as": [
                "https://data.getty.edu/local/thesaurus/google-vision-tag"
            ],
            "content": "black and white",
            "dimension": [
                {
                    "classified_as": [
                        "https://data.getty.edu/local/thesaurus/confidence-score"
                    ],
                    "id": "object/24f72b76-b751-42ed-b747-f368ab19b259/tile/7ef74c23-deac-44f1-bb61-8b0af8dd0e1b/node/abf6e06e-550e-11ea-a96c-02ba3a331460",
                    "type": "Dimension",
                    "unit": "http://vocab.getty.edu/aat/300417377",
                    "value": 0.9490996599197388,
                }
            ],
            "id": "object/24f72b76-b751-42ed-b747-f368ab19b259/tile/7ef74c23-deac-44f1-bb61-8b0af8dd0e1b/node/86322ece-550e-11ea-a96c-02ba3a331460",
            "type": "LinguisticObject",
        },
        {
            "_label": "photography",
            "classified_as": [
                {
                    "_label": "Google Vision tag",
                    "id": "https://data.getty.edu/local/thesaurus/google-vision-tag",
                    "type": "Type",
                }
            ],
            "content": "photography",
            "dimension": [
                {
                    "classified_as": [
                        {
                            "_label": "confidence score",
                            "id": "https://data.getty.edu/local/thesaurus/confidence-score",
                            "type": "Type",
                        }
                    ],
                    "id": "object/24f72b76-b751-42ed-b747-f368ab19b259/tile/7711c6bf-a9ba-4cee-9c72-45d144692e18/node/abf6e06e-550e-11ea-a96c-02ba3a331460",
                    "type": "Dimension",
                    "unit": {
                        "_label": "percentage",
                        "id": "http://vocab.getty.edu/aat/300417377",
                        "type": "MeasurementUnit",
                    },
                    "value": 0.8439844846725464,
                }
            ],
            "id": "object/24f72b76-b751-42ed-b747-f368ab19b259/tile/7711c6bf-a9ba-4cee-9c72-45d144692e18/node/86322ece-550e-11ea-a96c-02ba3a331460",
            "type": "LinguisticObject",
        },
    ],
    "subject_of": [
        {
            "_label": "Computer Vision and Brainfood document",
            "classified_as": [
                {
                    "_label": "Brainfood geojson",
                    "id": "https://data.getty.edu/local/thesaurus/brainfood_geojson",
                    "type": "Type",
                }
            ],
            "content": "{'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [-118.487339355214, 34.056686685495]}, 'properties': {'filename': 'http://media.getty.edu/iiif/research/archives/2012m1_ref71_2b5_FL3000212', 'bearing': 253.64146828730074, 'streetview': 'https://maps.google.com/maps/@?api=1&map_action=pano&viewpoint=34.056686685495,-118.487339355214&heading=343.64146828730077', 'ocr': [], 'tags': [{'score': 0.9698171019554138, 'description': 'tree'}, {'score': 0.9609088897705078, 'description': 'white'}, {'score': 0.9605928063392639, 'description': 'black'}, {'score': 0.9505931735038757, 'description': 'photograph'}, {'score': 0.9490996599197388, 'description': 'black and white'}, {'score': 0.9418175220489502, 'description': 'nature'}, {'score': 0.9401175379753113, 'description': 'woody plant'}, {'score': 0.9039850831031799, 'description': 'monochrome photography'}, {'score': 0.8439844846725464, 'description': 'photography'}, {'score': 0.8352271318435669, 'description': 'wall'}], 'colormetadata': {'hsv': [0, 0, 93.9726941581618], 'grey': [239.63037010331257, 239.63037010331257, 239.63037010331257]}, 'taxlots': [{'ain': '4405020012', 'yearbuilt': 1947, 'address': '12745 N BRISTOL CIR LOS ANGELES CA 90049'}], '_googleVision': {'crop': {'cropHints': [{'confidence': 0.7999999523162842, 'boundingPoly': {'vertices': [{'x': 0, 'y': 0}, {'x': 1599, 'y': 0}, {'x': 1599, 'y': 1080}, {'x': 0, 'y': 1080}], 'normalizedVertices': []}, 'importanceFraction': 1}]}, 'text': [], 'image': {'dominantColors': {'colors': [{'color': {'red': 27, 'blue': 27, 'alpha': None, 'green': 27}, 'score': 0.6325817704200745, 'pixelFraction': 0.42792078852653503}, {'color': {'red': 46, 'blue': 46, 'alpha': None, 'green': 46}, 'score': 0.2820541560649872, 'pixelFraction': 0.23623763024806976}, {'color': {'red': 80, 'blue': 80, 'alpha': None, 'green': 80}, 'score': 0.0382024310529232, 'pixelFraction': 0.08686468750238419}, {'color': {'red': 116, 'blue': 116, 'alpha': None, 'green': 116}, 'score': 0.017605498433113098, 'pixelFraction': 0.04633663222193718}, {'color': {'red': 160, 'blue': 160, 'alpha': None, 'green': 160}, 'score': 0.014466183260083199, 'pixelFraction': 0.04481848329305649}, {'color': {'red': 189, 'blue': 189, 'alpha': None, 'green': 189}, 'score': 0.013925923965871334, 'pixelFraction': 0.09082508087158203}, {'color': {'red': 224, 'blue': 224, 'alpha': None, 'green': 224}, 'score': 0.001164018758572638, 'pixelFraction': 0.06699670106172562}]}}, 'label': [{'mid': '/m/07j7r', 'score': 0.9698171019554138, 'locale': '', 'locations': [], 'confidence': 0, 'properties': [], 'topicality': 0.9698171019554138, 'description': 'tree', 'boundingPoly': None}, {'mid': '/m/083jv', 'score': 0.9609088897705078, 'locale': '', 'locations': [], 'confidence': 0, 'properties': [], 'topicality': 0.9609088897705078, 'description': 'white', 'boundingPoly': None}, {'mid': '/m/019sc', 'score': 0.9605928063392639, 'locale': '', 'locations': [], 'confidence': 0, 'properties': [], 'topicality': 0.9605928063392639, 'description': 'black', 'boundingPoly': None}, {'mid': '/m/068jd', 'score': 0.9505931735038757, 'locale': '', 'locations': [], 'confidence': 0, 'properties': [], 'topicality': 0.9505931735038757, 'description': 'photograph', 'boundingPoly': None}, {'mid': '/m/01g6gs', 'score': 0.9490996599197388, 'locale': '', 'locations': [], 'confidence': 0, 'properties': [], 'topicality': 0.9490996599197388, 'description': 'black and white', 'boundingPoly': None}, {'mid': '/m/05h0n', 'score': 0.9418175220489502, 'locale': '', 'locations': [], 'confidence': 0, 'properties': [], 'topicality': 0.9418175220489502, 'description': 'nature', 'boundingPoly': None}, {'mid': '/m/02hnx9', 'score': 0.9401175379753113, 'locale': '', 'locations': [], 'confidence': 0, 'properties': [], 'topicality': 0.9401175379753113, 'description': 'woody plant', 'boundingPoly': None}, {'mid': '/m/03d49p1', 'score': 0.9039850831031799, 'locale': '', 'locations': [], 'confidence': 0, 'properties': [], 'topicality': 0.9039850831031799, 'description': 'monochrome photography', 'boundingPoly': None}, {'mid': '/m/05wkw', 'score': 0.8439844846725464, 'locale': '', 'locations': [], 'confidence': 0, 'properties': [], 'topicality': 0.8439844846725464, 'description': 'photography', 'boundingPoly': None}, {'mid': '/m/09qqq', 'score': 0.8352271318435669, 'locale': '', 'locations': [], 'confidence': 0, 'properties': [], 'topicality': 0.8352271318435669, 'description': 'wall', 'boundingPoly': None}], 'safeSearch': {'racy': 'VERY_UNLIKELY', 'adult': 'VERY_UNLIKELY', 'spoof': 'UNLIKELY', 'medical': 'VERY_UNLIKELY', 'violence': 'VERY_UNLIKELY'}}}}",
            "format": "application/geo+json",
            "id": "object/24f72b76-b751-42ed-b747-f368ab19b259/tile/4274a758-3d5c-4848-b1ea-fd0b53e25f79/node/ef084d12-550d-11ea-a96c-02ba3a331460",
            "type": "InformationObject",
        },
        {
            "classified_as": [
                {
                    "_label": "IIIF manifest",
                    "id": "https://data.getty.edu/local/thesaurus/iiif-manifest",
                    "type": "Type",
                }
            ],
            "conforms_to": [
                {
                    "_label": "IIIF Presentation API",
                    "id": "http://iiif.io/api/presentation",
                    "type": "InformationObject",
                }
            ],
            "format": 'application/ld+json;profile="http://iiif.io/api/presentation/2/context.json"',
            "id": "https://media.getty.edu/iiif/manifest/f2e45d84-c82f-4bbc-9ad4-c40106d3df22",
            "type": "InformationObject",
        },
    ],
    "type": "HumanMadeObject",
    "part_of": [
        {
            "id": "component/a4af2733-fc43-568a-8ac1-426adab1bb85",
            "type": "InformationObject",
        }
    ],
}

place = {
    "@context": "https://linked.art/ns/v1/linked-art.json",
    "id": "place/c0380b6c-931f-11ea-9d86-068d38c13b76",
    "identified_by": [
        {
            "classified_as": [
                {
                    "_label": "thoroughfare names",
                    "id": "http://vocab.getty.edu/aat/300419273",
                    "type": "Type",
                }
            ],
            "content": "Sunset Boulevard",
            "id": "place/c0380b6c-931f-11ea-9d86-068d38c13b76/tile/80524a55-7a93-4afd-94a1-8e75b4b55d5b/node/53ad433c-8e78-11ea-9d86-068d38c13b76",
            "type": "Name",
        },
        {
            "id": "place/c0380b6c-931f-11ea-9d86-068d38c13b76/slug",
            "type": "Identifier",
            "content": "100B4W",
            "classified_as": [
                {
                    "id": "https://data.getty.edu/local/thesaurus/temporary-slug",
                    "type": "Type",
                    "_label": "generated URL slug",
                }
            ],
        },
    ],
    "part_of": {
        "_label": "Los Angeles (county)",
        "id": "https://dev-tools.aws.getty.edu/arches/ruscha/concepts/282e7bd0-ee7f-47df-b266-01cf521a365d",
        "type": "Place",
    },
    "type": "Place",
}


class TestSubaddressing:
    def test_get_hmo1_subsection(self, client, namespace, auth_token, test_db):
        # identifier of an resource within hmo1 jsonld:
        subaddress_entity_id = "object/24f72b76-b751-42ed-b747-f368ab19b259/tile/4274a758-3d5c-4848-b1ea-fd0b53e25f79/node/ef084d12-550d-11ea-a96c-02ba3a331460"

        response = client.post(
            f"/{namespace}/ingest",
            json=hmo1,
            headers={"Authorization": "Bearer " + auth_token},
        )

        assert response.status_code == 200

        response = client.get(
            f"/{namespace}/{subaddress_entity_id}",
            headers={"Authorization": "Bearer " + auth_token},
        )

        assert response.status_code == 200
        assert response.is_json is True

        doc = response.get_json()

        assert doc["id"].endswith(subaddress_entity_id)
        assert doc["format"] == "application/geo+json"
        assert doc["type"] == "InformationObject"

        subaddress2 = "object/24f72b76-b751-42ed-b747-f368ab19b259/tile/7711c6bf-a9ba-4cee-9c72-45d144692e18/node/abf6e06e-550e-11ea-a96c-02ba3a331460"
        response = client.get(
            f"/{namespace}/{subaddress2}",
            headers={"Authorization": "Bearer " + auth_token},
        )

        assert response.status_code == 200
        assert response.is_json is True

        doc = response.get_json()

        assert doc["id"].endswith(subaddress2)
        assert doc["type"] == "Dimension"
        assert doc["unit"]["id"] == "http://vocab.getty.edu/aat/300417377"

    def test_get_place_subsection(self, client, namespace, auth_token, test_db):
        # identifier of an resource within hmo1 jsonld:
        subaddress_entity_id = "place/c0380b6c-931f-11ea-9d86-068d38c13b76/tile/80524a55-7a93-4afd-94a1-8e75b4b55d5b/node/53ad433c-8e78-11ea-9d86-068d38c13b76"

        response = client.post(
            f"/{namespace}/ingest",
            json=place,
            headers={"Authorization": "Bearer " + auth_token},
        )

        assert response.status_code == 200

        response = client.get(
            f"/{namespace}/{subaddress_entity_id}",
            headers={"Authorization": "Bearer " + auth_token},
        )

        assert response.status_code == 200
        assert response.is_json is True

        doc = response.get_json()

        assert doc["id"].endswith(subaddress_entity_id)
        assert doc["content"] == "Sunset Boulevard"
        assert doc["type"] == "Name"

        sub2 = "place/c0380b6c-931f-11ea-9d86-068d38c13b76/slug"
        response = client.get(
            f"/{namespace}/{sub2}", headers={"Authorization": "Bearer " + auth_token},
        )

        assert response.status_code == 200
        assert response.is_json is True

        doc = response.get_json()

        assert doc["id"].endswith(sub2)
        assert doc["content"] == "100B4W"
        assert doc["type"] == "Identifier"

        sub_non_existent = (
            "place/c0380b6c-931f-11ea-9d86-068d38c13b76/slug/does/not/exist"
        )
        response = client.get(
            f"/{namespace}/{sub_non_existent}",
            headers={"Authorization": "Bearer " + auth_token},
        )

        assert response.status_code == 404
