# -*- coding: utf-8 -*-
#!/usr/bin/env python

"""
AMR (Abstract Meaning Representation) structure
For detailed description of AMR, see http://www.isi.edu/natural-language/amr/a.pdf

"""

from collections import defaultdict
import sys

# change this if needed
ERROR_LOG = sys.stderr

# change this if needed
DEBUG_LOG = sys.stderr


class AMR(object):
    """
    AMR is a rooted, labeled graph to represent semantics.
    This class has the following members:
    nodes: list of node in the graph. Its ith element is the name of the ith node. For example, a node name
           could be "a1", "b", "g2", .etc
    node_values: list of node labels (values) of the graph. Its ith element is the value associated with node i in
                 nodes list. In AMR, such value is usually a semantic concept (e.g. "boy", "want-01")
    root: root node name
    relations: list of edges connecting two nodes in the graph. Each entry is a link between two nodes, i.e. a triple
               <relation name, node1 name, node 2 name>. In AMR, such link denotes the relation between two semantic
               concepts. For example, "arg0" means that one of the concepts is the 0th argument of the other.
    attributes: list of edges connecting a node to an attribute name and its value. For example, if the polarity of
               some node is negative, there should be an edge connecting this node and "-". A triple < attribute name,
               node name, attribute value> is used to represent such attribute. It can also be viewed as a relation.

    """
    def __init__(self, node_list=None, node_value_list=None, relation_list=None, attribute_list=None):
        """
        node_list: names of nodes in AMR graph, e.g. "a11", "n"
        node_value_list: values of nodes in AMR graph, e.g. "group" for a node named "g"
        relation_list: list of relations between two nodes
        attribute_list: list of attributes (links between one node and one constant value)

        """
        # initialize AMR graph nodes using list of nodes name
        # root, by default, is the first in var_list

        if node_list is None:
            self.nodes = []
            self.root = None
        else:
            self.nodes = node_list[:]
            if len(node_list) != 0:
                self.root = node_list[0]
            else:
                self.root = None
        if node_value_list is None:
            self.node_values = []
        else:
            self.node_values = node_value_list[:]
        if relation_list is None:
            self.relations = []
        else:
            self.relations = relation_list[:]
        if attribute_list is None:
            self.attributes = []
        else:
            self.attributes = attribute_list[:]

    def rename_node(self, prefix):
        """
        Rename AMR graph nodes to prefix + node_index to avoid nodes with the same name in two different AMRs.

        """
        node_map_dict = {}
        # map each node to its new name (e.g. "a1")
        for i in range(0, len(self.nodes)):
            node_map_dict[self.nodes[i]] = prefix + str(i)
        # update node name
        for i, v in enumerate(self.nodes):
            self.nodes[i] = node_map_dict[v]
        # update node name in relations
        for i, d in enumerate(self.relations):
            new_dict = {}
            for k, v in d.items():
                new_dict[node_map_dict[k]] = v
            self.relations[i] = new_dict
  
    def get_triples(self):
        """
        Get the triples in three lists.
        instance_triple: a triple representing an instance. E.g. instance(w, want-01)
        attribute triple: relation of attributes, e.g. polarity(w, - )
        and relation triple, e.g. arg0 (w, b)

        """
        instance_triple = []
        relation_triple = []
        attribute_triple = []
        for i in range(len(self.nodes)):
            instance_triple.append(("instance", self.nodes[i], self.node_values[i]))
            # k is the other node this node has relation with
            # v is relation name
            for k, v in self.relations[i].items():
                relation_triple.append((v, self.nodes[i], k))
            # k2 is the attribute name
            # v2 is the attribute value
            for k2, v2 in self.attributes[i].items():
                attribute_triple.append((k2, self.nodes[i], v2))
        return instance_triple, attribute_triple, relation_triple


    def get_triples2(self):
        """
        Get the triples in two lists:
        instance_triple: a triple representing an instance. E.g. instance(w, want-01)
        relation_triple: a triple representing all relations. E.g arg0 (w, b) or E.g. polarity(w, - )
        Note that we do not differentiate between attribute triple and relation triple. Both are considered as relation
        triples.
        All triples are represented by (triple_type, argument 1 of the triple, argument 2 of the triple)

        """
        instance_triple = []
        relation_triple = []
        for i in range(len(self.nodes)):
            # an instance triple is instance(node name, node value).
            # For example, instance(b, boy).
            instance_triple.append(("instance", self.nodes[i], self.node_values[i]))
            # k is the other node this node has relation with
            # v is relation name
            for k, v in self.relations[i].items():
                relation_triple.append((v, self.nodes[i], k))
            # k2 is the attribute name
            # v2 is the attribute value
            for k2, v2 in self.attributes[i].items():
                relation_triple.append((k2, self.nodes[i], v2))
        return instance_triple, relation_triple


    def __str__(self):
        """
        Generate AMR string for better readability

        """
        lines = []
        for i in range(len(self.nodes)):
            lines.append("Node "+ str(i) + " " + self.nodes[i])
            lines.append("Value: " + self.node_values[i])
            lines.append("Relations:")
            for k, v in self.relations[i].items():
                lines.append("Node " + k + " via " + v)
            for k2, v2 in self.attributes[i].items():
                lines.append("Attribute: " + k2 + " value " + v2)
        return "\n".join(lines)

    def __repr__(self):
        return self.__str__()

    def output_amr(self):
        """
        Output AMR string

        """
        print >> DEBUG_LOG, self.__str__()

    @staticmethod
    def inverted_label(label):
        """Return the label of the inverted arc for an arc labeled `label`. If
        the arc should not be inverted, return None."""
        if label == "mod":
            return "domain"
        elif label.endswith("-of-of") or label.endswith("-of") and label != "consist-of" and not label.startswith("prep-"):
            return label[:-3]
        else:
            return None

    @staticmethod
    def parse_AMR_line(line):
        """
        Parse a AMR from line representation to an AMR object.
        This parsing algorithm scans the line once and process each character, in a shift-reduce style.

        """
        # Current state. It denotes the last significant symbol encountered. 1 for (, 2 for :, 3 for /,
        # and 0 for start state or ')'
        # Last significant symbol is ( --- start processing node name
        # Last significant symbol is : --- start processing relation name
        # Last significant symbol is / --- start processing node value (concept name)
        # Last significant symbol is ) --- current node processing is complete
        # Note that if these symbols are inside parenthesis, they are not significant symbols.
        state = 0
        # node stack for parsing
        stack = []
        # current not-yet-reduced character sequence
        cur_charseq = []
        # key: node name value: node value
        node_dict = {}
        # node name list (order: occurrence of the node)
        node_name_list = []
        # key: node name:  value: list of (relation name, the other node name)
        node_relation_dict1 = defaultdict(list)
        # key: node name, value: list of (attribute name, const value) or (relation name, unseen node name)
        node_relation_dict2 = defaultdict(list)
        # current relation name
        cur_relation_name = ""
        # having unmatched quote string
        in_quote = False
        for i, c in enumerate(line.strip()):
            if c == " ":
                # allow space in relation name
                if state == 2:
                    cur_charseq.append(c)
                continue
            if c == "\"":
                # flip in_quote value when a quote symbol is encountered
                in_quote = not in_quote
            elif c == "(":
                # not significant symbol if inside quote
                if in_quote:
                    continue
                # get the attribute name
                # e.g :arg0 (x ...
                # at this point we get "arg0"
                if state == 2:
                    # in this state, current relation name should be empty
                    if cur_relation_name != "":
                        print >> ERROR_LOG, "Format error when processing ", line[0:i+1]
                        return None
                    # update current relation name for future use
                    cur_relation_name = "".join(cur_charseq).strip()
                    cur_charseq[:] = []
                state = 1
            elif c == ":":
                # not significant symbol if inside quote
                if in_quote:
                    continue
                # Last significant symbol is "/". Now we encounter ":"
                # Example:
                # :OR (o2 / *OR*
                #    :mod (o3 / official)
                #  gets node value "*OR*" at this point
                if state == 3:
                    node_value = "".join(cur_charseq)
                    # clear current char sequence
                    cur_charseq[:] = []
                    # pop node name ("o2" in the above example)
                    cur_node_name = stack[-1]
                    # update node name/value map
                    node_dict[cur_node_name] = node_value
                # Last significant symbol is ":". Now we encounter ":"
                # Example:
                # :op1 w :quant 30
                # or :day 14 :month 3
                # the problem is that we cannot decide if node value is attribute value (constant)
                # or node value (variable) at this moment
                elif state == 2:
                    temp_attr_value = "".join(cur_charseq)
                    cur_charseq[:] = []
                    parts = temp_attr_value.split()
                    if len(parts) < 2:
                        print >> ERROR_LOG, "Error in processing", line[0:i+1]
                        return None
                    # For the above example, node name is "op1", and node value is "w"
                    # Note that this node name might not be encountered before
                    relation_name = parts[0].strip()
                    relation_value = parts[1].strip()
                    # We need to link upper level node to the current
                    # top of stack is upper level node
                    if len(stack) == 0:
                        print >> ERROR_LOG, "Error in processing", line[:i], relation_name, relation_value
                        return None
                    # if we have not seen this node name before
                    if node_value not in node_dict:
                        node_relation_dict2[stack[-1]].append((relation_name, relation_value))
                    else:
                        inverted_relation_name = AMR.inverted_label(relation_name)
                        if inverted_relation_name is None:
                            node_relation_dict1[stack[-1]].append((relation_name, relation_value))
                        else:
                            node_relation_dict1[relation_value].append((inverted_relation_name, stack[-1]))
                state = 2
            elif c == "/":
                if in_quote:
                    continue
                # Last significant symbol is "(". Now we encounter "/"
                # Example:
                # (d / default-01
                # get "d" here
                if state == 1:
                    node_name = "".join(cur_charseq)
                    cur_charseq[:] = []
                    # if this node name is already in node_dict, it is duplicate
                    if node_name in node_dict:
                        print >> ERROR_LOG, "Duplicate node name ", node_name, " in parsing AMR"
                        return None
                    # push the node name to stack
                    stack.append(node_name)
                    # add it to node name list
                    node_name_list.append(node_name)
                    # if this node is part of the relation
                    # Example:
                    # :arg1 (n / nation)
                    # cur_relation_name is arg1
                    # node name is n
                    # we have a relation arg1(upper level node, n)
                    if cur_relation_name != "":
                        # If the relation should be reversed, we store the reverse relation.
                        inverted_relation_name = AMR.inverted_label(cur_relation_name)
                        if inverted_relation_name is None:
                            # stack[-2] is upper_level node we encountered, as we just add node_name to stack
                            node_relation_dict1[stack[-2]].append((cur_relation_name, node_name))
                        else:
                            node_relation_dict1[node_name].append((inverted_relation_name, stack[-2]))
                        # clear current_relation_name
                        cur_relation_name = ""
                else:
                    # error if in other state
                    print >> ERROR_LOG, "Error in parsing AMR", line[0:i+1]
                    return None
                state = 3
            elif c == ")":
                if in_quote:
                    continue
                # stack should be non-empty to find upper level node
                if len(stack) == 0:
                    print >> ERROR_LOG, "Unmatched parenthesis at position", i, "in processing", line[0:i+1]
                    return None
                # Last significant symbol is ":". Now we encounter ")"
                # Example:
                # :op2 "Brown") or :op2 w)
                # get \"Brown\" or w here
                if state == 2:
                    temp_attr_value = "".join(cur_charseq)
                    cur_charseq[:] = []
                    parts = temp_attr_value.split()
                    if len(parts) < 2:
                        print >> ERROR_LOG, "Error processing", line[:i+1], temp_attr_value
                        return None
                    relation_name = parts[0].strip()
                    relation_value = parts[1].strip()
                    inverted_relation_name = AMR.inverted_label(relation_name)
                    if inverted_relation_name is not None:
                        # Store the reverse of the relation.  We are
                        # sure relation_value is a node here, as
                        # reversible relations are only between nodes.
                        node_relation_dict1[relation_value].append((inverted_relation_name, stack[-1]))
                    # attribute value not seen before
                    # Note that it might be a constant attribute value, or an unseen node
                    # process this after we have seen all the node names
                    elif relation_value not in node_dict:
                        node_relation_dict2[stack[-1]].append((relation_name, relation_value))
                    else:
                        node_relation_dict1[stack[-1]].append((relation_name, relation_value))
                # Last significant symbol is "/". Now we encounter ")"
                # Example:
                # :arg1 (n / nation)
                # we get "nation" here
                elif state == 3:
                    node_value = "".join(cur_charseq)
                    cur_charseq[:] = []
                    cur_node_name = stack[-1]
                    # map node name to its value
                    node_dict[cur_node_name] = node_value
                # pop from stack, as the current node has been processed
                stack.pop()
                cur_relation_name = ""
                state = 0
            else:
                # not significant symbols, so we just shift.
                cur_charseq.append(c)
        #create data structures to initialize an AMR
        node_value_list = []
        relation_list = []
        attribute_list = []
        delayed_inverted_edges = []
        for v in node_name_list:
            if v not in node_dict:
                print >> ERROR_LOG, "Error: Node name not found", v
                return None
            else:
                node_value_list.append(node_dict[v])
            # build relation map and attribute map for this node
            relation_dict = {}
            attribute_dict = {}
            if v in node_relation_dict1:
                for v1 in node_relation_dict1[v]:
                    assert AMR.inverted_label(v1[0]) is None
                    relation_dict[v1[1]] = v1[0]
            if v in node_relation_dict2:
                for v2 in node_relation_dict2[v]:
                    # if value is in quote, it is a constant value
                    # strip the quote and put it in attribute map
                    if v2[1][0] == "\"" and v2[1][-1] == "\"":
                        attribute_dict[v2[0]] = v2[1][1:-1]
                    # if value is a node name
                    elif v2[1] in node_dict:
                        inverted_label = AMR.inverted_label(v2[0])
                        if inverted_label is None:
                            relation_dict[v2[1]] = v2[0]
                        else:
                            delayed_inverted_edges.append((v2[1], v, inverted_label))
                    else:
                        attribute_dict[v2[0]] = v2[1]
            # each node has a relation map and attribute map
            relation_list.append(relation_dict)
            attribute_list.append(attribute_dict)
        # add TOP as an attribute. The attribute value is the top node value
        attribute_list[0]["TOP"] = node_value_list[0]
        for src, tgt, lab in delayed_inverted_edges:
            idx = node_name_list.index(src)
            relation_list[idx][tgt] = lab
        result_amr = AMR(node_name_list, node_value_list, relation_list, attribute_list)
        return result_amr

# test AMR parsing
# a unittest can also be used.
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print >> ERROR_LOG, "No file given"
        exit(1)
    amr_count = 1
    for line in open(sys.argv[1]):
        cur_line = line.strip()
        if cur_line == "" or cur_line.startswith("#"):
            continue
        print >> DEBUG_LOG, "AMR", amr_count
        current = AMR.parse_AMR_line(cur_line)
        current.output_amr()
        amr_count += 1
