from LAModelObject import LAModelObject
from LAModelPerson import LAModelPerson
from LAModelComponent import LAComponentType


# Dictionary with type as a key, and instance of the model as value
model_dict = {
    LAComponentType.Object: LAModelObject(),
    LAComponentType.Person: LAModelPerson()
}

# Class that has collection of all or any combination of LAModelComponent
class LAModelProcess:    
    def __init__(self, type_list):
        self.lamodel_list = self.__create_model_list(type_list)

    def process_models(self):
        for m in self.lamodel_list:
            id_list = m.get_id_list()
            for id in id_list:
                j_data = m.get_data(id)
                m.to_jsonld(j_data)

    # Private method to create a list of Model Classes from the list of Model types supplied by the user
    def __create_model_list(self, type_list):
        result_list = []
        for t in type_list:
            result_list.append(model_dict[t])
        return result_list



p = LAModelProcess([LAComponentType.Object, LAComponentType.Person])
p.process_models()

a = 0

