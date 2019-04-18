from cromulent.model import factory, \
	Identifier, Mark, ManMadeObject as Object, Type, \
	Person, Material, MeasurementUnit, Place, Dimension, Currency, \
	ConceptualObject, TimeSpan, Actor, PhysicalThing, Language, \
	LinguisticObject, InformationObject, \
	Activity, Group, Name, MonetaryAmount, PropertyInterest, \
	Destruction, AttributeAssignment, BaseResource, PhysicalObject, \
	Acquisition, ManMadeFeature, VisualItem, Set, \
	PropositionalObject, Payment, Creation, Phase

# TODO clarify how we add an ordering to the alternatite titles and other data attributes where ordering is important

o = Object("Irises");
p = Person("Van Gogh");

# Set Object URI
o.id = "https://data.getty.edu/museum/collection/object/826/";

# Set Classified As
o.classified_as = []

# Artwork
t = Type();
t.id = "http://vocab.getty.edu/aat/300133025"
t._label = "Artwork"
o.classified_as.append(t);

# Painting
t = Type();
t.id = "http://vocab.getty.edu/aat/300033618"
t._label = "Painting"
o.classified_as.append(t);

# Set Accession Number
o.identified_by = []
i = Identifier();
i.id = "https://data.getty,edu/museum/collection/identifier/?1"
i.content = "90.PA.20";
i._label = "Accession Number"
i.classified_as = []

# Set Accession Number Classification
t = Type()
t._label = "Accession Number"
t.id = "http://vocab.getty.edu/aat/300312355"
i.classified_as.append(t)
o.identified_by.append(i)

# Set Primary Title
n = Name()
n.id = "https://data.getty,edu/museum/collection/name/?1"
n.content = "Irises"
n.classified_as = []

# Set Primary Title Classification
# This is important as it denotes the title as being the primary out of any titles associated with the work
t = Type()
t.id = "http://vocab.getty.edu/aat/300404670"
t._label = "Primary Title"
n.classified_as.append(t)
o.identified_by.append(n)

# Add any Alternate Title(s); in this case just one (as an example)
n = Name()
n.id = "https://data.getty,edu/museum/collection/name/?2"
n.content = "IRISES"
o.identified_by.append(n)


print("Object Representation");
print("#####################");
print(factory.toString(o, compact=False))
print("");
print("Person Representation");
print("#####################");
print(factory.toString(p, compact=False))