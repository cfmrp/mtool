"""Converter module between different UCCA annotation formats.

This module contains utilities to convert between UCCA annotation in different
forms, to/from the :class:`core`.Passage form, acts as a pivot for all
conversions.

The possible other formats are:
    site XML
    standard XML
    conll (CoNLL-X dependency parsing shared task)
    sdp (SemEval 2015 semantic dependency parsing shared task)
"""

import os
import pickle
import re
import sys
import xml.etree.ElementTree as ET
import xml.sax.saxutils
from collections import defaultdict
from itertools import repeat, groupby
from operator import attrgetter, itemgetter

from ucca import textutil, core, layer0, layer1
from ucca.layer1 import EdgeTags
from ucca.normalization import attach_punct, COORDINATED_MAIN_REL

try:
    # noinspection PyPackageRequirements
    import simplejson as json
    from simplejson.scanner import JSONDecodeError
except ImportError:
    import json
    from json.decoder import JSONDecodeError


class SiteXMLUnknownElement(core.UCCAError):
    pass


class SiteCfg:
    """Contains static configuration for conversion to/from the site XML."""

    """
    XML Elements' tags in the site XML format of different annotation
    components - FNodes (Unit), Terminals, remote and implicit Units
    and linkages.
    """
    class _Tags:
        Unit = 'unit'
        Terminal = 'word'
        Remote = 'remoteUnit'
        Implicit = 'implicitUnit'
        Linkage = 'linkage'

    class _Paths:
        """Paths (from the XML root) to different parts of the annotation -
        the main units part, the discontiguous units, the paragraph
        elements and the annotation units.
        """
        Main = 'units'
        Attrib = 'attrib'
        Paragraphs = 'units/unit/*'
        Annotation = 'units/unit/*/*'
        Discontiguous = 'unitGroups'

    class _Types:
        """Possible types for the Type attribute, which is roughly equivalent
        to Edge/Node tag. Only specially-handled types are here, which is
        the punctuation type.
        """
        Punct = 'Punctuation'

    class _Attr:
        """Attribute names in the XML elements (not all exist in all elements)
        - passage and site ID, discontiguous unit ID, UCCA tag, uncertain
        flag, user remarks and linkage arguments. NodeID is special
        because we set it for every unit that was already converted, and
        it's not present in the original XML.
        """
        PassageID = 'passageID'
        SiteID = 'id'
        NodeID = 'internal_id'
        ElemTag = 'type'
        Uncertain = 'uncertain'
        Unanalyzable = 'unanalyzable'
        Remarks = 'remarks'
        GroupID = 'unitGroupID'
        LinkageArgs = 'args'
        Suggestion = 'suggestion'
        CoordinatedMainRel = 'cmr'

    __init__ = None
    Tags = _Tags
    Paths = _Paths
    Types = _Types
    Attr = _Attr

    """ XML tag used for wrapping words (non-punctuation) and unit groups """
    TBD = 'To Be Defined'

    """ values for True/False in the site XML (strings) """
    TRUE = 'true'
    FALSE = 'false'

    """ version of site XML scheme which self adheres to """
    SchemeVersion = '1.0.4'
    """ mapping of site XML tag attribute to layer1 edge tags. """
    TagConversion = {'Linked U': EdgeTags.ParallelScene,
                     'Parallel Scene': EdgeTags.ParallelScene,
                     'Function': EdgeTags.Function,
                     'Participant': EdgeTags.Participant,
                     'Process': EdgeTags.Process,
                     'State': EdgeTags.State,
                     'aDverbial': EdgeTags.Adverbial,
                     'Center': EdgeTags.Center,
                     'Elaborator': EdgeTags.Elaborator,
                     'Linker': EdgeTags.Linker,
                     'Ground': EdgeTags.Ground,
                     'Connector': EdgeTags.Connector,
                     'Role Marker': EdgeTags.Relator,
                     'Relator': EdgeTags.Relator,
                     'Time': EdgeTags.Time,
                     'Quantifier': EdgeTags.Quantifier,
                     }

    """ mapping of layer1.EdgeTags to site XML tag attributes. """
    EdgeConversion = {EdgeTags.ParallelScene: 'Parallel Scene',
                      EdgeTags.Function: 'Function',
                      EdgeTags.Participant: 'Participant',
                      EdgeTags.Process: 'Process',
                      EdgeTags.State: 'State',
                      EdgeTags.Adverbial: 'aDverbial',
                      EdgeTags.Center: 'Center',
                      EdgeTags.Elaborator: 'Elaborator',
                      EdgeTags.Linker: 'Linker',
                      EdgeTags.Ground: 'Ground',
                      EdgeTags.Connector: 'Connector',
                      EdgeTags.Relator: 'Relator',
                      EdgeTags.Time: 'Time',
                      EdgeTags.Quantifier: 'Quantifier',
                      }


class SiteUtil:
    """Contains utility functions for converting to/from the site XML.

    Functions:
        unescape: converts escaped characters to their original form.
        set_id: sets the Node ID (internal) attribute in the XML element.
        get_node: gets the node corresponding to the element given from
            the mapping. If not found, returns None
        set_node: writes the element site ID + node pair to the mapping

    """
    __init__ = None

    @staticmethod
    def unescape(x):
        return xml.sax.saxutils.unescape(x, {'&quot;': '"', r"\u2019": "'"})

    @staticmethod
    def set_id(e, i):
        e.set(SiteCfg.Attr.NodeID, i)

    @staticmethod
    def get_node(e, mapp):
        return mapp.get(e.get(SiteCfg.Attr.SiteID))

    @staticmethod
    def set_node(e, n, mapp):
        mapp.update({e.get(SiteCfg.Attr.SiteID): n})


def _from_site_terminals(elem, passage, elem2node):
    """Extract the Terminals from the site XML format.

    Some of the terminals metadata (remarks, type) is saved in a wrapper unit
    which encapsulates each terminal, so we use both for creating our
    :class:`layer0`.Terminal objects.

    :param elem: root element of the XML hierarchy
    :param passage: passage to add the Terminals to, already with Layer0 object
    :param elem2node: dictionary whose keys are site IDs and values are the
            created UCCA Nodes which are equivalent. This function updates the
            dictionary by mapping each word wrapper to a UCCA Terminal.
    """
    layer0.Layer0(passage)
    for para_num, paragraph in enumerate(elem.iterfind(
            SiteCfg.Paths.Paragraphs)):
        words = list(paragraph.iter(SiteCfg.Tags.Terminal))
        wrappers = []
        for word in words:
            # the list added has only one element, because XML is hierarchical
            wrappers += [x for x in paragraph.iter(SiteCfg.Tags.Unit)
                         if word in list(x)]
        for word, wrapper in zip(words, wrappers):
            punct = (wrapper.get(SiteCfg.Attr.ElemTag) == SiteCfg.Types.Punct)
            text = SiteUtil.unescape(word.text)
            # Paragraphs start at 1 and enumeration at 0, so add +1 to para_num
            t = passage.layer(layer0.LAYER_ID).add_terminal(text, punct,
                                                            para_num + 1)
            SiteUtil.set_id(word, t.ID)
            SiteUtil.set_node(wrapper, t, elem2node)


def _parse_site_units(elem, parent, passage, groups, elem2node):
    """Parses the given element in the site annotation.

    The parser works recursively by determining how to parse the current XML
    element, then adding it with a core.Edge object to the parent given.
    After creating (or retrieving) the current node, which corresponds to the
    XML element given, we iterate its subelements and parse them recursively.

    :param elem: the XML element to parse
    :param parent: layer1.FoundationalNode parent of the current XML element
    :param passage: the core.Passage we are converting to
    :param groups: the main XML element of the discontiguous units (unitGroups)
    :param elem2node: mapping between site IDs and Nodes, updated here

    :return: a list of (parent, elem) pairs which weren't process, as they should
        be process last (usually because they contain references to not-yet
        created Nodes).
    """

    def _get_node(node_elem):
        """Given an XML element, returns its node if it was already created.

        If not created, returns None. If the element is a part of discontiguous
        unit, returns the discontiguous unit corresponding Node (if exists).

        """
        gid = node_elem.get(SiteCfg.Attr.GroupID)
        return SiteUtil.get_node(node_elem, elem2node) if gid is None else elem2node.get(gid)

    def _get_work_elem(node_elem):
        """Given XML element, return either itself or its discontiguous unit."""
        gid = node_elem.get(SiteCfg.Attr.GroupID)
        return (node_elem if gid is None
                else [group_elem for group_elem in groups
                      if group_elem.get(SiteCfg.Attr.SiteID) == gid][0])

    def _fill_attributes(node_elem, target_node):
        """Fills in node the remarks and uncertain attributes from XML elem."""
        if node_elem.get(SiteCfg.Attr.Uncertain) == 'true':
            target_node.attrib['uncertain'] = True
        if node_elem.get(SiteCfg.Attr.Remarks) is not None:
            target_node.extra['remarks'] = SiteUtil.unescape(
                node_elem.get(SiteCfg.Attr.Remarks))

    l1 = passage.layer(layer1.LAYER_ID)
    tbd = []

    # Unit tag means its a regular, hierarchically built unit
    if elem.tag == SiteCfg.Tags.Unit:
        node = _get_node(elem)

        # Only nodes created by now are the terminals, or discontiguous units
        if node is not None:

            if node.tag == layer0.NodeTags.Word:
                parent.add(EdgeTags.Terminal, node)
            elif node.tag == layer0.NodeTags.Punct:
                SiteUtil.set_node(elem, l1.add_punct(
                    parent, node), elem2node)
            else:
                # if we got here, we are the second (or later) chunk of a
                # discontiguous unit, whose node was already created.
                # So, we don't need to create the node, just keep processing
                # our subelements (as subelements of the discontiguous unit)

                # Added by Omri to address cases where remote units direct at the chunks of discontiguous units
                SiteUtil.set_node(elem, node, elem2node)

                for subelem in elem:
                    tbd += _parse_site_units(subelem, node, passage,
                                             groups, elem2node)
        else:
            # Creating a new node, either regular or discontiguous.
            # Note that for discontiguous units we have a different work_elem,
            # because all the data on them are stored outside the hierarchy
            work_elem = _get_work_elem(elem)
            edge_tags = [(SiteCfg.TagConversion[tag],)
                         for tag in work_elem.get(SiteCfg.Attr.ElemTag, "").split("|") or None]
            attrib = {}
            if work_elem.get(SiteCfg.Attr.CoordinatedMainRel) == SiteCfg.TRUE:
                attrib[COORDINATED_MAIN_REL] = True
            node = l1.add_fnode_multiple(parent, edge_tags, edge_attrib=attrib)
            SiteUtil.set_node(work_elem, node, elem2node)

            # Added by Omri to address cases where remote units direct at the chunks of discontiguous units
            SiteUtil.set_node(elem, node, elem2node)

            _fill_attributes(work_elem, node)
            # For iterating the subelements, we don't use work_elem, as it may
            # out of the current XML hierarchy we are processing (discont...)
            for parent_elem in [elem] if elem is work_elem else [elem, work_elem]:
                for subelem in parent_elem:
                    tbd += _parse_site_units(subelem, node, passage,
                                             groups, elem2node)
    # Implicit units have their own tag, and aren't recursive, but nonetheless
    # are treated the same as regular units
    elif elem.tag == SiteCfg.Tags.Implicit:
        edge_tags = [(SiteCfg.TagConversion[tag],)
                     for tag in elem.get(SiteCfg.Attr.ElemTag, "").split("|") or None]
        node = l1.add_fnode_multiple(parent, edge_tags, implicit=True)
        SiteUtil.set_node(elem, node, elem2node)
        _fill_attributes(elem, node)
    # non-unit, probably remote or linkage, which should be created in the end
    else:
        tbd.append((parent, elem))

    return tbd


def _from_site_annotation(elem, passage, elem2node):
    """Parses site XML annotation.

    Parses the whole annotation, given that the terminals are already processed
    and converted and appear in elem2node.

    :param elem: root XML element
    :param passage: the passage to create, with layer0, w/o layer1
    :param elem2node: mapping from site ID to Nodes, should contain the Terminals

    :raise SiteXMLUnknownElement: if an unknown, unhandled element is found

    """
    tbd = []
    l1 = layer1.Layer1(passage)
    l1head = l1.heads[0]
    groups_root = elem.find(SiteCfg.Paths.Discontiguous)

    # this takes care of the hierarchical annotation
    for subelem in elem.iterfind(SiteCfg.Paths.Annotation):
        tbd += _parse_site_units(subelem, l1head, passage, groups_root,
                                 elem2node)

    # Handling remotes and linkages, which usually contain IDs from all over
    # the annotation, hence must be taken care of after all elements are
    # converted
    for parent, elem in tbd:
        if elem.tag == SiteCfg.Tags.Remote:
            edge_tags = [(SiteCfg.TagConversion[tag],)
                         for tag in elem.get(SiteCfg.Attr.ElemTag, "").split("|") or None]
            child = SiteUtil.get_node(elem, elem2node)
            if child is None:  # bug in XML, points to an invalid ID
                print("Warning: remoteUnit with ID {} is invalid - skipping".
                      format(elem.get(SiteCfg.Attr.SiteID)), file=sys.stderr)
                continue
            l1.add_remote_multiple(parent, edge_tags, child)
        elif elem.tag == SiteCfg.Tags.Linkage:
            args = [elem2node[x] for x in
                    elem.get(SiteCfg.Attr.LinkageArgs).split(',')]
            l1.add_linkage(parent, *args)
        else:
            raise SiteXMLUnknownElement(elem.tag)


def from_site(elem):
    """Converts site XML structure to :class:`core`.Passage object.

    :param elem: root element of the XML structure

    :return: The converted core.Passage object
    """
    pid = elem.find(SiteCfg.Paths.Main).get(SiteCfg.Attr.PassageID)
    attrib = elem.find(SiteCfg.Paths.Attrib)
    passage = core.Passage(pid, attrib=None if attrib is None else attrib.attrib)
    elem2node = {}
    _from_site_terminals(elem, passage, elem2node)
    _from_site_annotation(elem, passage, elem2node)
    return passage


def to_site(passage):
    """Converts a passage to the site XML format.

    :param passage: the passage to convert

    :return: the root element of the standard XML structure
    """

    class _State:
        def __init__(self):
            self.ID = 1
            self.mapping = {}
            self.elems = {}

        def get_id(self):
            ret = str(self.ID)
            self.ID += 1
            return ret

        def update(self, node_elem, node):
            self.mapping[node.ID] = node_elem.get(SiteCfg.Attr.SiteID)
            self.elems[node.ID] = node_elem

    state = _State()

    def _word(terminal):
        tag = SiteCfg.Types.Punct if terminal.punct else SiteCfg.TBD
        word = ET.Element(SiteCfg.Tags.Terminal,
                          {SiteCfg.Attr.SiteID: state.get_id()})
        word.text = terminal.text
        word_elem = ET.Element(SiteCfg.Tags.Unit,
                               {SiteCfg.Attr.ElemTag: tag,
                                SiteCfg.Attr.SiteID: state.get_id(),
                                SiteCfg.Attr.Unanalyzable: SiteCfg.FALSE,
                                SiteCfg.Attr.Uncertain: SiteCfg.FALSE})
        word_elem.append(word)
        state.update(word_elem, terminal)
        return word_elem

    def _cunit(node, cunit_subelem):
        uncertain = (SiteCfg.TRUE if node.attrib.get('uncertain')
                     else SiteCfg.FALSE)
        suggestion = (SiteCfg.TRUE if node.attrib.get('suggest')
                      else SiteCfg.FALSE)
        unanalyzable = (
            SiteCfg.TRUE if len(node) > 1 and all(
                e.tag in (EdgeTags.Terminal,
                          EdgeTags.Punctuation)
                for e in node)
            else SiteCfg.FALSE)
        elem_tag = "|".join(SiteCfg.EdgeConversion[tag] for tag in node.ftags)
        attrib = {SiteCfg.Attr.ElemTag: elem_tag,
                  SiteCfg.Attr.SiteID: state.get_id(),
                  SiteCfg.Attr.Unanalyzable: unanalyzable,
                  SiteCfg.Attr.Uncertain: uncertain,
                  SiteCfg.Attr.Suggestion: suggestion}
        remarks = node.attrib.get("remarks")
        if remarks:
            attrib[SiteCfg.Attr.Remarks] = remarks
        if any(edge.attrib.get(COORDINATED_MAIN_REL) for edge in node.incoming):
            attrib[SiteCfg.Attr.CoordinatedMainRel] = SiteCfg.TRUE
        cunit_elem = ET.Element(SiteCfg.Tags.Unit, attrib)
        if cunit_subelem is not None:
            cunit_elem.append(cunit_subelem)
        # When we add chunks of discontiguous units, we don't want them to
        # overwrite the original mapping (leave it to the unitGroupId)
        if node.ID not in state.mapping:
            state.update(cunit_elem, node)
        return cunit_elem

    def _remote(edge):
        uncertain = (SiteCfg.TRUE if edge.child.attrib.get('uncertain')
                     else SiteCfg.FALSE)
        suggestion = (SiteCfg.TRUE if edge.child.attrib.get('suggest')
                      else SiteCfg.FALSE)
        remote_elem = ET.Element(SiteCfg.Tags.Remote,
                                 {SiteCfg.Attr.ElemTag:
                                  "|".join(SiteCfg.EdgeConversion[tag] for tag in edge.tags),
                                  SiteCfg.Attr.SiteID: state.mapping[edge.child.ID],
                                  SiteCfg.Attr.Unanalyzable: SiteCfg.FALSE,
                                  SiteCfg.Attr.Uncertain: uncertain,
                                  SiteCfg.Attr.Suggestion: suggestion})
        state.elems[edge.parent.ID].insert(0, remote_elem)

    def _implicit(node):
        uncertain = (SiteCfg.TRUE if node.incoming[0].attrib.get('uncertain')
                     else SiteCfg.FALSE)
        suggestion = (SiteCfg.TRUE if node.attrib.get('suggest')
                      else SiteCfg.FALSE)
        implicit_elem = ET.Element(SiteCfg.Tags.Implicit,
                                   {SiteCfg.Attr.ElemTag:
                                    "|".join(SiteCfg.EdgeConversion[tag] for tag in node.ftags),
                                    SiteCfg.Attr.SiteID: state.get_id(),
                                    SiteCfg.Attr.Unanalyzable: SiteCfg.FALSE,
                                    SiteCfg.Attr.Uncertain: uncertain,
                                    SiteCfg.Attr.Suggestion: suggestion})
        state.elems[node.fparent.ID].insert(0, implicit_elem)

    def _linkage(link):
        args = [str(state.mapping[x.ID]) for x in link.arguments]
        linker_elem = state.elems[link.relation.ID]
        linkage_elem = ET.Element(SiteCfg.Tags.Linkage, {'args': ','.join(args)})
        linker_elem.insert(0, linkage_elem)

    def _fparent(node):
        primary, remotes = [[e.parent for e in node.incoming if e.attrib.get("remote", False) is v]
                            for v in (False, True)]
        for parents in primary, remotes:
            try:
                return parents[0]
            except IndexError:
                pass
        return None

    def _get_parent(node):
        ret = _fparent(node)
        if ret and ret.tag == layer1.NodeTags.Punctuation:
            ret = _fparent(ret)
        if ret and ret in passage.layer(layer1.LAYER_ID).heads:
            ret = None  # the parent is the fake FNodes head
        return ret

    para_elems = []

    # The IDs are used to check whether a parent should be real or a chunk
    # of a larger unit -- in the latter case we need the new ID
    split_ids = [ID for ID, node in passage.nodes.items()
                 if node.tag == layer1.NodeTags.Foundational and
                 node.discontiguous]
    unit_groups = [_cunit(passage.by_id(ID), None) for ID in split_ids]
    state.elems.update((ID, elem) for ID, elem in zip(split_ids, unit_groups))

    for term in sorted(list(passage.layer(layer0.LAYER_ID).all),
                       key=lambda x: x.position):
        unit = _word(term)
        parent = _get_parent(term)
        while parent is not None:
            if parent.ID in state.mapping and parent.ID not in split_ids:
                state.elems[parent.ID].append(unit)
                break
            elem = _cunit(parent, unit)
            if parent.ID in split_ids:
                elem.set(SiteCfg.Attr.ElemTag, SiteCfg.TBD)
                elem.set(SiteCfg.Attr.GroupID, state.mapping[parent.ID])
            unit = elem
            parent = _get_parent(parent)
        # The uppermost unit (w.o parents) should be the subelement of a
        # paragraph element, if it exists
        if parent is None:
            if term.para_pos == 1:  # need to add paragraph element
                para_elems.append(ET.Element(
                    SiteCfg.Tags.Unit,
                    {SiteCfg.Attr.ElemTag: SiteCfg.TBD,
                     SiteCfg.Attr.SiteID: state.get_id()}))
            para_elems[-1].append(unit)

    # Because we identify a partial discontiguous unit (marked as TBD) only
    # after we create the elements, we may end with something like:
    # <unit ... unitGroupID='3'> ... </unit> <unit ... unitGroupID='3'> ...
    # which we would like to merge under one element.
    # Because we keep changing the tree, we must break and re-iterate each time
    while True:
        for elems_root in para_elems:
            changed = False
            for parent in elems_root.iter():
                changed = False
                if any(x.get(SiteCfg.Attr.GroupID) for x in parent):
                    # Must use list() as we change parent members
                    for i, elem in enumerate(list(parent)):
                        if (i > 0 and elem.get(SiteCfg.Attr.GroupID) and
                                elem.get(SiteCfg.Attr.GroupID) ==
                                parent[i - 1].get(SiteCfg.Attr.GroupID)):
                            parent.remove(elem)
                            for subelem in list(elem):  # merging
                                elem.remove(subelem)
                                parent[i - 1].append(subelem)
                            changed = True
                            break
                    if changed:
                        break
            if changed:
                break
        else:
            break

    # Handling remotes, implicits and linkages
    for remote in [e for n in passage.layer(layer1.LAYER_ID).all
                   for e in n if e.attrib.get('remote')]:
        _remote(remote)
    for implicit in [n for n in passage.layer(layer1.LAYER_ID).all
                     if n.attrib.get('implicit')]:
        _implicit(implicit)
    for linkage in filter(lambda x: x.tag == layer1.NodeTags.Linkage,
                          passage.layer(layer1.LAYER_ID).heads):
        _linkage(linkage)

    # Creating the XML tree
    root = ET.Element('root', {'schemeVersion': SiteCfg.SchemeVersion})
    groups = ET.SubElement(root, 'unitGroups')
    groups.extend(unit_groups)
    units = ET.SubElement(root, SiteCfg.Paths.Main, {SiteCfg.Attr.PassageID: passage.ID})
    ET.SubElement(root, SiteCfg.Paths.Attrib, passage.attrib.copy())
    units0 = ET.SubElement(units, SiteCfg.Tags.Unit,
                           {SiteCfg.Attr.ElemTag: SiteCfg.TBD,
                            SiteCfg.Attr.SiteID: '0',
                            SiteCfg.Attr.Unanalyzable: SiteCfg.FALSE,
                            SiteCfg.Attr.Uncertain: SiteCfg.FALSE})
    units0.extend(para_elems)
    ET.SubElement(root, 'LRUunits')
    ET.SubElement(root, 'hiddenUnits')

    return root


def to_standard(passage):
    """Converts a Passage object to a standard XML root element.

    The standard XML specification is not contained here, but it uses a very
    shallow structure with attributes to create hierarchy.

    :param passage: the passage to convert

    :return: the root element of the standard XML structure
    """

    # This utility stringifies the Unit's attributes for proper XML
    # we don't need to escape the character - the serializer of the XML element
    # will do it (e.g. tostring())
    def _dumps(dic):
        return {str(k): str(v) if type(v) in (str, bool) else json.dumps(v) for k, v in dic.items()}

    # Utility to add an extra element if exists in the object
    def _add_extra(obj, elem):
        return obj.extra and ET.SubElement(elem, 'extra', _dumps(obj.extra))

    # Adds attributes element (even if empty)
    def _add_attrib(obj, elem):
        return ET.SubElement(elem, 'attributes', _dumps(obj.attrib))

    root = ET.Element('root', passageID=str(passage.ID), annotationID='0')
    _add_attrib(passage, root)
    _add_extra(passage, root)

    for layer in sorted(passage.layers, key=attrgetter('ID')):
        layer_elem = ET.SubElement(root, 'layer', layerID=layer.ID)
        _add_attrib(layer, layer_elem)
        _add_extra(layer, layer_elem)
        for node in layer.all:
            node_elem = ET.SubElement(layer_elem, 'node',
                                      ID=node.ID, type=node.tag)
            _add_attrib(node, node_elem)
            _add_extra(node, node_elem)
            for edge in node:
                edge_elem = ET.SubElement(node_elem, 'edge',
                                          toID=edge.child.ID, type=edge.tag)
                _add_attrib(edge, edge_elem)
                _add_extra(edge, edge_elem)
                for category in edge:
                    attrs = {}
                    if category.tag:
                        attrs["tag"] = category.tag
                    if category.slot:
                        attrs["slot"] = str(category.slot)
                    if category.layer:
                        attrs["layer_name"] = category.layer
                    if category.parent:
                        attrs["parent_name"] = category.parent
                    category_elem = ET.SubElement(edge_elem, "category", **attrs)
                    _add_extra(category, category_elem)
    return root


def from_standard(root, extra_funcs=None):
    def _str2bool(x):
        return x == "True"

    attribute_converters = {
        'paragraph': int,
        'paragraph_position': int,
        'remote': _str2bool,
        'implicit': _str2bool,
        'uncertain': _str2bool,
        'suggest': _str2bool,
        None: str,
    }

    def _loads(x):
        try:
            return False if x == "False" else x == "True" or json.loads(x)
        except JSONDecodeError:
            return x

    layer_objs = {layer0.LAYER_ID: layer0.Layer0,
                  layer1.LAYER_ID: layer1.Layer1}

    node_objs = {layer0.NodeTags.Word: layer0.Terminal,
                 layer0.NodeTags.Punct: layer0.Terminal,
                 layer1.NodeTags.Foundational: layer1.FoundationalNode,
                 layer1.NodeTags.Linkage: layer1.Linkage,
                 layer1.NodeTags.Punctuation: layer1.PunctNode}

    def _get_attrib(elem):
        try:
            return {k: attribute_converters.get(k, str)(v)
                    for k, v in elem.find('attributes').items()}
        except AttributeError as e:
            raise core.UCCAError("Element %s has no attributes" % elem.get("ID")) from e

    def _add_extra(obj, elem):
        if elem.find('extra') is not None:
            for k, v in elem.find('extra').items():
                obj.extra[k] = (extra_funcs or {}).get(k, _loads)(v)

    passage = core.Passage(root.get('passageID'), attrib=_get_attrib(root))
    _add_extra(passage, root)
    edge_elems = []
    for layer_elem in root.findall('layer'):
        layer_id = layer_elem.get('layerID')
        layer = layer_objs[layer_id](passage, attrib=_get_attrib(layer_elem))
        _add_extra(layer, layer_elem)
        # some nodes are created automatically, skip creating them when found
        # in the XML (they should have 'constant' IDs) but take their edges
        # and attributes/extra from the XML (may have changed from the default)
        created_nodes = {x.ID: x for x in layer.all}
        for node_elem in layer_elem.findall('node'):
            node_id = node_elem.get('ID')
            tag = node_elem.get('type')
            node = created_nodes.get(node_id)
            if node is None:
                node = node_objs[tag](root=passage, ID=node_id, tag=tag, attrib=_get_attrib(node_elem))
            else:
                for key, value in _get_attrib(node_elem).items():
                    node.attrib[key] = value
            _add_extra(node, node_elem)
            edge_elems += [(node, x) for x in node_elem.findall('edge')]

    # Adding edges (must have all nodes before doing so)
    for from_node, edge_elem in edge_elems:
        to_node = passage.nodes[edge_elem.get('toID')]
        categories_elems = edge_elem.findall('category')
        categories = []
        for c in categories_elems:
            tag = c.get('tag')
            slot = c.get('slot')
            layer = c.get('layer_name')
            parent = c.get('parent_name')
            categories.append((tag, slot, layer, parent))
        if not categories:  # an old xml format
            tag = edge_elem.get('type')
            categories.append((tag, "", "", ""))
        edge = from_node.add_multiple(categories, to_node, edge_attrib=_get_attrib(edge_elem))
        _add_extra(edge, edge_elem)

    return passage


def from_text(text, passage_id="1", tokenized=False, one_per_line=False, extra_format=None, lang="en", *args, **kwargs):
    """Converts from tokenized strings to a Passage object.

    :param text: a multi-line string or a sequence of strings:
                 each line will be a new paragraph, and blank lines separate passages
    :param passage_id: prefix of ID to set for returned passages
    :param tokenized: whether the text is already given as a list of tokens
    :param one_per_line: each line will be a new passage rather than just a new paragraph
    :param extra_format: value to set in passage.extra["format"]
    :param lang: language to use for tokenization model

    :return: generator of Passage object with only Terminal units
    """
    del args, kwargs
    if isinstance(text, str):
        text = text.splitlines()
    if tokenized:
        text = (text,)  # text is a list of tokens, not list of lines
    p = l0 = paragraph = None
    i = 0
    for line in text:
        if not tokenized:
            line = line.strip()
        if line or one_per_line:
            if p is None:
                p = core.Passage("%s_%d" % (passage_id, i), attrib=dict(lang=lang))
                if extra_format is not None:
                    p.extra["format"] = extra_format
                l0 = layer0.Layer0(p)
                layer1.Layer1(p)
                paragraph = 1
            for lex in textutil.get_tokenizer(tokenized, lang=lang)(line):
                l0.add_terminal(text=lex.orth_, punct=lex.is_punct, paragraph=paragraph)
            paragraph += 1
        if p and (not line or one_per_line):
            yield p
            p = None
            i += 1
    if p:
        yield p


def to_text(passage, sentences=True, lang="en", *args, **kwargs):
    """Converts from a Passage object to tokenized strings.

    :param passage: the Passage object to convert
    :param sentences: whether to break the Passage to sentences (one for string)
                      or leave as one string. Defaults to True
    :param lang: language to use for sentence splitting model

    :return: a list of strings - 1 if sentences=False, # of sentences otherwise
    """
    del args, kwargs
    tokens = [x.text for x in sorted(passage.layer(layer0.LAYER_ID).all,
                                     key=attrgetter('position'))]
    # break2sentences return the positions of the end tokens, which is
    # always the index into tokens incremented by ones (tokens index starts
    # with 0, positions with 1). So in essence, it returns the index to start
    # the next sentence from, and we should add index 0 for the first sentence
    if sentences:
        starts = [0] + textutil.break2sentences(passage, lang=lang)
    else:
        starts = [0, len(tokens)]
    return [' '.join(tokens[starts[i]:starts[i + 1]])
            for i in range(len(starts) - 1)]


def to_sequence(passage):
    """Converts from a Passage object to linearized text sequence.

    :param passage: the Passage object to convert

    :return: a list of strings - 1 if sentences=False, # of sentences otherwise
    """
    def _position(edge):
        while edge.child.layer.ID != layer0.LAYER_ID:
            edge = edge.child.outgoing[0]
        return tuple(map(edge.child.attrib.get, ('paragraph', 'paragraph_position')))

    seq = ''
    stacks = []
    edges = [e for u in passage.layer(layer1.LAYER_ID).all
             if not u.incoming for e in u.outgoing]
    # should avoid printing the same node more than once, refer to it by ID
    # convert back to passage
    # use Node.__str__ as it already does this...
    while True:
        if edges:
            stacks.append(sorted(edges, key=_position, reverse=True))
        else:
            stacks[-1].pop()
            while not stacks[-1]:
                stacks.pop()
                if not stacks:
                    return seq.rstrip()
                seq += ']_'
                seq += stacks[-1][-1].tag
                seq += ' '
                stacks[-1].pop()
        e = stacks[-1][-1]
        edges = e.child.outgoing
        if edges:
            seq += '['
        seq += e.child.attrib.get('text') or e.tag
        seq += ' '


UNANALYZABLE = "Unanalyzable"
UNCERTAIN = "Uncertain"
IGNORED_CATEGORIES = {UNANALYZABLE, UNCERTAIN, COORDINATED_MAIN_REL}
IGNORED_ABBREVIATIONS = {EdgeTags.Unanalyzable, EdgeTags.Uncertain, COORDINATED_MAIN_REL}


def get_json_attrib(d):
    attrib = {}
    user = d.get("user")
    if user:
        user_id = user.get("id")
        if user_id:
            attrib["userID"] = user_id
    remarks = d.get("user_comment")
    if remarks:
        attrib["remarks"] = remarks
    annotation_id = d.get("id")
    if annotation_id:
        attrib["annotationID"] = annotation_id
    return attrib or None


def get_categories_details(d):
    # mapping from a category id to the category's parent, layer
    curr_layer = d['project']['layer']
    categories = {}
    base_layer = None
    while curr_layer:
        base_layer = curr_layer['name']
        for c in curr_layer['categories']:
            categories[c['id']] = {'name': c["name"], 'parent': c.get("parent"), 'layer': base_layer}
        curr_layer = curr_layer['parent']
    return base_layer, categories


def from_json(lines, *args, skip_category_mapping=False, by_external_id=False, **kwargs):
    """Convert text (or dict) in UCCA-App JSON format to a Passage object.
        According to the API, annotation units are organized in a tree, where the full unit is included as a child of
          its parent: https://github.com/omriabnd/UCCA-App/blob/master/UCCAApp_REST_API_Reference.pdf
          Just token children are included in the simple form ("id" only), in the "children_tokens" field.
          Note: children_tokens contains all tokens that are descendants of the unit, not just immediate children.
        tree_id: encodes the path leading to the node, e.g., 3-5-2.
          1-based, and in reverse order to the children's appearance, so that 1 is last, 2 is before last, etc.
          The exception is the first level, where there is just 0, and the next level starts from 1 (not 0-1).
        parent_tree_id: the tree_id of the node's parent, where 0 is the root
    :param lines: iterable of lines in JSON format, describing a single passage.
    :param skip_category_mapping: if False, translate category names to edge tag abbreviations; if True, don't
    :param by_external_id: set passage ID to be the external ID of the source passage rather than its ID
    :return: generator of Passage objects
    """
    del args, kwargs
    d = lines if isinstance(lines, dict) else json.loads("".join(lines))
    passage_id = d["passage"]["id"]
    attrib = get_json_attrib(d)
    base_layer, categories = get_categories_details(d)
    base_slot = ""
    if by_external_id:
        attrib["passageID"] = passage_id
        external_id = d["passage"]["external_id"]
        assert external_id, "No external ID found for passage %s (task %s)" % (passage_id, d.get("id", "unknown"))
        passage_id = external_id
    passage = core.Passage(str(passage_id), attrib=attrib)

    # Create terminals
    l0 = layer0.Layer0(passage)
    token_id_to_terminal = {token["id"]: l0.add_terminal(
        text=token["text"], punct=not token["require_annotation"], paragraph=1)
        for token in sorted(d["tokens"], key=itemgetter("index_in_task"))}

    # Create non-terminals
    l1 = layer1.Layer1(passage)
    tree_id_to_node = {}
    token_id_to_preterminal = {}
    category_name_to_edge_tag = {} if skip_category_mapping else EdgeTags.__dict__
    # Assuming topological sort: parents always appear before children
    for unit in sorted(d["annotation_units"], key=itemgetter("is_remote_copy")):  # Get non-remotes first
        tree_id = unit["tree_id"]
        remote = unit["is_remote_copy"]
        cloned_from_tree_id = None
        if remote:
            cloned_from_tree_id = unit.get("cloned_from_tree_id")
            if cloned_from_tree_id is None:
                raise ValueError("Remote unit %s without cloned_from_tree_id" % tree_id)
        elif tree_id in tree_id_to_node:
            raise ValueError("Unit %s is repeated" % tree_id)
        parent_tree_id = unit["parent_tree_id"]
        if parent_tree_id is None:  # Root node: no need to create
            tree_id_to_node[tree_id] = None
            continue
        try:
            parent_node = tree_id_to_node[parent_tree_id]
        except KeyError as e:
            raise ValueError("Unit %s appears before its parent, %s" % (tree_id, parent_tree_id)) from e

        unit_categories = []
        for category in unit.get("categories", ()):
            try:
                category_name = category.get("name") or categories[category["id"]]['name']
            except KeyError as e:
                raise ValueError("Category missing from layer: " + category["id"]) from e
            c_tag = category_name_to_edge_tag.get(category_name.replace(" ", ""), category_name.replace(" ", "_"))
            c_slot = category.get("slot", "")
            c_data = categories[category["id"]]
            c_layer = c_data['layer']
            if c_layer == base_layer:
                base_slot = c_slot
            c_parent = c_data['parent']
            if c_parent:   # make sure it is not empty
                c_parent = category_name_to_edge_tag.get(c_parent['name'].replace(" ", ""),
                                                         c_parent['name'].replace(" ", "_"))
            unit_categories.append((c_tag, c_slot, c_layer, c_parent))

        if not unit_categories:
            raise ValueError("Unit %s has no categories" % tree_id)

        edge_attrib = {}
        for unit_category, *_ in unit_categories:
            if unit_category == EdgeTags.Uncertain:
                edge_attrib["uncertain"] = True
            elif unit_category == COORDINATED_MAIN_REL:
                edge_attrib[COORDINATED_MAIN_REL] = True
        if not edge_attrib:
            edge_attrib = None
        unit_categories = [uc for uc in unit_categories if uc[0] not in IGNORED_ABBREVIATIONS]
        children_tokens = [] if unit["type"] == "IMPLICIT" else unit["children_tokens"]
        try:
            terminal = token_id_to_terminal[children_tokens[0]["id"]] if len(children_tokens) == 1 else None
        except (IndexError, KeyError):
            terminal = None
        if remote:
            try:
                node = tree_id_to_node[cloned_from_tree_id]
            except KeyError as e:
                raise ValueError("Remote copy %s refers to nonexistent unit: %s" %
                                 (tree_id, cloned_from_tree_id)) from e
            l1.add_remote_multiple(parent_node, unit_categories, node, edge_attrib=edge_attrib)
        elif not skip_category_mapping and terminal and layer0.is_punct(terminal):
            tree_id_to_node[tree_id] = l1.add_punct(None, terminal, base_layer, base_slot, edge_attrib=edge_attrib)
        elif tree_id not in tree_id_to_node:
            node = tree_id_to_node[tree_id] = l1.add_fnode_multiple(parent_node, unit_categories,
                                                                    implicit=unit["type"] == "IMPLICIT",
                                                                    edge_attrib=edge_attrib)
            node.extra['tree_id'] = tree_id
            comment = unit.get("comment")
            if comment:
                node.extra['remarks'] = comment
            for token in children_tokens:
                token_id_to_preterminal[token["id"]] = node

    # Attach terminals to non-terminals
    for token_id, node in token_id_to_preterminal.items():
        terminal = token_id_to_terminal[token_id]
        if skip_category_mapping or not layer0.is_punct(terminal):
            node.add(EdgeTags.Terminal, terminal)

    return passage


IGNORED_EDGE_TAGS = {EdgeTags.Punctuation, EdgeTags.Terminal}


def to_json(passage, *args, return_dict=False, tok_task=None, all_categories=None, skip_category_mapping=False,
            **kwargs):
    """Convert a Passage object to text (or dict) in UCCA-App JSON
    :param passage: the Passage object to convert
    :param return_dict: whether to return dict rather than list of lines
    :param tok_task: either None (to do tokenization too), or a completed tokenization task dict with token IDs,
                     or True, to indicate that the function should do only tokenization and not annotation
    :param all_categories: list of category dicts so that IDs can be added, if available - otherwise names are used
    :param skip_category_mapping: if False, translate edge tag abbreviations to category names; if True, don't
    :return: list of lines in JSON format if return_dict=False, or task dict if True
    """
    del args, kwargs
    # Create tokens
    terminal_id_to_token_id = {}
    terminals = sorted(passage.layer(layer0.LAYER_ID).all, key=attrgetter("position"))
    if tok_task is True or tok_task is None:  # Necessary because bool(tok_task) == True also if a task dict is given
        tokens = []
        start_index = 0
        for terminal in terminals:
            end_index = start_index + len(terminal.text)
            token = dict(text=terminal.text, start_index=start_index, end_index=end_index,
                         index_in_task=terminal.position - 1,
                         require_annotation=not layer0.is_punct(terminal))
            if tok_task is None:  # When doing tokenization as a task, no need to fill the IDs (done by the server)
                token["id"] = terminal_id_to_token_id[terminal.ID] = terminal.position
            tokens.append(token)
            start_index = end_index + 1
    else:
        tokens = sorted(tok_task["tokens"], key=itemgetter("start_index"))
        if len(tokens) != len(terminals):
            raise ValueError("Number of tokens in tokenization task != number of terminals in passage: %d != %d" %
                             (len(tokens), len(terminals)))
        for token, terminal in zip(tokens, terminals):
            terminal_id_to_token_id[terminal.ID] = token["id"]
    # Create annotation units
    category_name_to_id = {c["name"]: c["id"] for c in all_categories} if all_categories else None
    annotation_units = []
    if tok_task is not True:  # Annotation required, not just tokenization; tok_task might be None or a full task dict

        def _create_unit(elements, n, ts, cs, is_remote_copy=False, parent_tree_id=None):
            implicit = n.attrib.get("implicit")
            assert implicit or ts, "Only implicit units may not have a children_tokens field: " + n.ID
            return dict(tree_id="-".join(map(str, elements)),
                        type="IMPLICIT" if implicit else "REGULAR", is_remote_copy=is_remote_copy,
                        categories=cs, comment=n.extra.get("remarks", ""), cluster="", cloned_from_tree_id=None,
                        parent_tree_id=parent_tree_id, gui_status="OPEN",
                        children_tokens=[dict(id=terminal_id_to_token_id[t.ID]) for t in ts])

        root_node = passage.layer(layer1.LAYER_ID).heads[0]  # Ignoring Linkage: taking only the first head
        root_unit = _create_unit([0], root_node, terminals, [])
        annotation_units.append(root_unit)
        node_id_to_primary_annotation_unit = {root_node.ID: root_unit}
        node_id_to_remote_annotation_units = defaultdict(list)
        edge_tag_to_category_name = {} if skip_category_mapping else \
            {v: re.sub(r"(?<=[a-z])(?=[A-Z])", " ", k) for k, v in EdgeTags.__dict__.items()}

        def _outgoing(elements, n):  # (ID element, outgoing edges sharing parent & child) for all n's children
            return [(elements + [i], list(es)) for i, (_, es) in enumerate(
                groupby(sorted([e for e in n if e.tag not in IGNORED_EDGE_TAGS],
                               key=attrgetter("child.start_position", "child.ID")),
                        key=attrgetter("child.ID")), start=1)]

        # (tree id elements, edges per child) for each edge
        queue = _outgoing([], root_node)
        while queue:  # breadth-first search
            tree_id_elements, edges = queue.pop(0)  # edges all have the same child but may differ by category
            edge = edges[0]
            node = edge.child
            remote = edge.attrib.get("remote", False)
            parent_annotation_unit = node_id_to_primary_annotation_unit[edge.parent.ID]
            # This can be used for additional tags written in the remarks -- no agreed format but some workaround:
            # list(filter(None, (_extra_tag(e) for e in edges if not e.attrib.get("remote"))))
            categories = [dict(name=edge_tag_to_category_name.get(c.tag, c.tag), slot=int(c.slot) if c.slot else 1)
                          for c in edge]
            terminals = node.get_terminals()
            outgoing = _outgoing(tree_id_elements, node)
            if not outgoing and len(terminals) > 1:
                categories.insert(0, dict(name=UNANALYZABLE, slot=1))
            if node.attrib.get("uncertain"):
                categories.append(dict(name=UNCERTAIN, slot=1))
            if all_categories:
                for category in categories:
                    try:
                        category["id"] = category_name_to_id[category["name"]]
                        del category["name"]
                    except KeyError as exception:
                        raise ValueError("Category missing from layer: " + category["name"]) from exception
            assert categories, "Non-root unit without categories: %s" % node.ID
            unit = _create_unit(tree_id_elements, node, terminals, categories, is_remote_copy=remote,
                                parent_tree_id=parent_annotation_unit["tree_id"])
            if remote:
                node_id_to_remote_annotation_units[node.ID].append(unit)
            else:
                queue += outgoing
                node_id_to_primary_annotation_unit[node.ID] = unit
            annotation_units.append(unit)
        # Update cloned_from_tree_id of remote copies to be the tree_id of their non-remote units
        for node_id, remote_annotation_units in node_id_to_remote_annotation_units.items():
            for unit in remote_annotation_units:
                unit["cloned_from_tree_id"] = node_id_to_primary_annotation_unit[node_id]["tree_id"]

    def _tree_id_key(u):
        return tuple(map(int, u["tree_id"].split("-")))

    annotation_units = sorted(annotation_units, key=_tree_id_key)
    if tokens and annotation_units:
        for _, units in groupby(annotation_units[1:], key=lambda u: _tree_id_key(u)[:-1]):
            units = list(units)
            start_indices = [min([t["start_index"] for t in tokens
                                  if any(s["id"] == t["id"] for s in u["children_tokens"])] or [-1]) for u in units]
            assert all(i == -1 or i < j for i, j in zip(start_indices[:-1], start_indices[1:])), \
                "Siblings are not correctly ordered by their minimal start_index: " +\
                ", ".join(u["comment"] for u in units)

    d = dict(tokens=tokens, annotation_units=annotation_units, manager_comment=passage.ID)
    return d if return_dict else json.dumps(d).splitlines()


def file2passage(filename):
    """Opens a file and returns its parsed Passage object
    Tries to read both as a standard XML file and as a binary pickle
    :param filename: file name to write to
    """
    methods = [pickle2passage, xml2passage]
    _, ext = os.path.splitext(filename)
    if ext == ".xml":
        del methods[0]
    elif ext == ".pickle":
        del methods[1]
    exception = None
    for method in methods:
        try:
            return method(filename)
        except Exception as e:
            exception = e
    if exception:
        raise IOError("Failed reading '%s'" % filename) from exception


def xml2passage(filename):
    with open(filename, encoding="utf-8") as f:
        return from_standard(ET.ElementTree().parse(f))


def pickle2passage(filename):
    with open(filename, "rb") as h:
        return pickle.load(h)


def passage2file(passage, filename, indent=True, binary=False):
    """Writes a UCCA passage as a standard XML file or a binary pickle
    :param passage: passage object to write
    :param filename: file name to write to
    :param indent: whether to indent each line
    :param binary: whether to write pickle format (or XML)
    """
    if binary:
        with open(filename, "wb") as h:
            pickle.dump(passage, h)
    else:  # xml
        root = to_standard(passage)
        xml_string = ET.tostring(root).decode()
        output = textutil.indent_xml(xml_string) if indent else xml_string
        with open(filename, "w", encoding="utf-8") as h:
            h.write(output)


def split2sentences(passage, remarks=False, lang="en", ids=None):
    return split2segments(passage, is_sentences=True, remarks=remarks, lang=lang, ids=ids)


def split2paragraphs(passage, remarks=False, lang="en", ids=None):
    return split2segments(passage, is_sentences=False, remarks=remarks, lang=lang, ids=ids)


def split2segments(passage, is_sentences, remarks=False, lang="en", ids=None):
    """
    Split passage to sub-passages
    :param passage: Passage object
    :param is_sentences: if True, split to sentences; otherwise, paragraphs
    :param remarks: Whether to add remarks with original node IDs
    :param lang: language to use for sentence splitting model
    :param ids: optional iterable of ids to set passage IDs for each split
    :return: sequence of passages
    """
    ends = (textutil.break2sentences if is_sentences else textutil.break2paragraphs)(passage, lang=lang)
    return split_passage(passage, ends, remarks=remarks, ids=ids)


def split_passage(passage, ends, remarks=False, ids=None, suffix_format="%03d", suffix_start=0):
    """
    Split the passage on the given terminal positions
    :param passage: passage to split
    :param ends: sequence of positions at which the split passages will end
    :param remarks: add original node ID as remarks to the new nodes
    :param ids: optional iterable of ids, the same length as ends, to set passage IDs for each split
    :param suffix_format: in case ids is None, use this format for the running index suffix
    :param suffix_start: in case ids is None, use this starting index for the running index suffix
    :return: sequence of passages
    """
    passages = []
    for i, (start, end, index) in enumerate(zip([0] + ends[:-1], ends, ids or repeat(None)), start=suffix_start):
        if start == end:
            continue
        other = core.Passage(ID=index or ("%s" + suffix_format) % (passage.ID, i), attrib=passage.attrib.copy())
        other.extra = passage.extra.copy()
        # Create terminals and find layer 1 nodes to be included
        l0 = passage.layer(layer0.LAYER_ID)
        other_l0 = layer0.Layer0(root=other, attrib=l0.attrib.copy())
        other_l0.extra = l0.extra.copy()
        level = set()
        nodes = set()
        id_to_other = {}
        paragraphs = []
        for terminal in l0.all[start:end]:
            other_terminal = other_l0.add_terminal(terminal.text, terminal.punct, 1)
            _copy_extra(terminal, other_terminal, remarks)
            other_terminal.extra["orig_paragraph"] = terminal.paragraph
            if terminal.paragraph not in paragraphs:
                paragraphs.append(terminal.paragraph)
            id_to_other[terminal.ID] = other_terminal
            level.update(terminal.parents)
            nodes.add(terminal)
        while level:
            nodes.update(level)
            level = set(e.parent for n in level for e in n.incoming if not e.attrib.get("remote") and
                        e.tag != layer1.EdgeTags.Punctuation and e.parent not in nodes)

        other_l1 = layer1.Layer1(root=other, attrib=passage.layer(layer1.LAYER_ID).attrib.copy())
        _copy_l1_nodes(passage, other, id_to_other, set(nodes), remarks=remarks)
        attach_punct(other_l0, other_l1)
        for j, paragraph in enumerate(paragraphs, start=1):
            other_l0.doc(j)[:] = l0.doc(paragraph)
        other.frozen = passage.frozen
        passages.append(other)
    return passages


def join_passages(passages, passage_id=None, remarks=False):
    """
    Join passages to one passage with all the nodes in order
    :param passages: sequence of passages to join
    :param passage_id: ID of newly created passage (otherwise, ID of first passage)
    :param remarks: add original node ID as remarks to the new nodes
    :return: joined passage
    """
    if not passages:
        raise ValueError("Cannot join empty list of passages")
    other = core.Passage(ID=passage_id or passages[0].ID, attrib=passages[0].attrib.copy())
    other.extra = passages[0].extra.copy()
    l0 = passages[0].layer(layer0.LAYER_ID)
    l1 = passages[0].layer(layer1.LAYER_ID)
    other_l0 = layer0.Layer0(root=other, attrib=l0.attrib.copy())
    layer1.Layer1(root=other, attrib=l1.attrib.copy())
    id_to_other = {}
    paragraph = 0
    for passage in passages:
        l0 = passage.layer(layer0.LAYER_ID)
        paragraphs = set()
        for terminal in l0.all:
            if terminal.para_pos == 1:
                paragraph += 1
            orig_paragraph = terminal.extra.get("orig_paragraph")
            if orig_paragraph is not None:
                paragraph = orig_paragraph
            paragraphs.add(paragraph)
            other_terminal = other_l0.add_terminal(terminal.text, terminal.punct, paragraph)
            _copy_extra(terminal, other_terminal, remarks)
            id_to_other[terminal.ID] = other_terminal
        for paragraph in paragraphs:
            other_l0.doc(paragraph).extend(l0.doc(1))
        _copy_l1_nodes(passage, other, id_to_other, remarks=remarks)
    return other


def _copy_l1_nodes(passage, other, id_to_other, include=None, remarks=False):
    """
    Copy all layer 1 nodes from one passage to another
    :param passage: source passage
    :param other: target passage
    :param id_to_other: dictionary mapping IDs from passage to existing nodes from other
    :param include: if given, only the nodes from this set will be copied
    :param remarks: add original node ID as remarks to the new nodes
    """
    l1 = passage.layer(layer1.LAYER_ID)
    other_l1 = other.layer(layer1.LAYER_ID)
    queue = [(n, None) for n in l1.heads]
    linkages = []
    remotes = []
    heads = []
    while queue:
        node, other_node = queue.pop()
        if node.tag == layer1.NodeTags.Linkage:
            if include is None or include.issuperset(node.children):
                linkages.append(node)
            continue
        if other_node is None:
            heads.append(node)
            other_node = other_l1.heads[0]
        for edge in node:
            is_remote = edge.attrib.get("remote", False)
            if include is None or edge.child in include or _unanchored(edge.child):
                if is_remote:
                    remotes.append((edge, other_node))
                    continue
                if edge.child.layer.ID == layer0.LAYER_ID:
                    edge_categories = [(c.tag, c.slot, c.layer, c.parent) for c in edge.categories]
                    other_node.add_multiple(edge_categories, id_to_other[edge.child.ID])
                    continue
                if edge.child.tag == layer1.NodeTags.Punctuation:
                    grandchild = edge.child.children[0]
                    other_child = other_l1.add_punct(other_node, id_to_other[grandchild.ID])
                    other_child.incoming[0].categories = edge.categories
                else:
                    edge_categories = [(c.tag, c.slot, c.layer, c.parent) for c in edge.categories]
                    other_child = other_l1.add_fnode_multiple(other_node, edge_categories,
                                                              implicit=edge.child.attrib.get("implicit"))
                    queue.append((edge.child, other_child))
                id_to_other[edge.child.ID] = other_child
                _copy_extra(edge.child, other_child, remarks)  # Add remotes
            elif is_remote:  # Cross-paragraph remote edge -> create implicit child instead
                edge_categories = [(c.tag, c.slot, c.layer, c.parent) for c in edge.categories]
                other_l1.add_fnode_multiple(other_node, edge_categories, implicit=True)
    for edge, parent in remotes:
        other_child = id_to_other.get(edge.child.ID)
        edge_categories = [(c.tag, c.slot, c.layer, c.parent) for c in edge.categories]
        if other_child is None:  # Promote remote edge to primary if the original primary parent is gone due to split
            id_to_other[edge.child.ID] = other_child = \
                other_l1.add_fnode_multiple(parent, edge_categories, implicit=edge.child.attrib.get("implicit"))
            _copy_extra(edge.child, other_child, remarks)
        else:
            other_l1.add_remote_multiple(parent, edge_categories, other_child)
    # Add linkages
    for linkage in linkages:
        try:
            arguments = [id_to_other[argument.ID] for argument in linkage.arguments]
            other_linkage = other_l1.add_linkage(id_to_other[linkage.relation.ID], *arguments)
            _copy_extra(linkage, other_linkage, remarks)
        except layer1.MissingRelationError:
            pass
    for head, other_head in zip(heads, other_l1.heads):
        _copy_extra(head, other_head, remarks)


def _copy_extra(node, other, remarks=False):
    other.extra.update(node.extra)
    if remarks:
        other.extra["remarks"] = node.ID


def _unanchored(n):
    unanchored_children = False
    for e in n:
        if not e.attrib.get("remote"):
            if _unanchored(e.child):
                unanchored_children = True
            else:
                return False
    return n.attrib.get("implicit") or unanchored_children
