from cromulent.model import factory, \
	Identifier, Mark, ManMadeObject as Object, Type, \
	Person, Material, MeasurementUnit, Place, Dimension, Currency, \
	ConceptualObject, TimeSpan, Actor, PhysicalThing, Language, \
	LinguisticObject, InformationObject, \
	Activity, Group, Name, MonetaryAmount, PropertyInterest, \
	Destruction, AttributeAssignment, BaseResource, PhysicalObject, \
	Acquisition, ManMadeFeature, VisualItem, Set, \
	PropositionalObject, Payment, Creation, Phase, Birth, Death, TimeSpan

import json
from DOR_data_access import DORDataAccessObject, DORDataAccessPerson
from utilities import PrintToFile

# Function to print out the result JSON so it can be opened in the editor

# Get record 826 as a test of DORDataAcces function
da = DORDataAccessObject()
raw_data = da.get_data(826)
r_code = raw_data[0]
r_data = raw_data[1]
data = json.loads(r_data)
outstr = json.dumps(data, indent=2)
PrintToFile("826_DOR.json", outstr)

r = da.get_all_ids()

# Get Person
da = DORDataAccessPerson()
raw_data = da.get_data(377)
r_code = raw_data[0]
r_data = raw_data[1]
data = json.loads(r_data)
outstr = json.dumps(data, indent=2)
PrintToFile("826_DOR.json", outstr)


