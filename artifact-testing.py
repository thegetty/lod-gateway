from cromulent.model import factory, \
	Identifier, Mark, ManMadeObject as Object, Type, \
	Person, Material, MeasurementUnit, Place, Dimension, Currency, \
	ConceptualObject, TimeSpan, Actor, PhysicalThing, Language, \
	LinguisticObject, InformationObject, \
	Activity, Group, Name, MonetaryAmount, PropertyInterest, \
	Destruction, AttributeAssignment, BaseResource, PhysicalObject, \
	Acquisition, ManMadeFeature, VisualItem, Set, \
	PropositionalObject, Payment, Creation, Phase

o = Object("Irises");
p = Person("Van Gogh");

# Set Object URI
o.id = "https://data.getty.edu/museum/object/826/";

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
i.id = "https://data.getty,edu/museum/identifier/?1"
i.content = "90.PA.20";
i._label = "Accession Number"
i.classified_as = []
t = Type()
t._label = "Accession Number"
t.id = "http://vocab.getty.edu/aat/300312355"
i.classified_as.append(t)
o.identified_by.append(i)

# Set Title
n = Name()
n.id = "https://data.getty,edu/museum/name/?1"
n.content = "Irises"
n.classified_as = []
t = Type()
t.id = "http://vocab.getty.edu/aat/300404670"
t._label = "Primary Title"
n.classified_as.append(t)
o.identified_by.append(n)

n = Name()
n.id = "https://data.getty,edu/museum/name/?2"
n.content = "IRISES"
o.identified_by.append(n)


print factory.toString(o, compact=False)