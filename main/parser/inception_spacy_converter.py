from cgi import test
from lib2to3.pgen2 import token
from cassis import *
from spacy.tokens import Span, DocBin, Doc
from spacy.vocab import Vocab
from spacy.tokenizer import Tokenizer
from spacy.lang.en import English
from spacy.util import compile_infix_regex
import spacy

import numpy as np

##laptop
test_typesystem = r"C:\Users\Olivi\Desktop\test_set\training_set\TypeSystem.xml"
test_xmi = r"C:\Users\Olivi\Desktop\test_set\training_set\k8s200v2.xmi"
##desktop
# test_typesystem = r"E:\pysec_test_folder\training_sets\training_set_8k_item801_securities_detection_annotated_138Filings\TypeSystem.xml"
# test_xmi = r"E:\pysec_test_folder\training_sets\training_set_8k_item801_securities_detection_annotated_138Filings\k8s200v2.xmi"
nlp = spacy.blank("en")

TOKEN_TAG = "de.tudarmstadt.ukp.dkpro.core.api.segmentation.type.Token"

#  mostly unused 
docs = {"train": [], "test": [], "dev": [], "total": []}
ids = {"train": set(), "test": set(), "dev": set(), "total": set()}
count_all = {"train": 0, "test": 0, "dev": 0, "total": 0}
count_valid = {"train": 0, "test": 0, "dev": 0, "total": 0}



def convert_relation_ner_to_doc(typesysteme_filepath, xmi_filepath):
    '''convert a UIMA CAS XMI (XML 1.0) Entity Relation File into a spaCy Doc.
    
    currently only supports one layer of custom Relation and Span which are labeled as 
    custom.Relation and custom.Span.

    Args:
        typesysteme_filepath: path to a valid typesystem.xml
        xmi_filepath: path to a valid .xmi file

    Returns:
        spaCy Doc Object 
    '''
    # declare new extension for relational data
    Doc.set_extension("rel", default={}, force=True)
    # load the annotations with cassis
    with open(typesysteme_filepath, 'rb') as f:
        typesystem = load_typesystem(f)
    with open(xmi_filepath, 'rb') as f:
        annotations = load_cas_from_xmi(f, typesystem=typesystem)
    tokens = annotations.select(TOKEN_TAG)
    doc = Doc(vocab=nlp.vocab, words=[t.get_covered_text() for t in tokens])
    token_start_idx_map = {}
    for idx in range(len(tokens)):
        token_start_idx_map[tokens[idx]["begin"]] =  idx

    
    # convert the span entities and add to doc
    #   here i could go layer by layer to cover other use cases with multiple custom layers
    entities = []
    relations = {}
    span_starts = set()
    span_start_token_map = {}
    map_labels = {}
    
    for span in annotations.select("custom.Span"):
        # ignore invalid/nameless annotations
        # print(span)
        if span["Labels"] is None:
            continue
        
        doc.char_span(span["begin"], span["end"], label=span["Labels"])
        span_starts.add(span["begin"])
        span_start_token_map[span["begin"]] = token_start_idx_map[span["begin"]]

    doc.ents = entities
    # print(len(span_starts))
    # print(len(token_start_idx_map))
    # print(len(span_start_token_map))
    # for x1 in token_idx_map.values():
    #     for x2 in token_idx_map.values():
    #         relations[(x1, x2)] = {}
    

    for relation in annotations.select("custom.Relation"):
        # print(relation)
        label = relation["Labels"]
        if label not in map_labels:
            map_labels[label] = label
            # replace with token_idx_map$
        try:
            start = span_start_token_map[relation["Governor"]["begin"]]
            end = span_start_token_map[relation["Dependent"]["begin"]]
        except KeyError as e:
            print(f"couldnt find token from relations span when converting to docbin")
            try:
                start = token_start_idx_map[relation["Governor"]["begin"]]
                end = token_start_idx_map[relation["Dependent"]["begin"]]
            except KeyError as e:
                print(f"also failed backup plan for finding relation so skipping")
            continue
        if (start, end) not in relations.keys():
            relations[(start, end)] = {}
        if label not in relations[(start, end)]:
            relations[(start, end)][label] = 1.0
        # if label not in relations[(start, end)]:
        #     relations[(start, end)][label] = 1.0
    # for x1 in token_idx_map.values():
    #     for x2 in token_idx_map.values():
    #         for label in map_labels.values():
    #             if label not in relations[(x1, x2)]:
    #                 relations[(x1, x2)][label] = 0.0
    doc._.rel = relations
    return doc     
        
def docs_to_training_file(docs: list[Doc], save_path: str):
    '''create a docBin from a list of Docs and save it to save_path'''
    docbin = DocBin(docs=docs, store_user_data=True)
    docbin.to_disk(save_path)



doc = convert_relation_ner_to_doc(test_typesystem, test_xmi)
docs_to_training_file((doc,), r"C:\Users\Olivi\Desktop\spacy_example2.spacy")
# npa = doc.to_array()

# print(npa, type(npa))

# t = "San Fransico is a nice place."
# nlp = spacy.load("en_core_web_trf")
# doc = nlp(t)
# print([e for e in doc])
# print([doc[t].text for t in range(len(doc))])
# print([t.ent_iob for t in doc])

# from spacy import displacy
# displacy.serve(doc, style="ent")    

