# Old, do not use
import odgi
import pandas as pd
# import re
# import itertools as it

# In order to use this script, I need to run these two commands in the terminal:
# env LD_PRELOAD=libjemalloc.so.2 PYTHONPATH=lib python3 -c 'import odgi'
# export LD_PRELOAD=/lib/x86_64-linux-gnu/libjemalloc.so.2

gr = odgi.graph()
gr.load("yeast+edits.og")
path_names = []
node_ids = []
# steps = []
gr.for_each_path_handle(lambda p: path_names.append(gr.get_path_name(p)))
gr.for_each_path_handle(lambda p: node_ids.append(p))


def step_str(step):
    path_str = gr.get_path_name(gr.get_path_handle_of_step(step))
    dir_str = "+" if not gr.get_is_reverse(gr.get_handle_of_step(step)) else "-"
    return path_str + dir_str


all_path = []


def show_steps(handle):
    steps = []
    gr.for_each_step_on_handle(handle, lambda step: steps.append(step))
    all_path.append([
        gr.get_id(handle), " ".join([step_str(s) for s in steps])
    ])


# Everything above this line was borrowed and slightly adapted from the odgi tutorial on GitHub
gr.for_each_handle(show_steps)
# The list "all_path" contains a list in the form of [node_id, path_name]


def read_gaf(gaf_file_name):
    """
    This function takes a gaf file and returns a list of the nodes that reads in the
    file were mapped to.
    :param gaf_file_name:
    :return:
    """
    headers = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]
    gaf_file = pd.read_csv(gaf_file_name, sep="\t", header=None, names=headers)
    # gaf_file = gaf_file.dropna()
    # Using dropna() broke something? Will just have to deal with the missing values manually
    # further down the line.
    nodes = []
    for j in range(0, len(gaf_file)):
        # Collect the node IDs in the appropriate column
        nodes.append(gaf_file[6][j])
    print(f"nodes: {nodes[:10]}")
    return nodes


gaf_nodes = read_gaf("GE00001631-DOT_H11_S191_R2_001.subset.gaf")
# gaf_nodes = read_gaf("positive_control.gaf")

# print(gaf_nodes)
# specify headers: headers = ["q_name", "q_len", "q_start", "q_end", "rel_orient", "path", "path_len", "path_start",
# "path_end", "res_matches", "aln_block_len", "mapq"]

# have now figured out how the data works and how to manipulate it


def make_paths(path):
    """
    This function separates the names of the paths.
    In the input, the names are in one string, separated by spaces.
    :param path:
    :return:
    """
    my_list = []
    for i in path:
        my_list.append([i[0], i[1].split(" ")])
    return my_list


pan_path = make_paths(all_path)
print(f'pan_path: {pan_path[:10]}')


def separate_paths(paths):
    sep_path_names = []
    # Getting the names of the paths in a uniform format
    # This is necessary because the paths are now lists with 1 or more elements
    for x in paths:
        # print(x[0])
        if len(x[1]) > 1:
            for y in x[1]:
                if y not in sep_path_names:
                    sep_path_names.append(y)
        else:
            if x[1][0] not in sep_path_names:
                sep_path_names.append(x[1][0])
    return sep_path_names


# separate_paths(pan_path)
print(f'sep_path_names: {separate_paths(pan_path)[:10]}')

# print(sep_path_names)


def get_path_names(paths):
    """
    This function returns 2 lists, one with the path names for the reference
    and one for the homology arms.
    Need to write this function such that it would work for any example, not only
    this specific one. Could take the names from the original files, need to think
    about this.
    """
    h_arms = []
    ref_paths = []
    for path_name in paths:
        if path_name.startswith("h"):
            h_arms.append(path_name)
        else:
            ref_paths.append(path_name)
    return h_arms, ref_paths


hom_path, ref_path = get_path_names(separate_paths(pan_path))


def dict_test(path):
    """
    creates a dictionary with the node IDs as keys and the path names as values
    :param path:
    :return:
    """
    path_dict = {}
    for i in path:
        path_dict[i[0]] = i[1]

    return path_dict


node_dict = dict_test(pan_path)


# print(node_dict.get(52430))


def get_path(node):
    """
    Careful, this function returns a list, even if there is only one element.
    Use a length or type check when this function is called.
    :param node:
    :return:
    """
    return node_dict.get(node)


print(f'get_path: {get_path(3)}')


# I now have a dictionary of node_id: path_name that I can use to query whether a node (from the reads)
# is in a reference path, homology arm, or both.

# I now need to figure out how to make edges from the paths.

# exploring the data:


# eg = '<41699<41698<41697<41695<41694<41692<41691<41689<41688<41686<41684'
# print(eg.replace('<', ','))
#
# for i in eg.split('<'):
#     if len(i) > 1:
#         print(f'node: {i}, path: {get_path(int(i))}')


def find_legit_edges(reads):
    """
    This function takes a list of nodes to which reads mapped (from the GAF file)
    and picks out the relevant edges (only reads that map to more than one node, for now).
    The dictionary with the edges still needs to be created in a subsequent step.
    :param reads:
    :return:
    """
    con_nodes = []
    for x in reads:
        if x.count('<') > 1 or x.count('>') > 1:
            x = x.replace('<', '>')
            con_nodes.append(x[1:].split('>'))

    # print(len(con_nodes))
    return con_nodes


my_edges = find_legit_edges(gaf_nodes)
# for z in my_edges[146534]:
#     print(z)
#     print(f'my_path: {get_path(int(z))}')


def create_edge_dict(edges):
    """
    This function takes a list of edges and creates a dictionary with the tuple of 2 concurrent nodes
    as the key and the number of reads mapping to that edge as the value. Tuples are sorted such that
    they are in ascending order. This means that the first node in the tuple is always the smaller node,
    regardless of original orientation of the read.
    :param edges:
    :return:
    """
    edge_list = []
    edge_dict = {}
    for nodes in edges:
        # print(nodes)
        # careful with 'node' and 'nodes' here
        if len(nodes) == 2:
            temp = (int(nodes[0]), int(nodes[1]))
            temp = sorted(temp)
            edge_list.append(tuple(temp))
        elif len(nodes) > 2:
            for j in range(len(nodes)-1):
                # print(nodes[j])
                # temp = (int(nodes[i]), int(nodes[i+1]))
                temp = (int(nodes[j]), int(nodes[j+1]))
                temp = sorted(temp)
                edge_list.append(tuple(temp))
    # print(edge_list)

    for i in edge_list:
        if i in edge_dict:
            edge_dict[i] += 1
        else:
            edge_dict[i] = 1
    return edge_dict


read_edges = create_edge_dict(my_edges)
# print(create_edge_dict([['28813', '28812', '28810', '28808', '28807', '28806', '28805']]))
# print(len(create_edge_dict(my_edges)))

# I have now created the dictionary of edges and the number of reads that map to each edge.
# I now need to tally up the coverage counts of reference edges vs homology-only edges
# for EACH homology arm.

# print(ref_path)
# print(hom_path)


def reverse_dict_search(dictionary, value):
    """
    This function takes a dictionary and a value and returns a list of keys that have that value.
    :param dictionary:
    :param value:
    :return:
    """
    # return [k for k, v in dictionary.items() if v == value[n] for n in range(len(value))]
    key = []
    for k, v in dictionary.items():
        if value in v:
            key.append(k)
    return key


print(f'{hom_path[619]}: {reverse_dict_search(node_dict, hom_path[619])}')
# print(f'{ref_path[1]}: {reverse_dict_search(node_dict, [ref_path[1]])}')

# Next step: write a function that iterates over each edge in each path (ref and homology) and tallies the number
# of reads that map in each path.


def create_edges(path):
    """
    This function takes a list of nodes and creates a list of edges. This function will be called to
    create the edges of the paths so that they can be compared to the edges that had reads mapped to them.
    :param path:
    :return:
    """
    edges = []
    for j in range(len(path) - 1):
        temp = (int(path[j]), int(path[j + 1]))
        temp = sorted(temp)
        edges.append(tuple(temp))

    return edges


# Reminder of where what data is. The names of the paths are in ref_path and hom_path. The actual paths are called
# with reverse_dict_search(node_dict, [PATH[i]]). They then need to be made into edges with create_edges(). I can
# then compare the edges of the paths to the edges that had reads mapped to them.

def tally_reads_in_path(path, edge_dict):
    read_tally = 0
    graph_edges = create_edges(reverse_dict_search(node_dict, path))
    for edge in graph_edges:
        if edge in edge_dict:
            read_tally += edge_dict[edge]
    return read_tally


total = 0
for i in hom_path:
    print(f'{i}: {tally_reads_in_path(i, read_edges)}')
    total += tally_reads_in_path(i, read_edges)
print(total)

# All the messy code below this is just for testing.

# for i in range(1, len(hom_path)):
#     print(i)
#     print(create_edges(reverse_dict_search(node_dict, [hom_path[i]])))

print(create_edges(reverse_dict_search(node_dict, 'homology_arm_35412-')))
print(tally_reads_in_path(hom_path[619], read_edges))
#
print(reverse_dict_search(node_dict, 'homology_arm_35412-'))
# print(hom_path[812])
print(get_path(38902))
print(get_path(38903))
print(get_path(38905))
print(get_path(38906))
print(get_path(38908))
print(hom_path.index('homology_arm_35412-'))
# Try to verify that the paths and edges are being created in the right way. The fact that a tally is returned
# for the reference paths is a good sign that the paths are being created correctly. But why don't the homology
# paths have ANY edges that have reads mapped to them?
