"""Input/output utility functions for UCCA scripts."""
import sys
import time
from collections import defaultdict
from itertools import filterfalse, chain

import os
from contextlib import contextmanager
from glob import glob
from tqdm import tqdm
from xml.etree.ElementTree import ParseError

from ucca.convert import file2passage, passage2file, from_text, to_text, split2segments
from ucca.core import Passage

DEFAULT_LANG = "en"
DEFAULT_ATTEMPTS = 3
DEFAULT_DELAY = 5


class LazyLoadedPassages:
    """
    Iterable interface to Passage objects that loads files on-the-go and can be iterated more than once
    """
    def __init__(self, files, sentences=False, paragraphs=False, converters=None, lang=DEFAULT_LANG,
                 attempts=DEFAULT_ATTEMPTS, delay=DEFAULT_DELAY):
        self.files = files
        self.sentences = sentences
        self.paragraphs = paragraphs
        self.split = self.sentences or self.paragraphs
        self.converters = defaultdict(lambda: from_text) if converters is None else converters
        self.lang = lang
        self.attempts = attempts
        self.delay = delay
        self._files_iter = None
        self._split_iter = None
        self._file_handle = None

    def __iter__(self):
        self._files_iter = iter(self.files)
        self._split_iter = None
        self._file_handle = None
        return self

    def __next__(self):
        while True:
            passage = self._next_passage()
            if passage is not None:
                return passage

    def _next_passage(self):
        passage = None
        if self._split_iter is None:
            try:
                file = next(self._files_iter)
            except StopIteration:  # Finished iteration
                raise
            if isinstance(file, Passage):  # Not really a file, but a Passage
                passage = file
            else:  # A file
                attempts = self.attempts
                while not os.path.exists(file):
                    with external_write_mode(file=sys.stderr):
                        if attempts == 0:
                            print("File not found: %s" % file, file=sys.stderr)
                            return None
                        print("Failed reading %s, trying %d more times..." % (file, attempts), file=sys.stderr)
                    time.sleep(self.delay)
                    attempts -= 1
                try:
                    passage = file2passage(file)  # XML or binary format
                except (IOError, ParseError) as e:  # Failed to read as passage file
                    base, ext = os.path.splitext(os.path.basename(file))
                    converter = self.converters.get(ext.lstrip("."))
                    if converter is None:
                        raise IOError("Could not read %s file. Try adding '.txt' suffix: '%s'" % (ext, file)) from e
                    self._file_handle = open(file, encoding="utf-8")
                    self._split_iter = iter(converter(chain(self._file_handle, [""]), passage_id=base, lang=self.lang))
            if self.split:
                if self._split_iter is None:
                    self._split_iter = (passage,)
                self._split_iter = iter(s for p in self._split_iter for s in
                                        split2segments(p, is_sentences=self.sentences, lang=self.lang))
        if self._split_iter is not None:  # Either set before or initialized now
            try:
                passage = next(self._split_iter)
            except StopIteration:  # Finished this converter
                self._split_iter = None
                if self._file_handle is not None:
                    self._file_handle.close()
                    self._file_handle = None
                return None
        return passage

    # The following three methods are implemented to support shuffle;
    # note files are shuffled but there is no shuffling within files, as it would not be efficient.
    # Note also the inconsistency because these access the files while __iter__ accesses individual passages.
    def __len__(self):
        return len(self.files)

    def __getitem__(self, i):
        return self.files[i]

    def __setitem__(self, i, value):
        self.files[i] = value

    def __bool__(self):
        return bool(self.files)


def resolve_patterns(filename_patterns):
    for pattern in [filename_patterns] if isinstance(filename_patterns, str) else filename_patterns:
        yield from sorted(glob(pattern)) or [pattern]


def get_passages_with_progress_bar(filename_patterns, desc=None, **kwargs):
    filenames = list(resolve_patterns(filename_patterns))
    t = tqdm(read_files_and_dirs(filenames, **kwargs), desc=desc, unit=" passages", total=len(filenames))
    for passage in t:
        t.set_postfix(ID=passage.ID)
        yield passage


def get_passages(filename_patterns, **kwargs):
    for filenames in resolve_patterns(filename_patterns):
        yield from read_files_and_dirs(filenames, **kwargs)


def gen_files(files_and_dirs):
    """
    :param files_and_dirs: iterable of files and/or directories to look in
    :return: all files given, plus any files directly under any directory given
    """
    for file_or_dir in [files_and_dirs] if isinstance(files_and_dirs, str) else files_and_dirs:
        if os.path.isdir(file_or_dir):
            yield from filterfalse(os.path.isdir, (os.path.join(file_or_dir, f)
                                                   for f in sorted(os.listdir(file_or_dir))))
        else:
            yield file_or_dir


def read_files_and_dirs(files_and_dirs, sentences=False, paragraphs=False, converters=None, lang=DEFAULT_LANG,
                        attempts=DEFAULT_ATTEMPTS, delay=DEFAULT_DELAY):
    """
    :param files_and_dirs: iterable of files and/or directories to look in
    :param sentences: whether to split to sentences
    :param paragraphs: whether to split to paragraphs
    :param converters: dict of input format converters to use based on the file extension
    :param lang: language to use for tokenization model
    :param attempts: number of times to try reading a file before giving up
    :param delay: number of seconds to wait before subsequent attempts to read a file
    :return: lazy-loaded passages from all files given, plus any files directly under any directory given
    """
    return LazyLoadedPassages(list(gen_files(files_and_dirs)), sentences=sentences, paragraphs=paragraphs,
                              converters=converters, lang=lang, attempts=attempts, delay=delay)


def write_passage(passage, output_format=None, binary=False, outdir=".", prefix="", converter=None, verbose=True,
                  append=False, basename=None):
    """
    Write a given UCCA passage in any format.
    :param passage: Passage object to write
    :param output_format: filename suffix (if given "ucca", suffix will be ".pickle" or ".xml" depending on `binary')
    :param binary: save in pickle format with ".pickle" suffix
    :param outdir: output directory, should exist already
    :param prefix: string to prepend to output filename
    :param converter: function to apply to passage before saving (if output_format is not "ucca"/"pickle"/"xml"),
                      returning iterable of strings, each corresponding to an output line
    :param verbose: print "Writing passage" message
    :param append: if using converter, append to output file rather than creating a new file
    :param basename: use this instead of `passage.ID' for the output filename
    :return: path of created output file
    """
    os.makedirs(outdir, exist_ok=True)
    suffix = output_format if output_format and output_format != "ucca" else ("pickle" if binary else "xml")
    outfile = os.path.join(outdir, prefix + (basename or passage.ID) + "." + suffix)
    if verbose:
        with external_write_mode():
            print("%s '%s'..." % ("Appending to" if append else "Writing passage", outfile))
    if output_format is None or output_format in ("ucca", "pickle", "xml"):
        passage2file(passage, outfile, binary=binary)
    else:
        with open(outfile, "a" if append else "w", encoding="utf-8") as f:
            f.writelines(map("{}\n".format, (converter or to_text)(passage)))
    return outfile


@contextmanager
def external_write_mode(*args, **kwargs):
    try:
        with tqdm.external_write_mode(*args, **kwargs):
            yield
    except AttributeError:
        yield
