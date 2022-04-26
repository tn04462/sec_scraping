from lib2to3.pgen2 import token
from cassis import *
from spacy.tokens import Span, DocBin, Doc
from spacy.vocab import Vocab
from spacy.lang.en import English
from spacy.util import compile_infix_regex
import spacy
from bisect import bisect_left
import typer 

import numpy as np

##laptop
# test_typesystem = r"C:\Users\Olivi\Desktop\test_set\training_set\TypeSystem.xml"
# test_xmi = r"C:\Users\Olivi\Desktop\test_set\training_set\k8s200v2.xmi"
# ##desktop
test_typesystem = r"C:\Users\Olivi\Testing\sec_scraping\main\parser\spacy_model\raw_training_data\TypeSystem.xml"
test_xmi = r"C:\Users\Olivi\Testing\sec_scraping\main\parser\spacy_model\raw_training_data\k8s200v2.xmi"
nlp = spacy.blank("en")

TOKEN_TAG = "de.tudarmstadt.ukp.dkpro.core.api.segmentation.type.Token"
SENTENCE_TAG = "de.tudarmstadt.ukp.dkpro.core.api.segmentation.type.Sentence"

#  mostly unused 
# docs = {"train": [], "test": [], "dev": [], "total": []}
# ids = {"train": set(), "test": set(), "dev": set(), "total": set()}
# count_all = {"train": 0, "test": 0, "dev": 0, "total": 0}
# count_valid = {"train": 0, "test": 0, "dev": 0, "total": 0}

'''
Useful for:
    currently only tested for converting Inception UIMA CAS XMI (XML 1.0)
    having 1 custom Span and 1 custom Relations Layer 
    to spaCy Docs. 

Usage:
    docs = convert_relation_ner_to_doc(path_to/typestysteme.xml, path_to/file.xmi, split=3, split_feature="custrom.Span")
'''

def take_closest(myList, myNumber):
    """
    https://stackoverflow.com/questions/12141150/from-list-of-integers-get-number-closest-to-a-given-value
    Assumes myList is sorted. Returns closest value to myNumber.

    If two numbers are equally close, return the smallest number.
    """
    pos = bisect_left(myList, myNumber)
    if pos == 0:
        return myList[0]
    if pos == len(myList):
        return myList[-1]
    before = myList[pos - 1]
    after = myList[pos]
    if after - myNumber < myNumber - before:
        return after
    else:
        return before


def get_feature_split_idxs(cas: Cas, split: int= 10, feature=TOKEN_TAG):
    '''get character bounds of n splits when we split by "feature"  while respecting
    the closest sentence end bound as a cutoff point, mostlikely results in less 
    parts than declared with split if we have very long sentences.
    This approache loses features(in my case: relations) 
    that go across the boundry of the last sentence!! '''
    split_token_bounds = []
    sentence_end_start_map = {}
    sentence_start_end_map = {}
    for sent in cas.select(SENTENCE_TAG):
        sentence_end_start_map[sent["end"]] = sent["begin"]
        sentence_start_end_map[sent["begin"]] = sent["end"]
    sentence_end_keys = list(sentence_end_start_map.keys())
    sentence_start_keys = list(sentence_start_end_map.keys())
    split_features = cas.select(feature)
    len_split_features = len(split_features)
    min_feature_set_size = int(len_split_features / split)
    feature_count = 0
    is_past_feature_size = False
    last_sentence = None
    start = None
    for idx, feature in enumerate(split_features):
        # account for first segment
        if (feature_count == 0) and (start is None):
            start = 0
        else:
            if is_past_feature_size is True:
                if last_sentence is None:
                    raise ValueError("last_sentence was None despite that it shouldnt be in this case")
                if feature["begin"] >= last_sentence["end"]:
                    # add entry of completed segment
                    split_token_bounds.append({"begin": start, "end": last_sentence["end"], "feature_count": feature_count})
                    # set new start of segment
                    start = take_closest(sentence_start_keys, last_sentence["end"])
                    # reset flags and the feature count
                    last_sentence = None
                    is_past_feature_size = False
                    feature_count = 0
            if (feature_count >= min_feature_set_size) and (last_sentence is None):
                is_past_feature_size = True
                sentence_start = take_closest(sentence_start_keys, feature["begin"])
                sentence_end = take_closest(sentence_end_keys, feature["begin"])
                if (sentence_start > sentence_end) and (feature["end"] < sentence_start):
                    last_sentence = {"begin": sentence_end_start_map[sentence_end], "end": sentence_end}
                    if feature["end"] > sentence_end:
                        print(True, sentence_start, sentence_end, sentence_end_start_map[sentence_end])
                else:
                    last_sentence = {"start": sentence_start, "end": sentence_start_end_map[sentence_start]}

        feature_count += 1
        # account for the last segment that isnt going to be longer than min_feature_size.
        # last feature!
        if idx == len_split_features:
            split_token_bounds.append({"begin": start, "end": sentence_end_keys[-1], "feature_count": feature_count})
    return split_token_bounds

                 
    
def cas_select_split(bound_start: int, bound_end: int, select_result: list):
    '''get segment of select_result between bound_start and bound_end.
    
    Args:
        bound_start: index of starting char of the token, so far found in the
                            Feature: de.tudarmstadt.ukp.dkpro.core.api.segmentation.type.Token as "begin"
        bound_end: index of last char of the token, so far found in the
                            Feature: de.tudarmstadt.ukp.dkpro.core.api.segmentation.type.Token as "end"
        select_result: return from a Cas.select() call'''
    valid_items = []
    for feature in select_result:
        if (feature["begin"] >= bound_start) and (feature["end"] <= bound_end):
            valid_items.append(feature)
    return valid_items

def convert_relation_ner_to_doc2(typesysteme_filepath, xmi_filepath):
    '''convert a UIMA CAS XMI (XML 1.0) Entity Relation File into a spaCy Doc.
    
    currently only tested/supports one layer of custom Relation and Span which are labeled as 
    custom.Relation and custom.Span.

    Args:
        typesysteme_filepath: path to a valid typesystem.xml
        xmi_filepath: path to a valid .xmi file
        split: how many docs you would like at most. will try to get as close while keeping
        the feature count of the split_feature as equal as possible. will mostikely result in
        number of segments being lower than split.
        split_feature: the xml tag to try and split evenly by. eg: custom.Relation 

    Returns:
        spaCy Doc Object 
    '''

    # print(locals())
    # declare new extension for relational data
    Doc.set_extension("rel", default={}, force=True)
    vocab = Vocab()
    # load the annotations with cassis
    with open(typesysteme_filepath, 'rb') as f:
        typesystem = load_typesystem(f)
    with open(xmi_filepath, 'rb') as f:
        annotations = load_cas_from_xmi(f, typesystem=typesystem)
    tokens = list(annotations.select(TOKEN_TAG))
    doc = Doc(vocab=vocab, words=[t.get_covered_text() for t in tokens])
    spacy_offset = {}
    token_start_idx_map = {}
    span_starts = set()
    span_start_token_map = {}
    map_labels = set()
    entities = []
    relations = {}
    
    pos = 0
    neg = 0
    # create map of offsets to fix the token offset problem between spaCy and inception
    st = nlp(" ".join([t.get_covered_text().strip() for t in tokens]))
    sdoc = nlp(st)
    # for idx in range(100):
    #     # print(tokens[idx].get_covered_text(), doc[idx])
    #     print(tokens[idx]["begin"] - doc[idx].idx, len(tokens[idx].get_covered_text()), len(doc[idx]), tokens[idx].get_covered_text(), doc[idx])
    
    for idx in range(len(tokens)):
        token_start = tokens[idx]["begin"]
        token_end = tokens[idx]["end"]
        print(doc[idx])
        if idx != doc[idx].i:
            raise ValueError("whilen creating offset map, tokens didnt align properly")
        spacy_offset[token_start] = sdoc[idx].idx - token_start
        spacy_offset[token_end] = sdoc[idx].idx - token_start
        token_start_idx_map[token_start + spacy_offset[token_start]] =  idx    
    # convert the span entities and add to doc
    #   here we could go layer by layer to cover other use cases with multiple custom layers
    for span in annotations.select("custom.Span"):
        # ignore invalid/nameless annotations
        if span["Labels"] is None:
            continue
        # print([(type(span[r]), span[r]) for r in ["begin", "end"]])
        span_spacy_start = span["begin"] + spacy_offset[span["begin"]]
        span_spacy_end = span["end"] + spacy_offset[span["end"]]

        entity = doc.char_span(
            span_spacy_start,
            span_spacy_end,
            span["Labels"])
        span_start_token_map[span_spacy_start] = token_start_idx_map[span_spacy_start]
        span_starts.add(token_start_idx_map[span_spacy_start])
        if entity is not None:
            entities.append(entity)
    print(entities)
    doc.set_ents(entities)
    
    # print(len(token_start_idx_map))
    # print(len(span_start_token_map))
    for x1 in span_starts:
        for x2 in span_starts:
            relations[(x1, x2)] = {}
    

    for relation in annotations.select("custom.Relation"):
        # print(relation)
        label = relation["label"]
        if label is None:
            neg += 1
            continue
        if label not in map_labels:
            map_labels.add(label)
        try:
            start = span_start_token_map[relation["Governor"]["begin"] + spacy_offset[relation["Governor"]["begin"]]]
            end = span_start_token_map[relation["Dependent"]["begin"] + spacy_offset[relation["Dependent"]["begin"]]]
        except KeyError as e:
            # print(f"couldnt find token from relations span when converting to docbin")
            try:
                start = token_start_idx_map[relation["Governor"]["begin"] + spacy_offset[relation["Governor"]["begin"]]]
                end = token_start_idx_map[relation["Dependent"]["begin"] + spacy_offset[relation["Dependent"]["begin"]]]
            except KeyError as e:
                print(f"also failed backup plan for finding relation")
            continue
        if (start, end) not in relations.keys():
            relations[(start, end)] = {}
        if label not in relations[(start, end)]:
            relations[(start, end)][label] = 1.0
            pos += 1
    
    # fill none occurence of relation as zeros
    for x1 in span_starts:
        for x2 in span_starts:
            for label in map_labels:
                if label not in relations[(x1, x2)]:
                    relations[(x1, x2)][label] = 0.0
    doc._.rel = relations
    return doc     

def convert_relation_ner_to_doc(typesysteme_filepath, xmi_filepath, split: int = 100, split_feature: str = "custom.Relation"):
    '''convert a UIMA CAS XMI (XML 1.0) Entity Relation File into a spaCy Doc.
    
    currently only tested/supports one layer of custom Relation and Span which are labeled as 
    custom.Relation and custom.Span.

    Args:
        typesysteme_filepath: path to a valid typesystem.xml
        xmi_filepath: path to a valid .xmi file
        split: how many docs you would like at most. will try to get as close while keeping
        the feature count of the split_feature as equal as possible. will mostikely result in
        number of segments being lower than split.
        split_feature: the xml tag to try and split evenly by. eg: custom.Relation 

    Returns:
        spaCy Doc Object 
    '''

    # print(locals())
    # declare new extension for relational data
    Doc.set_extension("rel", default={}, force=True)
    vocab = Vocab()
    # load the annotations with cassis
    with open(typesysteme_filepath, 'rb') as f:
        typesystem = load_typesystem(f)
    with open(xmi_filepath, 'rb') as f:
        annotations = load_cas_from_xmi(f, typesystem=typesystem)
    feature_split_idxs = get_feature_split_idxs(cas=annotations, split=split, feature=split_feature)
    all_tokens = list(annotations.select(TOKEN_TAG))
    docs = []
    for segment in feature_split_idxs:
        # print(segment)
        bound_start = segment["begin"]
        bound_end = segment["end"]
        tokens = cas_select_split(bound_start, bound_end, all_tokens)
        doc = Doc(vocab=vocab, words=[annotations.get_covered_text(t) for t in tokens])
        token_start_idx_map = {}
        entities = []
        relations = {}
        span_starts = set()
        span_start_token_map = {}
        map_labels = set()
        pos = 0
        neg = 0

        
        for idx in range(len(tokens)):
            token_start_idx_map[tokens[idx]["begin"]] =  idx 
        # convert the span entities and add to doc
        #   here i could go layer by layer to cover other use cases with multiple custom layers
        
        for span in cas_select_split(bound_start, bound_end, annotations.select("custom.Span")):
            # ignore invalid/nameless annotations
            # print(span)
            if span["Labels"] is None:
                continue
            # print([(type(span[r]), span[r]) for r in ["begin", "end"]])
            entity = doc.char_span(span["begin"], span["end"], span["Labels"])
            span_start_token_map[span["begin"]] = token_start_idx_map[span["begin"]]
            span_starts.add(token_start_idx_map[span["begin"]])
            if entity is not None:
                entities.append(entity)
        print(entities)
        doc.set_ents(entities)
        
        # print(len(token_start_idx_map))
        # print(len(span_start_token_map))
        for x1 in span_starts:
            for x2 in span_starts:
                relations[(x1, x2)] = {}
        

        for relation in cas_select_split(bound_start, bound_end, annotations.select("custom.Relation")):
            # print(relation)
            label = relation["label"]
            if label is None:
                neg += 1
                continue
            if label not in map_labels:
                map_labels.add(label)
            try:
                start = span_start_token_map[relation["Governor"]["begin"]]
                end = span_start_token_map[relation["Dependent"]["begin"]]
            except KeyError as e:
                # print(f"couldnt find token from relations span when converting to docbin")
                try:
                    start = token_start_idx_map[relation["Governor"]["begin"]]
                    end = token_start_idx_map[relation["Dependent"]["begin"]]
                except KeyError as e:
                    print(f"also failed backup plan for finding relation")
                continue
            if (start, end) not in relations.keys():
                relations[(start, end)] = {}
            if label not in relations[(start, end)]:
                relations[(start, end)][label] = 1.0
                pos += 1
        
        # fill none occurence of relation as zeros
        for x1 in span_starts:
            for x2 in span_starts:
                for label in map_labels:
                    if label not in relations[(x1, x2)]:
                        relations[(x1, x2)][label] = 0.0
        doc._.rel = relations
        if pos > 0:
            docs.append(doc)
    return docs   
        
def docs_to_training_file(docs: list[Doc], save_path: str):
    '''create a docBin from a list of Docs and save it to save_path'''
    docbin = DocBin(docs=docs, store_user_data=True)
    docbin.to_disk(save_path)


def main(typesysteme_path: str, xmi_path: str, train_path: str, dev_path: str, test_path: str, split: int=13):
    '''split documents into parts and then split into train/dev/test (70/20/10)'''
    docs = convert_relation_ner_to_doc(typesysteme_path, xmi_path, split=split)
    test = [docs[9]]
    dev = docs[7:8]
    train = docs[:6]
    docs_to_training_file(dev, dev_path)
    docs_to_training_file(train, train_path)
    docs_to_training_file(test, test_path)


if __name__ == "__main__":
    # docs = convert_relation_ner_to_doc(test_typesystem, test_xmi, split = 13)
    doc = convert_relation_ner_to_doc2(r"E:\pysec_test_folder\v1\TypeSystem.xml", r"E:\pysec_test_folder\v1\k8s1v1.xmi")
    # print(len(docs), docs)
    # test = [docs[9]]
    # dev = docs[7:8]
    # train = docs[:6]
    # print(test, dev, train)
    # typer.run(main)
    # testing start
        # print([t.get_covered_text() for t in tokens][:2])

    # files = [(r"E:\pysec_test_folder\v1\TypeSystem.xml", r"E:\pysec_test_folder\v1\k8s1v1.xmi"), (r"E:\pysec_test_folder\v2\TypeSystem.xml", r"E:\pysec_test_folder\v2\k8s1v2.xmi")]

    # for file in files:
    #     Doc.set_extension("rel", default={}, force=True)
    #     vocab = Vocab()
    #     # load the annotations with cassis
    #     with open(file[0], 'rb') as f:
    #         typesystem = load_typesystem(f)
    #     with open(file[1], 'rb') as f:
    #         annotations = load_cas_from_xmi(f, typesystem=typesystem)
    #     tokens = annotations.select(TOKEN_TAG)
    #     ws = [t.get_covered_text() for t in tokens]
    #     doc = Doc(vocab=vocab, words=ws)
    #     print(doc[:100])
    #     # print(annotations)
    
    
    # # testing end

