from calendar import c
import logging
import re


logging.basicConfig(level=logging.DEBUG)

# make units a attribute of the parser to reduce parsing same units for almost every file
# could also parse doc in a seperate process if parsing a list of a few hundred filings


class ParserXBRL():
    def parse_xbrl(self, xbrl_file):
        xbrl = XBRLInstanceDocument()
        xbrl.contexts = self._get_contexts(xbrl_file.ins)
        xbrl.units = self._get_units(xbrl_file.ins)
        xbrl.facts = self._get_facts(xbrl_file.ins, xbrl)
        return xbrl
    
    def parse_instance_file(self, xbrl):
        pass

    def _get_contexts(self, instance_file):
        # print(set([i.name for i in instance_file.find_all()]))
        contexts = {}
        for i in instance_file.find_all("context"):
            context = self._parse_context(i)
            contexts[context.id] = context
        return contexts
    
    def _get_units(self, instance_file):
        units = {}
        for x in instance_file.find_all("unit"):
            id = self.normalize_unit_ref(x.attrs["id"])
            if id not in units.keys():
                units[id] = self._parse_unit(x)
            # units[id] = Unit(id)
        units["unspecified"] = Unit("unspecified")
        return units
            

    def _get_facts(self, instance_file, xbrl):
        # check for contextRef attribute in tag
        facts = {}
        def is_fact(tag):
            if "contextRef" in tag.attrs:
                return True
            else:
                return False

        for fact in instance_file.find_all(is_fact):
            parsed_fact = self._parse_fact(fact, xbrl.contexts, xbrl.units)
            specifier = parsed_fact.tag.specifier
            if specifier not in facts.keys():
                facts[specifier] = [parsed_fact]
            else:
                facts[specifier].append(parsed_fact)
        return facts
        
    
    def _parse_context(self, context):
        # print(context)
        id = context.attrs["id"]
        entity = self._parse_entity(context.find("entity"))
        period = self._parse_period(context.find("period"))
        # print(f"context: {context}")
        if (id and entity and period):
            return Context(id, entity, period)

    def _parse_unit(self, unit):
        if unit.find("divide"):
            try:
                numerator = self._parse_measure(
                    unit.find("unitNumerator").find("measure"))
                denominator = self._parse_measure(
                    unit.find("unitDenominator").find("measure"))
                return DivisionUnit(numerator, denominator)
            except AttributeError as e:
                logging.debug(f"couldnt parse divide unit: {unit}")
                return Unit("unparsable")
        else:
            measure = self._parse_measure(unit.find("measure"))
            return Unit(measure)

        # handle numerator/denominator units
        # make it so the unitRef isnt the part that stays important
        # as it can change while the underlying measure stays the same
        # that allows removal of normalize_unit_ref
        pass

    def _parse_measure(self, measure):
        if measure.string:
            vals = measure.string.split(":")
            if vals:
                try:
                    return vals[1]
                except IndexError:
                    return vals[0]
        else:
            raise AttributeError
                 

    def _parse_fact(self, fact, contexts, units):
        tag = Tag(fact.prefix, fact.name)
        unit_ref = self.normalize_unit_ref(fact.attrs["unitRef"]) if "unitRef" in fact.attrs else None
        context_ref = fact.attrs["contextRef"]
        decimals = fact.attrs["decimals"] if "decimals" in fact.attrs else None
        val = fact.string
        if (decimals == "INF") or (decimals is None):
            pass
        else:
            decimals = int(decimals)
            zeros = ""
            # create a dict for 0->-20 decimal adjustment as a constant
            # 
            
            if decimals < 0:
                # or just use val = float(val) * (10 ** abs(decimals))
                # but could introduce floatingPoint precision errors
                for x in range(abs(decimals)):
                    zeros = zeros + "0"
                val = val + zeros
            elif decimals == 0:
                pass
            elif decimals > 0:
                pass               
        value = Value(val, units[unit_ref]) if unit_ref else Value(val, units["unspecified"])
        context = contexts[context_ref]
        return Fact(tag, context, value)

    def _parse_period(self, period):
        start, end, instant = None, None, None
        for x in period.children:
            if x.name == "instant":
                return Instant(x.string)
            if x.name == "startDate":
                start = x.string
            if x.name == "endDate":
                end = x.string
        if (start and end) != None:
            return Period(start, end)
        logging.debug(f"unhandled case in _parse_period: {period}")
        return None

    
    def _parse_entity(self, entity):
        identifier, segment = None, Segment([])
        for x in entity.children:
            if x.name == "identifier":
                identifier = x.string
            if x.name == "segment":
                for member in x:
                    
                    if member.name == "explicitMember":
                        dimension = member.attrs["dimension"] if "dimension" in member.attrs.keys() else None
                        member_tag = member.string.split(":")
                        tag = Tag(member_tag[0], member_tag[1])
                        segment.members.append(ExplicitMember(dimension, tag))
                        # print(f"current members in segment: {len(segment.members)}")
                        
            if x.name == "scenario":
                logging.debug("SCENARIO TAG NOT IMPLEMENTED")
        return Entity(identifier, segment)
    
    
    def normalize_unit_ref(self, unit_ref):
        if isinstance(unit_ref, str):
            return unit_ref.lower().replace("_", "")
        else:
            raise ValueError(f"can only normalize strings, got: {type(unit_ref)}")





class XBRLFile():
    '''unparsed full text files that are needed to parse xbrl.
    label file for more readable keys: not implemented
    instance file for context, facts ect.
    ''' 
    def __init__(self, instance_file, label_file):
        self.ins = instance_file
        self.lab = label_file

class XBRLInstanceDocument():
    '''Object representation of relevant information of the instance file'''
    def __init__(self):
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

