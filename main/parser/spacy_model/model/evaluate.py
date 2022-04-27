import random
from typing import Any, Dict, Iterable
import typer
from pathlib import Path
import spacy
from spacy.tokens import DocBin, Doc
from spacy.training.example import Example

from spacy.scorer import PRFScore, Scorer, get_ner_prf

# make the factory work
from rel_pipe import make_relation_extractor, score_relations

# make the config work
from rel_model import create_relation_model, create_classification_layer, create_instances, create_tensors

def main(trained_pipeline: Path, test_data: Path, print_details: bool):
    
    main_ner(trained_pipeline=trained_pipeline, test_data=test_data, print_details=print_details)
    main_relations(trained_pipeline=trained_pipeline, test_data=test_data, print_details=print_details)

def main_relations(trained_pipeline: Path, test_data: Path, print_details: bool):
    nlp = spacy.load(trained_pipeline)

    doc_bin = DocBin(store_user_data=True).from_disk(test_data)
    docs = doc_bin.get_docs(nlp.vocab)
    examples = []
    for gold in docs:
        pred = Doc(
            nlp.vocab,
            words=[t.text for t in gold],
            spaces=[t.whitespace_ for t in gold],
        )
        pred.ents = gold.ents
        for name, proc in nlp.pipeline:
            pred = proc(pred)
        examples.append(Example(pred, gold))

        # Print the gold and prediction, if gold label is not 0
        if print_details:
            print()
            print(f"Text: {gold.text}")
            print(f"spans: {[(e.start, e.text, e.label_) for e in pred.ents]}")
            for value, rel_dict in pred._.rel.items():
                try:
                    gold_labels = [k for (k, v) in gold._.rel[value].items() if v == 1.0]
                    if gold_labels:
                        print(
                            f" pair: {value} --> gold labels: {gold_labels} --> predicted values: {rel_dict}"
                        )
                except Exception as e:
                    print(e)
            print()

    random_examples = []
    docs = doc_bin.get_docs(nlp.vocab)
    for gold in docs:
        pred = Doc(
            nlp.vocab,
            words=[t.text for t in gold],
            spaces=[t.whitespace_ for t in gold],
        )
        pred.ents = gold.ents
        relation_extractor = nlp.get_pipe("relation_extractor")
        get_instances = relation_extractor.model.attrs["get_instances"]
        for (e1, e2) in get_instances(pred):
            offset = (e1.start, e2.start)
            if offset not in pred._.rel:
                pred._.rel[offset] = {}
            for label in relation_extractor.labels:
                pred._.rel[offset][label] = random.uniform(0, 1)
        random_examples.append(Example(pred, gold))

    thresholds = [0.000, 0.050, 0.100, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.99, 0.999]
    print()
    print("[Relations Component] Random baseline:")
    _score_and_format_relations(random_examples, thresholds)

    print()
    print("[Relations Component] Results of Trained Model")
    _score_and_format_relations(examples, thresholds)

def main_ner(trained_pipeline: Path, test_data: Path, print_details: bool):
    nlp = spacy.load(trained_pipeline)
    doc_bin = DocBin(store_user_data=True).from_disk(test_data)
    docs = doc_bin.get_docs(nlp.vocab)
    examples = []
    for gold in docs:
        pred = Doc(
            nlp.vocab,
            words=[t.text for t in gold],
            spaces=[t.whitespace_ for t in gold],
        )
        for name, proc in nlp.pipeline:
            pred = proc(pred)
        examples.append(Example(pred, gold))

    

    thresholds = [0.000, 0.050, 0.100, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.99, 0.999]
    print()
    print("Results of get_ner_prf:")
    print(get_ner_prf(examples))
    print()
    print("[NER] Results of Trained Model")
    _score_and_format_ner(examples)

def score_ner(examples: Iterable[Example]) -> Dict[str, Any]:
    """Score a batch of examples."""
    micro_prf = PRFScore()
    for example in examples:
        gold_map = {}
        gold = example.reference.ents
        pred = example.predicted.ents
        for gold_span in gold:
            gold_map[(gold_span.start, gold_span.end)] = gold_span
        gold_span_start_end = list(gold_map.keys())
        pred_span_start_end = [(s.start, s.end) for s in pred]
        for pspan in pred:
            if (pspan.start, pspan.end) in gold_span_start_end:
                if pspan.label == gold_map[(pspan.start, pspan.end)].label:
                    micro_prf.tp += 1
                else:
                    micro_prf.fp  += 1
            else:
                micro_prf.fp += 1
        for gspan in gold:
            if (gspan.start, gspan.end) not in pred_span_start_end:
                micro_prf.fn += 1            
    return {
        "ner_micro_p": micro_prf.precision,
        "ner_micro_r": micro_prf.recall,
        "ner_micro_f": micro_prf.fscore,
    }

def _score_and_format_ner(examples):
    r = score_ner(examples)
    results_ner = {k: "{:.2f}".format(v * 100) for k, v in r.items()}
    print(f"\t {results_ner}")

def _score_and_format_relations(examples, thresholds):
    for threshold in thresholds:
        r = score_relations(examples, threshold)
        results_rel = {k: "{:.2f}".format(v * 100) for k, v in r.items()}
        print(f"threshold {'{:.2f}'.format(threshold)} \t {results_rel}")


if __name__ == "__main__":
    typer.run(main)