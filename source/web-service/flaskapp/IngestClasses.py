import json
from collections import namedtuple


class IngestRecord:
    """
    This class encapsulates a single JSON record and methods to operate on the record
    """

    # Vallidation status named tuple. Note the same status code (e.g. '422')
    # can be used for different errors
    status_nt = namedtuple("name", "code title detail")
    status_ok = status_nt(200, "Ok", "")
    status_wrong_syntax = status_nt(422, "Invalid JSON", "Could not parse JSON record")
    status_id_missing = status_nt(422, "ID Missing", "ID for the JSON record not found")

    # Initialize 'self._record' with JSON string
    def __init__(self, rec):
        self._id = ""
        self._record = rec

    def validate(self):
        """
        Check JSON syntax and do some other validations.
        Set 'self._id' if syntax is correct. Done here so we do not load JSON twice.
        Returns named tuple of type 'status_nt'      
        """

        # JSON loads fine, extract 'self._id' and do other validations
        try:
            data = json.loads(self._record)

            if "id" in data.keys():
                # id found. Set the '_id' variable
                self._id = data["id"]
                return self.status_ok
            else:
                # id not found. Return corresponding error
                return status_id_missing

        # JSON does not load. Return 'wrong syntax'
        except:
            return self.status_wrong_syntax
