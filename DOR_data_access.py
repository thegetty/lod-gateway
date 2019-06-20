import requests
import json
import config as cfg
from abc import ABC, abstractmethod

# Abstract class with some common types and methods from which all DOR data access classes will be derived
# Currently only 'base_url' differes among classes. Subclassing (rather than parameterizing) done to facilitate possible futre change
class DORDataAccess(ABC):
    
    def __init__(self):
        self.base_url    = cfg.dor_config["base_url"]       
        self.access_code = cfg.dor_config['code']
        self.user_name   = cfg.dor_config['user_name']
        self.headers = {
            "Authorization": "ApiKey " + self.user_name + ":" + self.access_code,
            "Accept":        "application/json;charset=UTF-8;"
        }

    def get_data(self, id):
        r = requests.get(self.base_url + str(id), headers=self.headers)
        if (r.status_code == 200):
            return json.loads(r.text)
        #else:
        #    raise Exception("Error accessing data. Status code: " + str(r.status_code))

    @abstractmethod
    def get_all_ids(self):
        pass

       
# 'artifact' is temporary end point. Will be 'Object'
class DORDataAccessObject(DORDataAccess):

    def __init__(self):
        super().__init__()
        self.base_url = self.base_url + "artifact/"

    def get_all_ids(self):
        pass
    

class DORDataAccessPerson(DORDataAccess):

    def __init__(self):
        super().__init__()
        self.base_url = self.base_url + "constituent/"

    def get_all_ids(self):
        raise NotImplementedError()


class DORDataAccessGroup(DORDataAccess):

    def __init__(self):
        super().__init__()
        self.base_url = self.base_url + "group/"

    def get_all_ids(self):
        raise NotImplementedError()


class DORDataAccessProvenance(DORDataAccess):

    def __init__(self):
        super().__init__()
        self.base_url = self.base_url + "provenance/"

    def get_all_ids(self):
        raise NotImplementedError()


class DORDataAccessPlace(DORDataAccess):

    def __init__(self):
        super().__init__()
        self.base_url = self.base_url + "place/"

    def get_all_ids(self):
        raise NotImplementedError()


class DORDataAccessCollection(DORDataAccess):

    def __init__(self):
        super().__init__()
        self.base_url = self.base_url + "Collection/"

    def get_all_ids(self):
        raise NotImplementedError()
