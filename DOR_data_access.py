import requests
import json
import config as cfg


class DORDataAccess:
    
    def __init__(self):
        self.base_url = "https://atlas7.getty.edu/api/"
                
        self.access_code = cfg.dor_secret['code']

        self.headers = {
            "Authorization": "ApiKey getty.edu:" + self.access_code,
            "Accept":        "application/json;charset=UTF-8;"
        }


class DORDataAccessArtifact(DORDataAccess):

    def __init__(self):
        super().__init__()
        self.base_url_artifact = self.base_url + "artifact/"

    def get_data(self, id):
        r = requests.get(self.base_url_artifact + str(id), headers=self.headers)
        return (r.status_code, r.text)
    

    

