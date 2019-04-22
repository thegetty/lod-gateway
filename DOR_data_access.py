import requests
import json
import config as cfg


class DORDataAccess:
    
    def __init__(self):
        self.base_url = "https://atlas7.getty.edu/api/artifact/"
        
        # This needs to be changed so we don't publish secret to GitHub
        self.access_code = cfg.dor_secret['code']

        self.headers = {
            "Authorization": "ApiKey getty.edu:" + self.access_code,
            "Accept":        "application/json;charset=UTF-8;"
        }

    def get_data(self, id):            
        r = requests.get(self.base_url + str(id), headers=self.headers)
        return (r.status_code, r.text)