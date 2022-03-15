import re



class XBRLInstanceDocument():
    '''Object representation of parsed relevant information of the instance file'''
    def __init__(self, info):
        self.info = info
        self.contexts = {}
        self.facts = {}
        self.units = {}
    
    def search_for_key(self, regex):
        match = []
        for key in self.facts.keys():
            if re.search(regex, key):
                match.append(key)
        return match
    
    def match_for_key(self, regex):
        match = []
        for key in self.facts.keys():
            if re.match(regex, key):
                match.append(key)
        return match
    

class Context():
    '''object representation of a <context> tag.
    example xml:
        <context id="if745c13b17f2451da3e609125ef1b62e_D20200101-20201231">
            <entity>...</entity>
            <period>...</period>
        </context>
    '''
    def __init__(self, id, entity, period, scenario=None):
        self.id = id
        self.entity = entity
        self.period = period
        self.scenario = scenario
    
    def __repr__(self):
        return "Context<id:"+self.id+" "+str(self.entity) + " " + str(self.period)+">" 


class Period():
    '''object representation of a <period> representing a span of time.
    example xml:
        <period>
            <startDate>2020-01-01</startDate>
            <endDate>2020-12-31</endDate>
        </period>
    '''
    def __init__(self, start, end):
        self.start = start
        self.end = end
    
    def __repr__(self):
        return "Period<"+str(self.start) + " to " + str(self.end)+">" 


class Instant():
    '''object representation of a <period> representing one point in time.
    example xml:
        <period>
            <instant>2020-06-30</instant>
        </period>
    '''
    def __init__(self, timestamp):
        self.timestamp = timestamp
    
    def __repr__(self):
        return "Instant<"+str(self.timestamp)+">"


class Segment():
    '''object representation of a <segment> tag.
    example xml:
        <segment>
            <xbrldi:explicitMember dimension="us-gaap:StatementClassOfStockAxis">us-gaap:CommonStockMember</xbrldi:explicitMember>
        </segment>
    '''
    def __init__(self, members=[]):
        self.members = members
    
    def __repr__(self):
        members_string = ""
        for m in self.members:
            members_string = members_string + str(m.tag) + ";"
        return "Segment<"+members_string+">"


class Entity():
    '''object representation of a <entity> tag.
    example xml:
        <entity>
            <identifier scheme="http://www.sec.gov/CIK">0001665300</identifier>
            <segment>...</segment>
        </entity>
    '''
    def __init__(self, identifier, segments=None):
        self.identifier = identifier
        self.segments = segments
    
    def __repr__(self):
        return "Entity<"+str(self.identifier) + " " + str(self.segments)+">"


class DivisionUnit():
    '''object representation of a <unit> tag, which presents as a ratio
    example xml:
    '''
    def __init__(self, numerator, denominator):
        self.numerator = numerator
        self.denominator = denominator
        self.name = str(numerator).lower() + " per " +str(denominator).lower()
    

class Unit():
    '''object representation of a <unit> tag.
    example xml:
        <unit id="usd">
            <measure>iso4217:USD</measure>
        </unit>
    '''
    def __init__(self, unit):
        self.unit = unit
    
    def __repr__(self):
        if self.unit == "number":
            return ""
        if self.unit == "usd":
            return "$"
        return str(self.unit)


class Value():
    '''object representation of a value found in a xbrl fact'''
    def __init__(self, value, unit=None):
        self.value = value
        self.unit = unit
    
    def __repr__(self):
        return str(self.value) +" "+ str(self.unit)


class Fact():
    '''object representation of a xbrl fact.
    example xml:
        <dei:EntityPublicFloat contextRef="i7e9c6efa" decimals="0" id="id31231" unitRef="usd">
            44457382
        </dei:EntityPublicFloat>
    '''
    def __init__(self, tag, context, value):
        self.tag = tag
        self.context = context
        self.value = value
    
    def __repr__(self):
        return "Fact<"+str(self.tag) + ": " + str(self.value) + " with: " + str(self.context)+">"


class Tag():
    '''object representation of a tag of the form classifier:specifier.
    example: us-gaap:WarrantMember
    '''
    def __init__(self, classifier, specifier):
        self.classifier = classifier
        self.specifier = specifier
    
    def __repr__(self):
        return str(self.classifier) + ":" + str(self.specifier)


class ExplicitMember():
    '''object representation of a <explicitMember> tag.
    example xml: 
        <xbrldi:explicitMember dimension="us-gaap:StatementClassOfStockAxis">
            us-gaap:WarrantMember
        </xbrldi:explicitMember>
    '''
    def __init__(self, dimension, tag):
        self.dimension = dimension
        self.tag = tag
    
    def __repr__(self):
        return str(self.tag) + " with dimension: " + str(self.dimension)


class Label():
    '''object representation of a <link:label> in a linkbase
    example:
        <link:label id="lab_dei_EntityAddressCityOrTown_label_en-US" xlink:label="lab_dei_EntityAddressCityOrTown" xlink:role="http://www.xbrl.org/2003/role/label" xlink:type="resource" xml:lang="en-US">
            Entity Address, City or Town
        </link:label>     
    '''
    def __init__(self, classifier, specifier, name):
        self.classifier = classifier
        self.specifier = specifier
        self.name = name
    
    def __repr__(self):
        return str(self.classifier) + ":" + str(self.specifier) + " represented as: " + str(self.name)