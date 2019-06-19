import requests
import json
import config as cfg

from abc import ABC, abstractmethod

class DORDataAccess(ABC):
    
    def __init__(self):
        self.base_url = cfg.dor_config["base_url"]
        self.access_code = cfg.dor_config['code']

        self.headers = {
            "Authorization": "ApiKey getty.edu:" + self.access_code,
            "Accept":        "application/json;charset=UTF-8;"
        }

        # Abstract methods
        # Get all ids from the endpoint
        @abstractmethod
        def get_all_ids(self):
            pass

        # Get data for spesific id
        @abstractmethod
        def get_data(self, id):
            pass

class DORDataAccessObject(DORDataAccess):

    def __init__(self):
        super().__init__()
        self.base_url_artifact = self.base_url + "artifact/"

    def get_data(self, id):
        r = requests.get(self.base_url_artifact + str(id), headers=self.headers)
        return (r.status_code, r.text)
