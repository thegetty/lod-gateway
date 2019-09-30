import pytest

from app.transformers import *


class SampleTransformer(BaseTransformer):

    def activityStreamEndpoint(self):
        """Provide a method for conveying the Activity Stream endpoint that this transformer will process"""
        pass

    def activityStreamEndpointOptions(self):
        """Provide a method for conveying the Activity Stream endpoint options to configure each HTTP request"""
        pass

    def activityStreamObjectTypes(self):
        """Provide a method for conveying the supported Activity Stream Object type names that this transformer will handle"""
        pass

    def entityType(self):
        """Provide a method for determining the correct target entity type"""
        pass

    def assembleHeaders(self):
        """Assemble our HTTP Request Headers for the DOR API call"""
        pass

    def generateURI(self):
        """Generate the URI for a DOR API resource"""
        pass

    def generateURL(self):
        """Generate the absolute URL for a DOR API resource"""
        pass

    def getUUID(self):
        """Provide a method for accessing the record's UUID"""

        debug("%s.getUUID() called..." % (self.__class__.__name__), level=1)

        pass


def test_base_transformer_dummy_pass():
    transformer = SampleTransformer()
    print(type(transformer))

    assert True
