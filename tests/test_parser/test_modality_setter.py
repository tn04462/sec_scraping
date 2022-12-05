from main.parser.filing_nlp_modality import create_modality_setter
import spacy
from spacy.tokens import Span, Token, Doc


def test_modality_setter():
    nlp = spacy.load("en_core_web_lg")
    nlp.add_pipe("modality_setter")

    text = "We might issue securities after the date of issuance. We may be issuing new securities from time to time."

    doc = nlp(text)
    for marker_idx, scope_idxs in doc._.certainty_marker_map.items():
        scope = [doc[i] for i in scope_idxs]
        marker = doc[marker_idx]
        print(marker, scope)
    for token in doc:
        print(token._.certainty_info)
        

    assert 1 == 2

    