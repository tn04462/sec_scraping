import re
import logging



class XBRLInstanceDocument():
    '''Object representation of parsed relevant information of the instance file
    '''
    def __init__(self, info):
        self.info = info
        self.contexts = {}
        self.facts = {}
        self.units = {}
    
    def add_fact(self, fact):
        specifier = fact.tag.specifier
        if specifier not in self.facts.keys():
            self.facts[specifier] = []
        if fact not in self.facts[specifier]:
            self.facts[specifier].append(fact)
    
    def search_fact(self, specifier: str, member_specifier: str ="", namespace: str ="any", period="instant"):
        ''''tries to find a fact that matches params, returns those facts.
        params:
            member_specifier: "" = all
            period: "instant", "period" or "any" 
        '''
        found_keys = self.search_for_key(re.compile(specifier, re.I))
        matched_facts = []    
        for fk in found_keys:
            possible_facts = self.facts[fk]
            for pf in possible_facts:
                if pf.has_period(period):                          
                    if member_specifier == "":
                        matched_facts.append(pf)
                    elif pf.has_member(member_specifier) and pf.has_namespace(namespace):
                        matched_facts.append(pf)
        return matched_facts


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

class AbstractXBRLElement():
    '''to be subclassed only'''
    def __eq__(self, other):
        return (isinstance(other, self.__class__) and (self.__dict__ == other.__dict__))
    
    def __ne__(self, other):
        return not self.__eq__(other)
    

class Context(AbstractXBRLElement):
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
    
    def __str__(self):
        return "Context<id:"+self.id+" "+str(self.entity) + " " + str(self.period)+">" 


class Period(AbstractXBRLElement):
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
    
    def __str__(self):
        return str(self.start) + "_" + str(self.end) 


class Instant(AbstractXBRLElement):
    '''object representation of a <period> representing one point in time.
    example xml:
        <period>
            <instant>2020-06-30</instant>
        </period>
    '''
    def __init__(self, timestamp: str):
        self.timestamp = str(timestamp)
    
    def __str__(self):
        return self.timestamp


class Segment(AbstractXBRLElement):
    '''object representation of a <segment> tag.
    example xml:
        <segment>
            <xbrldi:explicitMember dimension="us-gaap:StatementClassOfStockAxis">us-gaap:CommonStockMember</xbrldi:explicitMember>
        </segment>
    '''
    def __init__(self, members: list =[]):
        self.members = members
        if self.members != []:
            self._has_members = True
        else:
            self._has_members = False
    
    def add_member(self, member):
        self.members.append(member)
        if self.members != []:
            self._has_members = True

    
    def __str__(self):
        members_string = ""
        for m in self.members:
            members_string = members_string + str(m.tag) + ";"
        return "Segment<"+members_string+">"


class Entity(AbstractXBRLElement):
    '''object representation of a <entity> tag.
    example xml:
        <entity>
            <identifier scheme="http://www.sec.gov/CIK">0001665300</identifier>
            <segment>...</segment>
        </entity>
    '''
    def __init__(self, identifier, segment=None):
        self.identifier = identifier
        self.segment = segment
    
    def __str__(self):
        return "Entity<"+str(self.identifier) + " " + str(self.segment)+">"


class DivisionUnit(AbstractXBRLElement):
    '''object representation of a <unit> tag, which presents as a ratio
    example xml:
    '''
    def __init__(self, numerator, denominator):
        self.numerator = numerator
        self.denominator = denominator
        self.name = str(numerator).lower() + " per " +str(denominator).lower()
    

class Unit(AbstractXBRLElement):
    '''object representation of a <unit> tag.
    example xml:
        <unit id="usd">
            <measure>iso4217:USD</measure>
        </unit>
    '''
    def __init__(self, unit: str):
        self.unit = unit
    
    def __str__(self):
        if self.unit == "number":
            return ""
        if self.unit == "usd":
            return "$"
        return str(self.unit)


class Value(AbstractXBRLElement):
    '''object representation of a value found in a xbrl fact'''
    def __init__(self, value, unit=None):
        self.value = value
        self.unit = unit
    
    def __str__(self):
        return str(self.value) +" "+ str(self.unit)


class Fact(AbstractXBRLElement):
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
 
        # maybe make attributes of facts more accessible like below
        self.period = self._get_period()
    
    def __str__(self):
        return "Fact<"+str(self.tag) + ": " + str(self.value) + " with: " + str(self.context)+">"
    
    def _get_period(self):
          return self.context.period
    
    def convert_to_dict(self):
        '''convert to a flatter dict. return the dict'''
        return {
            "namespace": self.tag.classifier,
            "specifier": self.tag.specifier,
            "value": self.value.value,
            "unit": str(self.value.unit),
            "period": str(self.period),
            "members": [str(x) for x in self.get_members_tags()],
            "identifier": self.context.entity.identifier
            }
    
    def get_members_tags(self):
        return [s.tag for s in  [m for m in self.context.entity.segment.members]]
    
    def has_period(self, period: str ="instant"):
        '''check if period is "instance",  regular "period" or either. returns boolean'''
        if period == "instant":
            if isinstance(self.period, Instant):
                return True
        if period == "period":
            if isinstance(self.period, Period):
                return True
        if (period == "any") and self.period:
            return True
        return False
    
    def has_namespace(self, namespace):
        if namespace == "any":
            return True
        if self.tag.classifier == namespace:
            return True
        else:
            return False

    def has_members(self):
        return self.context.entity.segment._has_members

    def has_member(self, specifier):
        if (specifier == ""):
            return True
        if (specifier == None):
            if self.has_members():
                return False
            else:
                return True
                # logging.debug(f"shouldnt be empty: {self.context.entity.segment.members}")
        regex = re.compile(str(specifier), re.I)
        members = [re.search(regex, m.tag.specifier) for m in self.context.entity.segment.members]
        if members != []:
            return True
        return False


class Tag(AbstractXBRLElement):
    '''object representation of a tag of the form classifier:specifier.
    example: us-gaap:WarrantMember
    '''
    def __init__(self, classifier, specifier):
        self.classifier = classifier
        self.specifier = specifier
    
    def __str__(self):
        return str(self.classifier) + ":" + str(self.specifier)


class ExplicitMember(AbstractXBRLElement):
    '''object representation of a <explicitMember> tag.
    example xml: 
        <xbrldi:explicitMember dimension="us-gaap:StatementClassOfStockAxis">
            us-gaap:WarrantMember
        </xbrldi:explicitMember>
    '''
    def __init__(self, dimension, tag):
        self.dimension = dimension
        self.tag = tag
    
    def __str__(self):
        return str(self.tag) + " with dimension: " + str(self.dimension)


class Label(AbstractXBRLElement):
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
    
    def __str__(self):
        return str(self.classifier) + ":" + str(self.specifier) + " represented as: " + str(self.name)