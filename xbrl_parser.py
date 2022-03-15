from xbrl_structure import *

import logging
logging.basicConfig(level=logging.DEBUG)

# make units a attribute of the parser to reduce parsing same units for almost every file
# could also parse doc in a seperate process if parsing a list of a few hundred filings


class ParserXBRL():
    def parse_xbrl(self, xbrl_file):
        xbrl = XBRLInstanceDocument(xbrl_file.info)
        xbrl.contexts = self._get_contexts(xbrl_file.ins)
        xbrl.units = self._get_units(xbrl_file.ins)
        xbrl.facts = self._get_facts(xbrl_file.ins, xbrl)
        return xbrl
    
    # def parse_instance_file(self, xbrl):
    #     pass

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
                        segment.add_member(ExplicitMember(dimension, tag))
                        # print(f"current members in segment: {len(segment.members)}")
                        
            if x.name == "scenario":
                logging.debug("SCENARIO TAG NOT IMPLEMENTED")
        return Entity(identifier, segment)
    
    
    def normalize_unit_ref(self, unit_ref):
        if isinstance(unit_ref, str):
            return unit_ref.lower().replace("_", "")
        else:
            raise ValueError(f"can only normalize strings, got: {type(unit_ref)}")







