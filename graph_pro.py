import os
import copy
import json
import random

from pycyclone.io import load_placement
import pycyclone
import pythunder
from pnr_graph import (
    RoutingResultGraph,
    construct_graph,
    TileType,
    RouteType,
    TileNode,
    RouteNode,
)

class seg:
    def __init__(self, width = 0, nodes = [], color = lambda:(0,0,0,0), net = None, edi = True, settled = True):
        self.width = width
        self.nodes = nodes
        self.color = color
        self.net = net
        self.edit = edi
        self.settled = settled
        self.picked = False
    
    def set_start(self, node, tile_id):
        self.start = node
        self.start_t = tile_id
    
    def set_end(self, node, tile_id):
        self.end = node
        self.end_t = tile_id

class th_node:
    def __init__(self, ty, id, width, nets = set()):
        self.ty = ty
        self.id = id
        self.width = width
        self.nets = nets

class rh_node:
    def __init__(self, loc, is_out, track, net_id):
        self.dir = dir
        self.is_out = is_out
        self.track = track
        self.net_id = net_id


class PathComponents:
    def __init__(
        self,
        glbs=0,
        sb_delay=[],
        sb_clk_delay=[],
        pes=0,
        mems=0,
        rmux=0,
        available_regs=0,
        parent=None,
    ):
        self.glbs = glbs
        self.sb_delay = sb_delay
        self.sb_clk_delay = sb_clk_delay
        self.pes = pes
        self.mems = mems
        self.rmux = rmux
        self.available_regs = available_regs
        self.parent = parent
        self.delays = json.load(
            open(os.path.dirname(os.path.realpath(__file__)) + "/sta_delays.json")
        )

    def get_total(self):
        total = 0
        total += self.glbs * self.delays["glb"]
        total += self.pes * self.delays["pe"]
        total += self.mems * self.delays["mem"]
        total += self.rmux * self.delays["rmux"]
        total += sum(self.sb_delay)
        total -= sum(self.sb_clk_delay)
        return total

    def print(self):
        print("\t\tGlbs:", self.glbs)
        print("\t\tPEs:", self.pes)
        print("\t\tMems:", self.mems)
        print("\t\tRmux:", self.rmux)
        print("\t\tSB delay:", sum(self.sb_delay), "ps")
        print("\t\tSB delay:", self.sb_delay, "ps")
        print("\t\tSB clk delay:", sum(self.sb_clk_delay), "ps")
        print("\t\tSB clk delay:", self.sb_clk_delay, "ps")


class Design:
    def __init__(self, netlist_f, place_f, route_f, id2name_f, graphs):
        self.netlist_f = netlist_f
        self.place_f = place_f
        self.route_f = route_f
        self.id2name_f = id2name_f
        self.graphs = graphs

        self.netlist, self.buses = pythunder.io.load_netlist(self.netlist_f)
        self.id2name = pythunder.io.load_id_to_name(self.netlist_f)
        self.place = load_placement(self.place_f)
        self.route = self.load_routing_result(self.route_f)

        self.pe_latency = 1
        self.io_cycles = 1
        self.sparse = False

        # self.nets contains the start and the end of each segment
        (self.result_graph, self.nets) = construct_graph(self.place, self.route, self.id2name, 
                                            self.netlist, self.pe_latency, 0, 
                                            self.io_cycles, self.sparse)
        self.seg_cnt = 0
        self.create_sg()
        self.create_tr_map()
        self.create_th()
        self.create_rh()

        self.free_net = dict()
        
        self.route_graph = self.load_graph(graphs)

    ##################### NEW CODE ####################
    def create_sg(self):
        self.sg = {}
        self.net_to_segs = {}
        for net_id in self.nets:
            # print(net_id, self.nets[net_id].node_s, self.nets[net_id].width)

            seg_num = len(self.nets[net_id].node_s)
            color = self.nets[net_id].color

            if net_id not in self.net_to_segs:
                self.net_to_segs[net_id] = []

            edi = True
            if seg_num > 1:
                edi = False
            # print("start ==================")
            
            for i in range(seg_num):
                node_st = self.nets[net_id].node_s[i]
                node_ed = self.nets[net_id].node_e[i]
                while node_st.route_type == RouteType.SB or node_st.route_type == RouteType.RMUX:
                    assert (len(self.result_graph.sources[node_st]) > 0)
                    node_st = self.result_graph.sources[node_st][0]
                nodes = []
                node_cur = node_ed
                # print(node_cur)
                # print(node_ed)
                # print(node_st)
                while node_cur != node_st:
                    nodes.append(node_cur)
                    assert (len(self.result_graph.sources[node_cur]) > 0)
                    node_cur = self.result_graph.sources[node_cur][0]
                nodes.append(node_cur)
                nodes.reverse()

                self.sg[self.seg_cnt] = seg(self.nets[net_id].width, nodes, color, net_id, edi)
                for t in self.result_graph.sources[node_st]:
                    if type(t) is TileNode:
                        start_tile = t
                        break
                # start_tile = self.result_graph.sources[node_st][0]
                self.sg[self.seg_cnt].set_start(node_st, start_tile.tile_id)

                for t in self.result_graph.sinks[node_ed]:
                    if type(t) is TileNode:
                        end_tile = t
                        break
                end_tile = self.result_graph.sinks[node_ed][0]
                self.sg[self.seg_cnt].set_end(node_ed, end_tile.tile_id)

                self.net_to_segs[net_id].append(self.seg_cnt) # a map from net_id to seg_ids
                self.seg_cnt += 1

    def create_tr_map(self):
        assert(len(self.sg) > 0)

        self.tr_map = {}

        for sg_id in self.sg:
            sg = self.sg[sg_id]
            # print(sg_id)
            node1 = sg.start
            node2 = sg.end

            if node1.route_type == RouteType.PORT:
                tile_id = self.result_graph.get_tile_at(
                    node1.x, node1.y, node1.port, None
                )
                # print(tile_id)
                if tile_id not in self.tr_map:
                    self.tr_map[tile_id] = []
                if node1 not in self.tr_map[tile_id]:
                    self.tr_map[tile_id].append(node1)
                    # print(tile_id)

            elif node1.route_type == RouteType.REG:
                reg_tile = self.result_graph.get_or_create_reg_at(
                    node1.x,
                    node1.y,
                    node1.track,
                    node1.bit_width,
                    node1.reg_name,
                )
                if reg_tile.tile_id not in self.tr_map:
                    self.tr_map[reg_tile.tile_id] = []
                if node1 not in self.tr_map[reg_tile.tile_id]:
                    self.tr_map[reg_tile.tile_id].append(node1)
                    # print(reg_tile.tile_id)

            if node2.route_type == RouteType.PORT:
                tile_id = self.result_graph.get_tile_at(
                    node2.x, node2.y, node2.port, None
                )
                if tile_id not in self.tr_map:
                    self.tr_map[tile_id] = []
                if node2 not in self.tr_map[tile_id]:
                    self.tr_map[tile_id].append(node2)
                    # print(tile_id)

            elif node2.route_type == RouteType.REG:
                reg_tile = self.result_graph.get_or_create_reg_at(
                    node2.x,
                    node2.y,
                    node2.track,
                    node2.bit_width,
                    node2.reg_name,
                )
                if reg_tile.tile_id not in self.tr_map:
                    self.tr_map[reg_tile.tile_id] = []
                if node2 not in self.tr_map[reg_tile.tile_id]:
                    self.tr_map[reg_tile.tile_id].append(node2)
                    # print(reg_tile.tile_id)
                                    

    def create_th(self):
        assert(len(self.tr_map) > 0)

        tiles = self.result_graph.get_tiles()
        self.blk_id_list = {tile.tile_id: tile for tile in tiles}
        self.th = dict()
        self.type_count = 0

        for blk_id, node in self.blk_id_list.items():

            assert(blk_id in self.tr_map)
            if (node.x, node.y) not in self.th:
                self.th[(node.x, node.y)] = []

            seg_l = self.tr_map[blk_id]
            width = seg_l[0].bit_width
            nets = set()
            for n in seg_l:
                nets.add(n.net_id)

            th_n = th_node(node.tile_type, blk_id, width, nets)
            self.th[(node.x, node.y)].append(th_n)
            self.type_count = max(len(self.th[(node.x, node.y)]), self.type_count)
    

    def create_rh(self):
        self.rh = dict()

        routes = self.result_graph.get_routes()
        for r in routes:
            if r.route_type == RouteType.SB:
                if (r.x, r.y) not in self.rh:
                    self.rh[(r.x, r.y)] = set()
                    
                self.rh[(r.x, r.y)].add(r)

    def get_dim(self):
        array_width = 0
        array_height = 0
        # for node in self.result_graph.nodes:
        #     array_width = max(array_width, node.x)
        #     array_height = max(array_height, node.y)
        # array_width += 1
        # array_height += 1
        while self.route_graph[1].has_tile(array_width, 0):
            array_width += 1
        while self.route_graph[1].has_tile(0, array_height):
            array_height += 1
        self.w = array_width
        self.h = array_height
        return (self.w, self.h)

    def get_route_info(self, seg_id):
        assert (seg_id in self.sg)
        segment = self.sg[seg_id]
        info = ""
        for r in segment.nodes:
            if r.route_type == RouteType.SB:
                info += "SB: loc " + str(r.x) + " " + str(r.y)+ " side " + str(r.side) + " track " + str(r.track)
                if r.io:
                    info += " out\n"
                else:
                    info += " in\n"
        return info

    ##################### OLD CODE ####################    

    def load_routing_result(self, filename):
        # copied from pnr python implementation
        with open(filename) as f:
            lines = f.readlines()

        routes = {}
        line_index = 0
        while line_index < len(lines):
            line = lines[line_index].strip()
            line_index += 1
            if line[:3] == "Net":
                tokens = line.split(" ")
                net_id = tokens[2]
                routes[net_id] = []
                num_seg = int(tokens[-1])
                for seg_index in range(num_seg):
                    segment = []
                    line = lines[line_index].strip()
                    line_index += 1
                    assert line[:len("Segment")] == "Segment"
                    tokens = line.split()
                    seg_size = int(tokens[-1])
                    for i in range(seg_size):
                        line = lines[line_index].strip()
                        line_index += 1
                        line = "".join([x for x in line if x not in ",()"])
                        tokens = line.split()
                        tokens = [int(x) if x.isdigit() else x for x in tokens]
                        segment.append(tokens)
                    routes[net_id].append(segment)
        return routes

    def load_graph(self, graph_files):
        graph_result = {}
        for graph_file in graph_files:
            bit_width = os.path.splitext(graph_file)[0]
            bit_width = int(os.path.basename(bit_width))
            graph = pycyclone.io.load_routing_graph(graph_file)
            graph_result[bit_width] = graph
        return graph_result
    
    def get_mem_tile_columns(self, graph):
        mem_column = 4
        for mem in graph.get_mems():
            if (mem.x + 1) % mem_column != 0:
                raise ValueError("MEM tile not at expected column, please update me")

        return mem_column
    
    def calc_sb_delay(self, graph, node, parent, comp, mem_column, sparse):
        # Need to associate each sb hop with these catagories:
        # mem2pe_clk
        # pe2mem_clk
        # north_input_clk
        # south_input_clk
        # pe2pe_west_east_input_clk
        # mem_endpoint_sb
        # pe_endpoint_sb

        if graph.sinks[node][0].route_type == RouteType.PORT:
            if graph.sinks[graph.sinks[node][0]]:
                if graph.sinks[graph.sinks[node][0]][0].tile_type == TileType.MEM:
                    comp.sb_delay.append(comp.delays[f"SB_IN_to_MEM"])
                else:
                    comp.sb_delay.append(comp.delays[f"SB_IN_to_PE"])

        if parent.io == 0:
            # Its the input to the SB
            if parent.side == 0:
                # Coming in from right
                source_x = parent.x + 1
            elif parent.side == 1:
                # Coming in from bottom
                source_x = parent.x
            elif parent.side == 2:
                # Coming in from left
                source_x = parent.x - 1
            else:
                # Coming in from top
                source_x = parent.x
            next_sb = node
            if next_sb.route_type != RouteType.SB:
                return
            assert next_sb.io == 1
            source_mem = False
            if (source_x + 1) % mem_column == 0:
                # Starting at mem column
                source_mem = True

            dest_mem = False
            if (next_sb.x + 1) % mem_column == 0:
                # Starting at mem column
                dest_mem = True

            if source_mem and not dest_mem:
                # mem2pe_clk
                comp.sb_clk_delay.append(comp.delays["mem2pe_clk"])
            elif not source_mem and dest_mem:
                # pe2mem_clk
                comp.sb_clk_delay.append(comp.delays["pe2mem_clk"])
            elif parent.side == 3:
                # north_input_clk
                comp.sb_clk_delay.append(comp.delays["north_input_clk"])
            elif parent.side == 1:
                # south_input_clk
                comp.sb_clk_delay.append(comp.delays["south_input_clk"])
            else:
                # pe2pe_west_east_input_clk
                comp.sb_clk_delay.append(comp.delays["pe2pe_west_east_input_clk"])

            side_to_dir = {0: "EAST", 1: "SOUTH", 2: "WEST", 3: "NORTH"}

            if not sparse:
                if (parent.x + 1) % mem_column == 0:
                    comp.sb_delay.append(
                        comp.delays[
                            f"MEM_B{parent.bit_width}_{side_to_dir[parent.side]}_{side_to_dir[next_sb.side]}"
                        ]
                    )
                else:
                    comp.sb_delay.append(
                        comp.delays[
                            f"PE_B{parent.bit_width}_{side_to_dir[parent.side]}_{side_to_dir[next_sb.side]}"
                        ]
                    )
            else:

                if (parent.x + 1) % mem_column == 0:
                    comp.sb_delay.append(
                        comp.delays[
                            f"MEM_B{parent.bit_width}_valid_{side_to_dir[parent.side]}_{side_to_dir[next_sb.side]}"
                        ]
                    )
                else:
                    comp.sb_delay.append(
                        comp.delays[
                            f"PE_B{parent.bit_width}_valid_{side_to_dir[parent.side]}_{side_to_dir[next_sb.side]}"
                        ]
                    )

                if (parent.x + 1) % mem_column == 0:
                    comp.sb_delay.append(
                        comp.delays[
                            f"MEM_B{parent.bit_width}_ready_{side_to_dir[next_sb.side]}_{side_to_dir[parent.side]}"
                        ]
                    )
                else:
                    comp.sb_delay.append(
                        comp.delays[
                            f"PE_B{parent.bit_width}_ready_{side_to_dir[next_sb.side]}_{side_to_dir[parent.side]}"
                        ]
                    )


    def sta(self):
        graph = self.result_graph
        mem_tile_column = self.get_mem_tile_columns(graph)
        nodes = graph.topological_sort()
        timing_info = {}

        for node in nodes:
            comp = PathComponents()
            components = [comp]

            if len(graph.sources[node]) == 0 and (
                node.tile_type == TileType.IO16 or node.tile_type == TileType.IO1
            ):
                if not node.input_port_break_path["output"]:
                    comp = PathComponents()
                    comp.glbs = 1
                    components = [comp]

            for parent in graph.sources[node]:
                comp = PathComponents()

                if parent in timing_info:
                    comp = copy.deepcopy(timing_info[parent])
                    comp.parent = parent

                if isinstance(node, TileNode):
                    if node.tile_type == TileType.PE:
                        comp.pes += 1
                    elif node.tile_type == TileType.MEM:
                        comp.mems += 1
                    elif node.tile_type == TileType.IO16 or node.tile_type == TileType.IO1:
                        comp.glbs += 1
                else:
                    if len(graph.sinks[node]) == 0:
                        continue
                    if node.route_type == RouteType.PORT and isinstance(
                        graph.sinks[node][0], TileNode
                    ):
                        if graph.sinks[node][0].input_port_break_path[node.port]:
                            comp = PathComponents()
                    elif node.route_type == RouteType.REG and isinstance(
                        graph.sinks[node][0], TileNode
                    ):
                        # if graph.sinks[node][0].input_port_break_path["reg"]:
                        comp = PathComponents()
                    elif node.route_type == RouteType.SB:
                        self.calc_sb_delay(
                            graph, node, parent, comp, mem_tile_column, graph.sparse
                        )
                    elif node.route_type == RouteType.RMUX:
                        if (
                            isinstance(parent, RouteNode)
                            and parent.route_type == RouteType.REG
                        ):
                            comp.rmux += 1
                        if parent.route_type != RouteType.REG:
                            comp.available_regs += 1

                components.append(comp)

            maxt = 0
            max_comp = components[0]
            for comp in components:
                if comp.get_total() > maxt:
                    maxt = comp.get_total()
                    max_comp = comp

            timing_info[node] = max_comp

        node_to_timing = {node: timing_info[node].get_total() for node in graph.nodes}
        node_to_timing = dict(
            sorted(
                reversed(list(node_to_timing.items())),
                key=lambda item: item[1],
                reverse=True,
            )
        )
        max_node = list(node_to_timing.keys())[0]
        max_delay = list(node_to_timing.values())[0]

        clock_speed = int(1.0e12 / max_delay / 1e6)

        print("\tMaximum clock frequency:", clock_speed, "MHz")
        print("\tCritical Path:", max_delay, "ps")
        print("\tCritical Path Info:")
        timing_info[max_node].print()

        max_node = list(node_to_timing.keys())[0]
        curr_node = max_node
        crit_path = []
        crit_path.append((curr_node, timing_info[curr_node].get_total()))
        crit_nodes = []
        while True:
            crit_nodes.append(curr_node)
            curr_node = timing_info[curr_node].parent
            crit_path.append((curr_node, timing_info[curr_node].get_total()))
            if timing_info[curr_node].parent is None:
                break

        crit_path.reverse()

        clk_info = "Maximum clock frequency: " + str(clock_speed) + " MHz\n"
        clk_info += "Critical Path: " + str(max_delay) + " ps\n"
        st_info = "start: " + str(crit_nodes[-1].x) + " " + str(crit_nodes[-1].y)
        if type(crit_nodes[-1]) is TileNode:
            st_info += " tile_id: " + str(crit_nodes[-1].tile_id)
        else:
            st_info += " width: " + str(crit_nodes[-1].bit_width)
        end_info = "end: " + str(crit_nodes[0].x) + " " + str(crit_nodes[0].y)
        if type(crit_nodes[0]) is TileNode:
            end_info += " tile_id: " + str(crit_nodes[0].tile_id)
        else:
            end_info += " width: " + str(crit_nodes[0].bit_width)
        return clk_info, st_info, end_info
        # return clock_speed, crit_path, crit_nodes
