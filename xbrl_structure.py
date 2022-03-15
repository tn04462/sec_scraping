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
    
    def get_fact(self, specifier, member_specifier, namespace="any"):
        found_keys = self.search_for_key(re.compile(specifier, re.I))
        # logging.debug(found_keys)
        valid_facts = []
        for fk in found_keys:
            possible_facts = self.facts[fk]
            for pf in possible_facts:                   
                if member_specifier == "":
                    valid_facts.append(pf)
                elif pf.has_member(member_specifier) is True and self.is_fact_in_namespace(pf, namespace):
                    valid_facts.append(pf)
        print(valid_facts)
    
    def is_fact_in_namespace(self, fact, namespace):
        if namespace == "any":
            return True
        if fact.tag.classifier == namespace:
            return True
        else:
            return False


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
        if self.members != []:
            self._has_members = True
        else:
            self._has_members = False
    
    def add_member(self, member):
        self.members.append(member)
        if self.members != []:
            self._has_members = True

    
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
    def __init__(self, identifier, segment=None):
        self.identifier = identifier
        self.segment = segment
    
    def __repr__(self):
        return "Entity<"+str(self.identifier) + " " + str(self.segment)+">"


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

        
        # maybe make attributes of facts more accessible like that
        # self.period = self._get_period()
        # def _get_period(self):
        #   return self.context.period
    
    def __repr__(self):
        return "Fact<"+str(self.tag) + ": " + str(self.value) + " with: " + str(self.context)+">"

    def get_members_tags(self):
        return [s.tag for s in  [m for m in self.context.entity.segment.members]]
    
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