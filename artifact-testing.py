from cromulent.model import factory, \
	Identifier, Mark, ManMadeObject as Object, Type, \
	Person, Material, MeasurementUnit, Place, Dimension, Currency, \
	ConceptualObject, TimeSpan, Actor, PhysicalThing, Language, \
	LinguisticObject, InformationObject, \
	Activity, Group, Name, MonetaryAmount, PropertyInterest, \
	Destruction, AttributeAssignment, BaseResource, PhysicalObject, \
	Acquisition, ManMadeFeature, VisualItem, Set, \
	PropositionalObject, PropositionalObject as Exhibition, Payment, Creation, Phase, Birth, Death, TimeSpan, Production

import json

#j = {}
#j["@context"] = "https://linked.art/ns/v1/linked-art.json"
#j["id"] = "https://linked.art/example/object/46"
#j["identified_by"] = []

#print(json.dumps(j, indent=2))

# TODO clarify how we add an ordering to the alternatite titles and other data attributes where ordering is important

# Define Person Entity
p = Person("Van Gogh")

# print(dir(p));

# Set Person URI
p.id = "https://data.getty.edu/museum/collection/person/377/"
p._label = "Vincent van Gogh"

# Define Object Entity
o = Object("Irises")

# Set Object URI
o.id = "https://data.getty.edu/museum/collection/object/826/"
o._label = "Irises"

# TODO Set Object Creation Date(s)

# Set RightsStatements.org Assertion
l = LinguisticObject()
l.id = "http://rightsstatements.org/vocab/NoC-US/1.0/"
l.content = "No Copyright - United States"
t = Type()
t.id = "http://vocab.getty.edu/aat/300055547/"
t._label = "Rights Statement"
l.classified_as = t
t = Type()
t.id = "http://vocab.getty.edu/aat/300418049/"
t._label = "Brief Text"
l.classified_as = t
o.referred_to_by = l

# Set Object Artist/Maker Relationship(s)
a = Production()
a.id = "https://data.getty.edu/museum/collection/object/826/activity/produced-by/377/"
a._label = "Production of Artwork"
a.carried_out_by = p
o.produced_by = a

# Set Object Artwork Classification
t = Type()
t.id = "http://vocab.getty.edu/aat/300133025/"
t._label = "Artwork"
o.classified_as = t

# Set Object Painting Classification
t = Type()
t.id = "http://vocab.getty.edu/aat/300033618/"
t._label = "Painting"
o.classified_as = t

# Set Object Accession Number
i = Identifier()
i.id = "https://data.getty.edu/museum/collection/identifier/1/"
i.content = "90.PA.20"
i._label = "Accession Number"

# Set Object Accession Number Classification
t = Type()
t._label = "Accession Number"
t.id = "http://vocab.getty.edu/aat/300312355/"
i.classified_as = t
o.identified_by = i

# Set Object Primary Title & Set Primary Title Classification
# This is important as it denotes the title as being the primary out of any titles associated with the work
n = Name()
n.id = "https://data.getty.edu/museum/collection/object/826/name/1/"
n._label = "Primary Title"
n.content = "Irises"
t = Type()
t.id = "http://vocab.getty.edu/aat/300404670/"
t._label = "Primary Title"
n.classified_as = t
o.identified_by = n

# Add Object Alternate Title(s); in this case just one (as an example)
n = Name()
n.id = "https://data.getty.edu/museum/collection/object/826/name/2/"
n._label = "Example Secondary Title"
n.content = "IRISES"
o.identified_by = n

# Add Object Dimensions

# Add Object Width
d = Dimension()
d.id = "https://data.getty.edu/museum/collection/object/826/dimension/1/"
d.value = "29 1/4";
m = MeasurementUnit()
m.id = "http://vocab.getty.edu/aat/300379100/"
m._label = "inches"
d.unit = m
t = Type()
t.id = "http://vocab.getty.edu/aat/300055647/"
t._label = "Width"
d.classified_as = t
o.dimension = d

# Add Object Height
d = Dimension()
d.id = "https://data.getty.edu/museum/collection/object/826/dimension/2/"
d.value = "37 1/8"
m = MeasurementUnit()
m.id = "http://vocab.getty.edu/aat/300379100/"
m._label = "inches"
d.unit = m
t = Type()
t.id = "http://vocab.getty.edu/aat/300055644/"
t._label = "Height"
d.classified_as = t
o.dimension = d

# Add Object Dimensions Statement
l = LinguisticObject()
l.id = "https://data.getty.edu/museum/collection/object/826/dimension-statement/"
l.content = "74.3 × 94.3 cm (29 1/4 × 37 1/8 in.)"
t = Type()
t.id = "http://vocab.getty.edu/aat/300266036/"
t._label = "Dimension Statement"
l.classified_as = t
t = Type()
t.id = "http://vocab.getty.edu/aat/300418049/"
t._label = "Brief Text"
l.classified_as = t
o.referred_to_by = l

# Add Object Materials
m = Material()
m.id = "http://vocab.getty.edu/aat/300015050/"
m._label = "oil paint (paint)"
o.made_of = m

m = Material()
m.id = "http://vocab.getty.edu/aat/300014078/"
m._label = "canvas (textile material)"
o.made_of = m

# Add Object Material Description
l = LinguisticObject()
l.id = "https://data.getty.edu/museum/collection/object/826/material-statement/"
l.content = "Oil on canvas"
t = Type()
t.id = "http://vocab.getty.edu/aat/300010358/"
t._label = "Material Statement"
l.classified_as = t
t = Type()
t.id = "http://vocab.getty.edu/aat/300418049/"
t._label = "Brief Text"
l.classified_as = t
o.referred_to_by = l

# Add Object Description
l = LinguisticObject()
l.id = "https://data.getty.edu/museum/collection/object/826/description/"
l.content = "<p>In May 1889, after episodes of self-mutilation and hospitalization, Vincent van Gogh chose to enter an asylum in Saint-Rémy, France. There, in the last year before his death, he created almost 130 paintings. Within the first week, he began Irises, working from nature in the asylum's garden. The cropped composition, divided into broad areas of vivid color with monumental irises overflowing its borders, was probably influenced by the decorative patterning of Japanese woodblock prints.</p><p>There are no known drawings for this painting; Van Gogh himself considered it a study. His brother Theo quickly recognized its quality and submitted it to the Salon des Indépendants in September 1889, writing Vincent of the exhibition: \"[It] strikes the eye from afar. It is a beautiful study full of air and life.\"</p><p>Each one of Van Gogh's irises is unique. He carefully studied their movements and shapes to create a variety of curved silhouettes bounded by wavy, twisting, and curling lines. The painting's first owner, French art critic Octave Mirbeau, one of Van Gogh's earliest supporters, wrote: \"How well he has understood the exquisite nature of flowers!\"</p>"
t = Type()
t.id = "http://vocab.getty.edu/aat/300080091/"
t._label = "Description"
l.classified_as = t
t = Type()
t.id = "http://vocab.getty.edu/aat/300418049/"
t._label = "Brief Text"
l.classified_as = t
o.referred_to_by = l

# Add Object Culture Description
l = LinguisticObject()
l.id = "https://data.getty.edu/museum/collection/object/826/culture-statement/"
l.content = "Dutch"
t = Type()
# TODO What is the correct AAT ID for "Culture Statement"?
t.id = "http://vocab.getty.edu/aat/<culture-statement-id>/"
t._label = "Culture Statement"
l.classified_as = t
t = Type()
t.id = "http://vocab.getty.edu/aat/300418049/"
t._label = "Brief Text"
l.classified_as = t
o.referred_to_by = l

# Add Object Shows (VisualItem)
v = VisualItem()
v.id = "https://data.getty.edu/museum/collection/object/826/shows/1/"
pl = Place()
pl.id = "https://data.getty.edu/museum/collection/object/826/place/created/"
pl._label = "Saint Rémy, France"
n = Name()
n.id = "https://data.getty.edu/museum/collection/object/826/place/created/name/"
n.content = "Saint Rémy, France"
pl.identified_by = n
t = Type()
t.id = "http://vocab.getty.edu/page/aat/300008347/"
t._label = "Inhabited Place"
pl.classified_as = t
v.represents = pl
o.shows = v

# Add Object Main Image
v = VisualItem();
v.id = "http://media.getty.edu/museum/images/web/larger/00094701.jpg"
v._label = "Main Image"
t = Type();
t.id = "http://vocab.getty.edu/aat/300215302/"
t._label = "Digital Image"
v.classified_as = t
v.format = "image/jpeg"

# TODO How do we add InformationObjects to images? How do we define administrative attributes this way?
# i = InformationObject()
# i.id = "http://media.getty.edu/museum/images/web/larger/00094701.jpg/information/"
# i.content = "hello";
# v.information = i

o.representation = v

# Add Object Home Page
l = LinguisticObject()
l.id = "http://www.getty.edu/art/collection/objects/826/"
l._label = "Homepage for Object"
t = Type()
t.id = "http://vocab.getty.edu/aat/300264578/"
t._label = "Web Page"
l.classified_as = t
t = Type()
t.id = "http://vocab.getty.edu/aat/300404670/"
t._label = "Primary"
l.classified_as = t
l.format = "text/html"
o.subject_of = l

# Add Object's Current Location (Gallery/Storage)
pl = Place()
pl.id = "https://data.getty.edu/museum/collection/place/279/getty-center-west-pavilion-gallery-204/"
pl._label = "Getty Center, Museum West Pavilion, Gallery W204"

n = Name()
n.id = "https://data.getty.edu/museum/collection/place/279/getty-center-west-pavilion-gallery-204/name/"
n.content = "Getty Center, Museum West Pavilion, Gallery W204"

pl.identified_by = n
o.current_location = pl

# Add Ownership
g = Group()
g.id = "http://vocab.getty.edu/ulan/500115988/"
g._label = "J. Paul Getty Museum, Los Angeles, California"

t = Type()
t.id = "http://vocab.getty.edu/aat/300312281/"
t._label = "Museum"
g.classified_as = t

a = Acquisition()
a.id = "https://data.getty.edu/museum/collection/object/826/activity/acquisition/"
a._label = "Acquisition"
g.acquired_title_through = a

o.current_owner = g


# TODO Add Previous Ownership (Provenance)


# Add Exhibition History
e = Exhibition()
e.id = "https://data.getty.edu/museum/collection/exhibition/999/"
e._label = "Salon des Indépendants"

i = Identifier()
i.id = "https://data.getty.edu/museum/collection/exhibition/999/identifier/1/"
i._label = "Exhibition Name"
e.identified_by = i

n = Name()
n.id = "https://data.getty.edu/museum/collection/exhibition/999/name/"
n.content = "Salon des Indépendants"
e.identified_by = n

t = Type()
t.id = "http://vocab.getty.edu/aat/300417531/"
t._label = "Exhibition"
e.classified_as = t

e.about = []

ea = Activity()
ea.id = "https://data.getty.edu/museum/collection/exhibition/999/activity/"
ea._label = "Exhibition Activity"
t = Type()
t.id = "http://vocab.getty.edu/aat/300054766/"
t._label = "Exhibiting"
ea.classified_as = t

e.motivated = ea

c = Creation()
c.id = "https://data.getty.edu/museum/collection/exhibition/999/creation/"
c._label = "Creation"

cp = Person()
cp.id = "https://data.getty.edu/museum/collection/person/x/"
cp._label = "Curator"
c.carried_out_by = cp

e.created_by = c

a = Activity()
a.id = "https://data.getty.edu/museum/collection/exhibition/999/activity/"
a._label = "Salon des Indépendants"

a.timespan = TimeSpan()
a.timespan.id = "https://data.getty.edu/museum/collection/exhibition/999/time-span/"
a.timespan.begin_of_the_begin = ""
a.timespan.end_of_the_end     = ""
g = Group()
g.id = "https://data.getty.edu/museum/collection/group/x/"
g._label = "X"
t = Type()
t.id = "http://vocab.getty.edu/aat/300312281/"
t._label = "Museum"
g.classified_as = t
a.carried_out_by = g

# TODO How do we associate exhibitions with the Object?

# Serialize Object to JSON-LD representation
print("")
print("Object Representation")
print("#####################")
print(factory.toString(o, compact=False))

# NOTE To prevent all of the Person data being emitted as part of the related Object,
# we need to define the Person with only its top-level ID, then wait until the Object
# has been emitted before we add the rest of the detail to the Person. We can then emit
# the Person record seperately after having emitted the Object; it appears that CROM may
# not be aware of the "document boundaries" (if that is the correct term) to know to only
# include the reference to the Person in the Object, rather than including all of the data

# Add Person Primary Name
n = Name()
n.id = "https://data.getty.edu/museum/collection/person/377/name/1/"
n.content = "Vincent van Gogh"
t = Type()
t.id = "http://vocab.getty.edu/aat/300404670/"
t._label = "Primary Name"
n.classified_as = t
p.identified_by = n

# Add Person ULAN ID (if available)
t = Type()
t.id = "http://vocab.getty.edu/ulan/500115588-agent/"
t._label = "Vincent van Gogh"
p.exact_match = t

# Add Person Birth Date (Vincent van Gogh; Born 1853 in Zundert, The Netherlands)
b = Birth()
b.id = "https://data.getty.edu/museum/collection/person/377/activity/born/"
t = TimeSpan()
t.id = "https://data.getty.edu/museum/collection/person/377/time/born/"
t.begin_of_the_begin = "1853"
t.end_of_the_begin = "1853"
b.timespan = t
# Birth Place modeled via took_place_at: E21Person (P98) was born - E67 Birth (P7) took place at: E53 Place
# see http://www.cidoc-crm.org/Issue/ID-29-how-to-model-a-persons-birthplace
pl = Place()
pl.id = "https://data.getty.edu/museum/collection/person/377/place/born/"
pl._label = "Zundert, The Netherlands"
n = Name()
n.id = "https://data.getty.edu/museum/collection/person/377/place/born/name/"
n.content = "Zundert, The Netherlands"
pl.identified_by = n
t = Type()
t.id = "http://vocab.getty.edu/page/aat/300008347/"
t._label = "Inhabited Place"
pl.classified_as = t
b.took_place_at = pl
p.born = b

# print(dir(b))

# Add Person Death Date (Vincent van Gogh; Died 1899 in Auvers-sur-Oise, France)
d = Death()
d.id = "https://data.getty.edu/museum/collection/person/377/activity/died/"
t = TimeSpan()
t.id = "https://data.getty.edu/museum/collection/person/377/time/died/"
t.begin_of_the_end = "1890"
t.end_of_the_end = "1890"
d.timespan = t
# Death Place modeled via took_place_at: E21Person (P100) was death of (died in) - E69 Death (P7) took place at: E53 Place
# see http://www.cidoc-crm.org/Issue/ID-29-how-to-model-a-persons-birthplace
pl = Place()
pl.id = "https://data.getty.edu/museum/collection/person/377/place/died/"
pl._label = "Auvers-sur-Oise, France"
n = Name()
n.id = "https://data.getty.edu/museum/collection/person/377/place/died/name/"
n.content = "Auvers-sur-Oise, France"
pl.identified_by = n
t = Type()
t.id = "http://vocab.getty.edu/page/aat/300008347/"
t._label = "Inhabited Place"
pl.classified_as = t
d.took_place_at = pl
p.died = d

# Add Person Activity Start Date (if known)
# a = Activity()
# a.id = "https://data.getty.edu/museum/collection/activity/377/active/from/"
# p.carried_out = a

# Add Person Activity End Date (if known)
# a = Activity()
# a.id = "https://data.getty.edu/museum/collection/activity/377/active/to/"
# p.carried_out = a

# Add Person Nationality
t1 = Type()
t1.id = "http://vocab.getty.edu/aat/300111175/"
t1._label = "Dutch"
t2 = Type()
t2.id = "http://vocab.getty.edu/aat/300379842/"
t2._label = "Nationality"
t1.classified_as = t2
p.classified_as = t1

# Add Person Biography
l = LinguisticObject()
l.id = "https://data.getty.edu/museum/collection/person/377/biography/"
l.content = "<p>Art was Van Gogh's means of personal, spiritual redemption, and his voluminous letters to his devoted brother Theo, offer profound insight into the artistic struggle.</p><p>Van Gogh became an artist in 1881. Although he studied briefly in Antwerp and Paris, he was largely self-taught. He ultimately chose to live in the country, and most of his paintings capture his deep affinity for nature. Theo, an art dealer, introduced Vincent to Paris's most advanced painters, and his work changed under the influences of Edgar Degas, Paul Gauguin, Georges Seurat, and Henri de Toulouse-Lautrec. The flatness of color and shape in Japanese <term>woodcuts</term> also inspired him.</p><p>Van Gogh's color expressed his emotions as he responded to the world. His insistence on color's expressive possibilities led him to develop a corresponding expressiveness in applying <term>pigment</term>. His brushstrokes of thick, opaque paint almost seem drawn. His often violently interacting colors and forms and strong expressive line influenced nearly every artistic movement that came after him: <term>Symbolism</term>, <term>Fauvism</term>, <term>Expressionism</term>, and beyond.</p>"
t = Type()
t.id = "http://vocab.getty.edu/aat/300080102/"
t._label = "Biography Statement"
l.classified_as = t
p.referred_to_by = l

# Serialize Person to JSON-LD representation
# print("")
# print("Person Representation")
# print("#####################")
# print(factory.toString(p, compact=False))