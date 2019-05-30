"""Utility functions for UCCA package."""
import os
import sys
import time
from collections import OrderedDict
from collections import deque
from contextlib import contextmanager
from enum import Enum
from itertools import groupby, islice
from operator import attrgetter, itemgetter

import numpy as np
from tqdm import tqdm

from ucca import layer0, layer1

MODEL_ENV_VAR = "SPACY_MODEL"  # Determines the default spaCy model to load
DEFAULT_MODEL = {"en": "en_core_web_md", "fr": "fr_core_news_md", "de": "de_core_news_md"}

N_THREADS = 4
BATCH_SIZE = 50


class Attr(Enum):
    """Wrapper for spaCy Attr, determining order for saving in layer0.extra per token when as_array=True"""
    ORTH = 0
    LEMMA = 1
    TAG = 2
    POS = 3
    ENT_TYPE = 4
    ENT_IOB = 5
    DEP = 6
    HEAD = 7
    SHAPE = 8
    PREFIX = 9
    SUFFIX = 10

    def __call__(self, value, vocab=None, as_array=False, lang=None):
        """Resolve numeric ID of attribute value to string (if as_array=False) or to int (if as_array=True)"""
        if value is None:
            return None
        if self in (Attr.ENT_IOB, Attr.HEAD):
            return int(np.int64(value))
        if as_array:
            is_str = isinstance(value, str)
            if is_str or self in (Attr.ORTH, Attr.LEMMA):
                try:  # Will find the value even if it's a new string, but that's OK since the hash is deterministic
                    i = get_vocab(vocab, lang).strings[value]
                    if is_str:  # Replace with numeric ID since as_array=True
                        value = i
                except KeyError:
                    value = None
            return value if value is None or isinstance(value, str) else int(value)
        try:
            return get_vocab(vocab, lang)[value].text
        except KeyError:
            return None
    
    @property
    def key(self):
        """String used in `extra' dict of Terminals to store this attribute when as_array=False"""
        return self.name.lower()


def get_nlp(lang="en"):
    """Load spaCy model for a given language, determined by `models' dict or by MODEL_ENV_VAR"""
    instance = nlp.get(lang)
    if instance is None:
        import spacy
        model = models.get(lang)
        if not model:
            models[lang] = model = os.environ.get("_".join((MODEL_ENV_VAR, lang.upper()))) or \
                                   os.environ.get(MODEL_ENV_VAR) or DEFAULT_MODEL.get(lang, "xx")
        started = time.time()
        with external_write_mode():
            print("Loading spaCy model '%s'... " % model, end="", flush=True)
            try:
                nlp[lang] = instance = spacy.load(model)
            except OSError:
                spacy.cli.download(model)
                try:
                    nlp[lang] = instance = spacy.load(model)
                except OSError as e:
                    raise OSError("Failed to get spaCy model. Download it manually using "
                                  "`python -m spacy download %s`." % model) from e
            tokenizer[lang] = instance.tokenizer
            instance.tokenizer = lambda words: spacy.tokens.Doc(instance.vocab, words=words)
            print("Done (%.3fs)." % (time.time() - started))
    return instance


models = {}  # maps language two-letter code to name of spaCy model
nlp = {}  # maps language two-letter code to actual loaded spaCy model
tokenizer = {}  # maps language two-letter code to tokenizer of spaCy model


def get_tokenizer(tokenized=False, lang="en"):
    instance = get_nlp(lang)
    return instance.tokenizer if tokenized else tokenizer[lang]


def get_vocab(vocab=None, lang=None):
    if vocab is not None:
        return vocab
    return (get_nlp(lang) if lang else get_nlp()).vocab


def get_word_vectors(dim=None, size=None, filename=None, vocab=None):
    """
    Get word vectors from spaCy model or from text file
    :param dim: dimension to trim vectors to (default: keep original)
    :param size: maximum number of vectors to load (default: all)
    :param filename: text file to load vectors from (default: from spaCy model)
    :param vocab: instead of strings, look up keys of returned dict in vocab (use lang str, e.g. "en", for spaCy vocab)
    :return: tuple of (dict of word [string or integer] -> vector [NumPy array], dimension)
    """
    orig_keys = vocab is None
    if isinstance(vocab, str) or not filename:
        vocab = get_nlp(vocab if isinstance(vocab, str) else "en").vocab

    def _lookup(word):
        try:
            return word.orth_ if orig_keys else word.orth
        except AttributeError:
            if orig_keys:
                return word
        lex = vocab[word]
        return getattr(lex, "orth", lex)

    if filename:
        it = read_word_vectors(dim, size, filename)
        nr_row, nr_dim = next(it)
        vectors = OrderedDict(islice(tqdm(((_lookup(w), v) for w, v in it if orig_keys or w in vocab),
                                          desc="Loading '%s'" % filename, postfix=dict(dim=nr_dim),
                                          file=sys.stdout, total=nr_row, unit=" vectors"), nr_row))
    else:  # return spaCy vectors
        nr_row, nr_dim = vocab.vectors.shape
        if dim is not None and dim < nr_dim:
            nr_dim = int(dim)
            vocab.vectors.resize(shape=(int(size or nr_row), nr_dim))
        lexemes = sorted([l for l in vocab if l.has_vector], key=attrgetter("prob"), reverse=True)[:size]
        vectors = OrderedDict((_lookup(l), l.vector) for l in lexemes)
    return vectors, nr_dim


def read_word_vectors(dim, size, filename):
    """
    Read word vectors from text file, with an optional first row indicating size and dimension
    :param dim: dimension to trim vectors to
    :param size: maximum number of vectors to load
    :param filename: text file to load vectors from
    :return: generator: first element is (#vectors, #dims); and all the rest are (word [string], vector [NumPy array])
    """
    try:
        first_line = True
        nr_row = nr_dim = None
        with open(filename, encoding="utf-8") as f:
            for line in f:
                fields = line.split()
                if first_line:
                    first_line = False
                    try:
                        nr_row, nr_dim = map(int, fields)
                        is_header = True
                    except ValueError:
                        nr_dim = len(fields) - 1  # No header, just get vector length from first one
                        is_header = False
                    if dim and dim < nr_dim:
                        nr_dim = dim
                    yield size or nr_row, nr_dim
                    if is_header:
                        continue  # Read next line
                word, *vector = fields
                if len(vector) >= nr_dim:  # May not be equal if word is whitespace
                    yield word, np.asarray(vector[-nr_dim:], dtype="f")
    except OSError as e:
        raise IOError("Failed loading word vectors from '%s'" % filename) from e


def annotate(passage, *args, **kwargs):
    """
    Run spaCy pipeline on the given passage, unless already annotated
    :param passage: Passage object, whose layer 0 nodes will be added entries in the `extra' dict
    """
    list(annotate_all([passage], *args, **kwargs))


def annotate_as_tuples(passages, replace=False, as_array=False, lang="en", vocab=None, verbose=False):
    for passage_lang, passages_by_lang in groupby(passages, get_lang):
        for need_annotation, stream in groupby(to_annotate(passages_by_lang, replace, as_array), lambda x: bool(x[0])):
            annotated = get_nlp(passage_lang or lang).pipe(
                stream, as_tuples=True, n_threads=N_THREADS, batch_size=BATCH_SIZE) if need_annotation else stream
            annotated = set_docs(annotated, as_array, passage_lang or lang, vocab, replace, verbose)
            for passage, passages in groupby(annotated, itemgetter(0)):
                yield deque(passages, maxlen=1).pop()  # Wait until all paragraphs have been annotated


def annotate_all(passages, replace=False, as_array=False, as_tuples=False, lang="en", vocab=None, verbose=False):
    """
    Run spaCy pipeline on the given passages, unless already annotated
    :param passages: iterable of Passage objects, whose layer 0 nodes will be added entries in the `extra' dict
    :param replace: even if a given passage is already annotated, replace with new annotation
    :param as_array: instead of adding `extra' entries to each terminal, set layer 0 extra["doc"] to array of ids
    :param as_tuples: treat input as tuples of (passage text, context), and return context for each passage as-is
    :param lang: optional two-letter language code, will be overridden if passage has "lang" attrib
    :param vocab: optional dictionary of vocabulary IDs to string values, to avoid loading spaCy model
    :param verbose: whether to print annotated text
    :return: generator of annotated passages, which are actually modified in-place (same objects as input)
    """
    if not as_tuples:
        passages = ((p,) for p in passages)
    for t in annotate_as_tuples(passages, replace=replace, as_array=as_array, lang=lang, vocab=vocab, verbose=verbose):
        yield t if as_tuples else t[0]


def get_lang(passage_context):
    return passage_context[0].attrib.get("lang")


def to_annotate(passage_contexts, replace, as_array):
    """Filter passages to get only those that require annotation; split to paragraphs and return generator of
    (list of tokens, (paragraph index, list of Terminals, Passage) + original context appended) tuples"""
    return (([t.text for t in terminals] if replace or not is_annotated(passage, as_array) else (),
             (i, terminals, passage) + tuple(context)) for passage, *context in passage_contexts
            for i, terminals in enumerate(break2paragraphs(passage, return_terminals=True)))


def is_annotated(passage, as_array):
    """Whether the passage is already annotated or only partially annotated"""
    l0 = passage.layer(layer0.LAYER_ID)
    if as_array:
        docs = l0.extra.get("doc")
        return not l0.all or docs is not None and len(docs) == max(t.paragraph for t in l0.all) and \
            sum(map(len, docs)) == len(l0.all) and \
            all(i is None or isinstance(i, int) for l in docs for t in l for i in t)
    return all(a.key in t.extra for t in l0.all for a in Attr)


def set_docs(annotated, as_array, lang, vocab, replace, verbose):
    """Given spaCy annotations, set values in layer0.extra per paragraph if as_array=True, or else in Terminal.extra"""
    for doc, (i, terminals, passage, *context) in annotated:
        if doc:  # Not empty, so copy values
            from spacy import attrs
            arr = doc.to_array([getattr(attrs, a.name) for a in Attr])
            if as_array:
                docs = passage.layer(layer0.LAYER_ID).docs(i + 1)
                existing = docs[i] + (len(arr) - len(docs[i])) * [len(Attr) * [None]]
                docs[i] = [[a(v if e is None or replace else e, get_vocab(vocab, lang), as_array=True)
                            for a, v, e in zip(Attr, values, es)] for values, es in zip(arr, existing)]
            else:
                for terminal, values in zip(terminals, arr):
                    for attr, value in zip(Attr, values):
                        if replace or not terminal.extra.get(attr.key):
                            terminal.extra[attr.key] = attr(value, get_vocab(vocab, lang))
        if verbose:
            data = [[a.key for a in Attr]] + \
                   [[str(a(t.tok[a.value], get_vocab(vocab, lang)) if as_array else t.extra[a.key])
                     for a in Attr] for j, t in enumerate(terminals)]
            width = [max(len(f) for f in t) for t in data]
            for j in range(len(Attr)):
                try:
                    print(" ".join("%-*s" % (w, f[j]) for f, w in zip(data, width)))
                except UnicodeEncodeError:
                    pass
            print()
        yield (passage,) + tuple(context)


SENTENCE_END_MARKS = ('.', '?', '!')


def break2sentences(passage, lang="en", *args, **kwargs):
    """
    Breaks paragraphs into sentences according to the annotation.

    A sentence is a list of terminals which ends with a mark from
    SENTENCE_END_MARKS, and is also the end of a paragraph or parallel scene.
    :param passage: the Passage object to operate on
    :param lang: optional two-letter language code
    :return: a list of positions in the Passage, each denotes a closing Terminal of a sentence.
    """
    del args, kwargs
    l1 = passage.layer(layer1.LAYER_ID)
    terminals = extract_terminals(passage)
    if not terminals:
        return []
    if any(n.outgoing for n in l1.all):  # Passage is labeled
        ps_ends = [ps.end_position for ps in l1.top_scenes]
        ps_starts = [ps.start_position for ps in l1.top_scenes]
        marks = [t.position for t in terminals if t.text in SENTENCE_END_MARKS]
        # Annotations doesn't always include the ending period (or other mark)
        # with the parallel scene it closes. Hence, if the terminal before the
        # mark closed the parallel scene, and this mark doesn't open a scene
        # in any way (hence it probably just "hangs" there), it's a sentence end
        marks = [x for x in marks if x in ps_ends or ((x - 1) in ps_ends and x not in ps_starts)]
    else:  # Not labeled, split using spaCy
        annotated = get_nlp(lang=lang)([t.text for t in terminals])
        marks = [span.end for span in annotated.sents]
    marks = sorted(set(marks + break2paragraphs(passage)))
    # Avoid punctuation-only sentences
    if len(marks) > 1:
        marks = [x for x, y in zip(marks[:-1], marks[1:]) if not all(layer0.is_punct(t) for t in terminals[x:y])] + \
                [marks[-1]]
    return marks


def extract_terminals(p):
    """returns an iterator of the terminals of the passage p"""
    return p.layer(layer0.LAYER_ID).all


def break2paragraphs(passage, return_terminals=False, *args, **kwargs):
    """
    Breaks into paragraphs according to the annotation.

    Uses the `paragraph' attribute of layer 0 to find paragraphs.
    :param passage: the Passage object to operate on
    :param return_terminals: whether to return actual Terminal objects of all terminals rather than just end positions
    :return: a list of positions in the Passage, each denotes a closing Terminal of a paragraph.
    """
    del args, kwargs
    terminals = list(extract_terminals(passage))
    if not terminals:
        return []
    return [list(p) for _, p in groupby(terminals, key=attrgetter("paragraph"))] if return_terminals else \
        [t.position - 1 for t in terminals if t.position > 1 and t.para_pos == 1] + [terminals[-1].position]


def indent_xml(xml_as_string):
    """
    Indents a string of XML-like objects.

    This works only for units with no text or tail members, and only for
    strings whose leaves are written as <tag /> and not <tag></tag>.
    :param xml_as_string: XML string to indent
    :return: indented XML string
    """
    tabs = 0
    lines = str(xml_as_string).replace('><', '>\n<').splitlines()
    s = ''
    for line in lines:
        if line.startswith('</'):
            tabs -= 1
        s += ("  " * tabs) + line + '\n'
        if not (line.endswith('/>') or line.startswith('</')):
            tabs += 1
    return s


@contextmanager
def external_write_mode(*args, **kwargs):
    try:
        with tqdm.external_write_mode(*args, **kwargs):
            yield
    except AttributeError:
        yield
