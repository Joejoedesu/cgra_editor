import PIL
from PIL import Image, ImageQt, ImageDraw
import random

import pythunder
import pycyclone

from pnr_graph import (
    RoutingResultGraph,
    construct_graph,
    TileType,
    RouteType,
    TileNode,
    RouteNode,
)

# GRAPHICS DRAWING


GLOBAL_TILE_WIDTH = 200
GLOBAL_TILE_MARGIN = 40 #each side is 40 pixs
GLOBAL_TILE_WIDTH_INNER = GLOBAL_TILE_WIDTH - 2 * GLOBAL_TILE_MARGIN
GLOBAL_OFFSET_X = 20 #outer margin
GLOBAL_OFFSET_Y = 20
GLOBAL_NUM_TRACK = 5
GLOBAL_ARROW_DISTANCE = GLOBAL_TILE_WIDTH_INNER // (GLOBAL_NUM_TRACK * 2 + 1)

side_map = ["Right", "Bottom", "Left", "Top"]
io_map = ["IN", "OUT"]

# from tile_hist import TileType

class TILE_BLOCK:
    def __init__(self, loc, reg_img) -> None:
        self.loc = loc
        self.reg_img = reg_img

class IMG_DRAW:
    def __init__(self, dim) -> None:
        self.W_ = dim[0]
        self.H_ = dim[1]
        self.width_ = dim[0] * GLOBAL_TILE_WIDTH + 2 * GLOBAL_TILE_WIDTH
        self.height_ = dim[1] * GLOBAL_TILE_WIDTH + 2 * GLOBAL_TILE_WIDTH

        self.img_ = Image.new("RGB", (self.width_, self.height_), "White")
        self.draw_ = ImageDraw.Draw(self.img_)

        self.buf_ = []

        self.set_bg()#Image.new("RGB", (self.width_, self.height_), "White")

        self.i_ = 0
        self.j_ = 0



    def rt_Qt(self):
        return ImageQt.ImageQt(self.img_)
    

    def draw_arrow(
        self,
        draw,
        x,
        y,
        dir="UP",
        len=GLOBAL_TILE_MARGIN,
        color="Black",
        width=1,
        source_port=False,
        sink_port=False,
    ):
        arr_w = max(min(width, 7), 3)
        if dir == "UP":
            dx = 0
            dy = -1
            rx = arr_w
            ry = 0.7 * len
        elif dir == "DOWN":
            dx = 0
            dy = 1
            rx = arr_w
            ry = 0.7 * len
        elif dir == "LEFT":
            dx = -1
            dy = 0
            rx = 0.7 * len
            ry = arr_w
        elif dir == "RIGHT":
            dx = 1
            dy = 0
            rx = 0.7 * len
            ry = arr_w
        else:
            print("[Error] unsupported arrow direction")
            exit()
        xy = [(x, y), (x + dx * len * 0.8, y + dy * len * 0.8)]
        if dir == "UP" or dir == "DOWN":
            lxy = (x + dy * rx, y + dy * ry)
            rxy = (x + -dy * rx, y + dy * ry)
        else:
            lxy = (x + dx * rx, y + -dx * ry)
            rxy = (x + dx * rx, y + dx * ry)
        draw.line(xy=xy, fill=color, width=width)
        draw.polygon([(x + dx * len, y + dy * len), lxy, rxy], fill = color)

        pw = (GLOBAL_TILE_WIDTH - 2 * GLOBAL_TILE_MARGIN) / 40
        if source_port:
            xy = [(x - pw, y - pw), (x + pw, y - pw), (x + pw, y + pw), (x - pw, y + pw)]
            draw.polygon(xy=xy, fill="Green", outline="Black", width=1)

        if sink_port:
            x += dx * len
            y += dy * len
            xy = [(x - pw, y - pw), (x + pw, y - pw), (x + pw, y + pw), (x - pw, y + pw)]
            draw.polygon(xy=xy, fill="Green", outline="Black", width=1) #TODO same color

    def draw_sb_box(
        self,
        draw,
        x,
        y,
        dir,
        color,
        len=GLOBAL_TILE_MARGIN,
    ):
        x_c = x
        y_c = y
        if dir == "UP":
            y_c -= 0.5*len
        elif dir == "DOWN":
            y_c += 0.5*len
        elif dir == "LEFT":
            x_c -= 0.5*len
        elif dir == "RIGHT":
            x_c += 0.5*len
        else:
            print("[Error] unsupported arrow direction")
            exit()
        
        pw = (GLOBAL_TILE_WIDTH - 2 * GLOBAL_TILE_MARGIN) / 25
        xy = [(x_c - pw, y_c - pw), (x_c + pw, y_c - pw), (x_c + pw, y_c + pw), (x_c - pw, y_c + pw)]
        draw.polygon(xy=xy, fill=color, outline="Black", width=1)


    def draw_diagonal_arrow(
        self, draw, x, y, dir, x2, y2, dir2="UP", len=GLOBAL_TILE_MARGIN, color="Black", width=1
    ):
        # color = "Blue"
        if dir == "UP":
            dx = 0
            dy = -len
            rx = 0.09
            ry = 0.8
        elif dir == "DOWN":
            dx = 0
            dy = len
            rx = 0.09
            ry = 0.8
        elif dir == "LEFT":
            dx = -len
            dy = 0
            rx = 0.8
            ry = 0.09
        elif dir == "RIGHT":
            dx = len
            dy = 0
            rx = 0.8
            ry = 0.09
        else:
            print("[Error] unsupported arrow direction")
            exit()
        xy = [(x, y), (x + dx, y + dy)]

        if dir2 == "UP":
            dx = 0
            dy = -len
            rx = 0.09
            ry = 0.8
        elif dir2 == "DOWN":
            dx = 0
            dy = len
            rx = 0.09
            ry = 0.8
        elif dir2 == "LEFT":
            dx = -len
            dy = 0
            rx = 0.8
            ry = 0.09
        elif dir2 == "RIGHT":
            dx = len
            dy = 0
            rx = 0.8
            ry = 0.09
        else:
            print("[Error] unsupported arrow direction")
            exit()
        xy2 = [(x2, y2), (x2 + dx, y2 + dy)]
        new_xy = [xy[0], xy2[1]]
        draw.line(xy=new_xy, fill=color, width=width)


    def draw_arrow_between_sb(self, draw, node, node2, color="Black", width=1):
        tile_x = node.x
        tile_y = node.y
        side = side_map[node.side]
        io = io_map[node.io]
        track_id = node.track

        tile_x2 = node2.x
        tile_y2 = node2.y
        side2 = side_map[node2.side]
        io2 = io_map[node2.io]
        track_id2 = node2.track

        if tile_x != tile_x2 or tile_y != tile_y2:
            return
        
        if side == "Top":
            if io == "IN":
                dir = "DOWN"
                x = (
                    GLOBAL_OFFSET_X
                    + GLOBAL_TILE_MARGIN
                    + tile_x * GLOBAL_TILE_WIDTH
                    + (track_id + 1) * GLOBAL_ARROW_DISTANCE
                )
                y = GLOBAL_OFFSET_Y + tile_y * GLOBAL_TILE_WIDTH
            elif io == "OUT":
                dir = "UP"
                x = (
                    GLOBAL_OFFSET_X
                    + GLOBAL_TILE_MARGIN
                    + tile_x * GLOBAL_TILE_WIDTH
                    + (track_id + 1 + GLOBAL_NUM_TRACK) * GLOBAL_ARROW_DISTANCE
                )
                y = GLOBAL_OFFSET_Y + GLOBAL_TILE_MARGIN + tile_y * GLOBAL_TILE_WIDTH
        elif side == "Right":
            if io == "IN":
                dir = "LEFT"
                x = GLOBAL_OFFSET_X + tile_x * GLOBAL_TILE_WIDTH + GLOBAL_TILE_WIDTH
                y = (
                    GLOBAL_OFFSET_Y
                    + GLOBAL_TILE_MARGIN
                    + tile_y * GLOBAL_TILE_WIDTH
                    + (track_id + 1) * GLOBAL_ARROW_DISTANCE
                )
            elif io == "OUT":
                dir = "RIGHT"
                x = (
                    GLOBAL_OFFSET_X
                    + tile_x * GLOBAL_TILE_WIDTH
                    + GLOBAL_TILE_WIDTH
                    - GLOBAL_TILE_MARGIN
                )
                y = (
                    GLOBAL_OFFSET_Y
                    + GLOBAL_TILE_MARGIN
                    + tile_y * GLOBAL_TILE_WIDTH
                    + (track_id + 1 + GLOBAL_NUM_TRACK) * GLOBAL_ARROW_DISTANCE
                )
        elif side == "Bottom":
            if io == "IN":
                dir = "UP"
                x = (
                    GLOBAL_OFFSET_X
                    + GLOBAL_TILE_MARGIN
                    + tile_x * GLOBAL_TILE_WIDTH
                    + (track_id + 1 + GLOBAL_NUM_TRACK) * GLOBAL_ARROW_DISTANCE
                )
                y = GLOBAL_OFFSET_Y + tile_y * GLOBAL_TILE_WIDTH + GLOBAL_TILE_WIDTH
            elif io == "OUT":
                dir = "DOWN"
                x = (
                    GLOBAL_OFFSET_X
                    + GLOBAL_TILE_MARGIN
                    + tile_x * GLOBAL_TILE_WIDTH
                    + (track_id + 1) * GLOBAL_ARROW_DISTANCE
                )
                y = (
                    GLOBAL_OFFSET_Y
                    + tile_y * GLOBAL_TILE_WIDTH
                    + GLOBAL_TILE_WIDTH
                    - GLOBAL_TILE_MARGIN
                )
        elif side == "Left":
            if io == "IN":
                dir = "RIGHT"
                x = GLOBAL_OFFSET_X + tile_x * GLOBAL_TILE_WIDTH
                y = (
                    GLOBAL_OFFSET_Y
                    + GLOBAL_TILE_MARGIN
                    + tile_y * GLOBAL_TILE_WIDTH
                    + (track_id + 1 + GLOBAL_NUM_TRACK) * GLOBAL_ARROW_DISTANCE
                )
            elif io == "OUT":
                dir = "LEFT"
                x = GLOBAL_OFFSET_X + tile_x * GLOBAL_TILE_WIDTH + GLOBAL_TILE_MARGIN
                y = (
                    GLOBAL_OFFSET_Y
                    + GLOBAL_TILE_MARGIN
                    + tile_y * GLOBAL_TILE_WIDTH
                    + (track_id + 1) * GLOBAL_ARROW_DISTANCE
                )

        if side2 == "Top":
            if io2 == "IN":
                dir2 = "DOWN"
                x2 = (
                    GLOBAL_OFFSET_X
                    + GLOBAL_TILE_MARGIN
                    + tile_x2 * GLOBAL_TILE_WIDTH
                    + (track_id2 + 1) * GLOBAL_ARROW_DISTANCE
                )
                y2 = GLOBAL_OFFSET_Y + tile_y2 * GLOBAL_TILE_WIDTH
            elif io2 == "OUT":
                dir2 = "UP"
                x2 = (
                    GLOBAL_OFFSET_X
                    + GLOBAL_TILE_MARGIN
                    + tile_x2 * GLOBAL_TILE_WIDTH
                    + (track_id2 + 1 + GLOBAL_NUM_TRACK) * GLOBAL_ARROW_DISTANCE
                )
                y2 = GLOBAL_OFFSET_Y + GLOBAL_TILE_MARGIN + tile_y2 * GLOBAL_TILE_WIDTH
        elif side2 == "Right":
            if io2 == "IN":
                dir2 = "LEFT"
                x2 = GLOBAL_OFFSET_X + tile_x2 * GLOBAL_TILE_WIDTH + GLOBAL_TILE_WIDTH
                y2 = (
                    GLOBAL_OFFSET_Y
                    + GLOBAL_TILE_MARGIN
                    + tile_y2 * GLOBAL_TILE_WIDTH
                    + (track_id2 + 1) * GLOBAL_ARROW_DISTANCE
                )
            elif io2 == "OUT":
                dir2 = "RIGHT"
                x2 = (
                    GLOBAL_OFFSET_X
                    + tile_x2 * GLOBAL_TILE_WIDTH
                    + GLOBAL_TILE_WIDTH
                    - GLOBAL_TILE_MARGIN
                )
                y2 = (
                    GLOBAL_OFFSET_Y
                    + GLOBAL_TILE_MARGIN
                    + tile_y2 * GLOBAL_TILE_WIDTH
                    + (track_id2 + 1 + GLOBAL_NUM_TRACK) * GLOBAL_ARROW_DISTANCE
                )
        elif side2 == "Bottom":
            if io2 == "IN":
                dir2 = "UP"
                x2 = (
                    GLOBAL_OFFSET_X
                    + GLOBAL_TILE_MARGIN
                    + tile_x2 * GLOBAL_TILE_WIDTH
                    + (track_id2 + 1 + GLOBAL_NUM_TRACK) * GLOBAL_ARROW_DISTANCE
                )
                y2 = GLOBAL_OFFSET_Y + tile_y2 * GLOBAL_TILE_WIDTH + GLOBAL_TILE_WIDTH
            elif io2 == "OUT":
                dir2 = "DOWN"
                x2 = (
                    GLOBAL_OFFSET_X
                    + GLOBAL_TILE_MARGIN
                    + tile_x2 * GLOBAL_TILE_WIDTH
                    + (track_id2 + 1) * GLOBAL_ARROW_DISTANCE
                )
                y2 = (
                    GLOBAL_OFFSET_Y
                    + tile_y2 * GLOBAL_TILE_WIDTH
                    + GLOBAL_TILE_WIDTH
                    - GLOBAL_TILE_MARGIN
                )
        elif side2 == "Left":
            if io2 == "IN":
                dir2 = "RIGHT"
                x2 = GLOBAL_OFFSET_X + tile_x2 * GLOBAL_TILE_WIDTH
                y2 = (
                    GLOBAL_OFFSET_Y
                    + GLOBAL_TILE_MARGIN
                    + tile_y2 * GLOBAL_TILE_WIDTH
                    + (track_id2 + 1 + GLOBAL_NUM_TRACK) * GLOBAL_ARROW_DISTANCE
                )
            elif io2 == "OUT":
                dir2 = "LEFT"
                x2 = GLOBAL_OFFSET_X + tile_x2 * GLOBAL_TILE_WIDTH + GLOBAL_TILE_MARGIN
                y2 = (
                    GLOBAL_OFFSET_Y
                    + GLOBAL_TILE_MARGIN
                    + tile_y2 * GLOBAL_TILE_WIDTH
                    + (track_id2 + 1) * GLOBAL_ARROW_DISTANCE
                )
        self.draw_diagonal_arrow(
            draw=draw, x=x, y=y, dir=dir, x2=x2, y2=y2, dir2=dir2, color=color, width=width
        )


    def draw_arrow_on_tile(
        self,
        draw,
        tile_x,
        tile_y,
        side,
        io,
        track_id,
        color="Black",
        width=1,
        source_port=False,
        sink_port=False,
    ):

        if side == "Top":
            if io == "IN":
                dir = "DOWN"
                x = (
                    GLOBAL_OFFSET_X
                    + GLOBAL_TILE_MARGIN
                    + tile_x * GLOBAL_TILE_WIDTH
                    + (track_id + 1) * GLOBAL_ARROW_DISTANCE
                )
                y = GLOBAL_OFFSET_Y + tile_y * GLOBAL_TILE_WIDTH
            elif io == "OUT":
                dir = "UP"
                x = (
                    GLOBAL_OFFSET_X
                    + GLOBAL_TILE_MARGIN
                    + tile_x * GLOBAL_TILE_WIDTH
                    + (track_id + 1 + GLOBAL_NUM_TRACK) * GLOBAL_ARROW_DISTANCE
                )
                y = GLOBAL_OFFSET_Y + GLOBAL_TILE_MARGIN + tile_y * GLOBAL_TILE_WIDTH
        elif side == "Right":
            if io == "IN":
                dir = "LEFT"
                x = GLOBAL_OFFSET_X + tile_x * GLOBAL_TILE_WIDTH + GLOBAL_TILE_WIDTH
                y = (
                    GLOBAL_OFFSET_Y
                    + GLOBAL_TILE_MARGIN
                    + tile_y * GLOBAL_TILE_WIDTH
                    + (track_id + 1) * GLOBAL_ARROW_DISTANCE
                )
            elif io == "OUT":
                dir = "RIGHT"
                x = (
                    GLOBAL_OFFSET_X
                    + tile_x * GLOBAL_TILE_WIDTH
                    + GLOBAL_TILE_WIDTH
                    - GLOBAL_TILE_MARGIN
                )
                y = (
                    GLOBAL_OFFSET_Y
                    + GLOBAL_TILE_MARGIN
                    + tile_y * GLOBAL_TILE_WIDTH
                    + (track_id + 1 + GLOBAL_NUM_TRACK) * GLOBAL_ARROW_DISTANCE
                )
        elif side == "Bottom":
            if io == "IN":
                dir = "UP"
                x = (
                    GLOBAL_OFFSET_X
                    + GLOBAL_TILE_MARGIN
                    + tile_x * GLOBAL_TILE_WIDTH
                    + (track_id + 1 + GLOBAL_NUM_TRACK) * GLOBAL_ARROW_DISTANCE
                )
                y = GLOBAL_OFFSET_Y + tile_y * GLOBAL_TILE_WIDTH + GLOBAL_TILE_WIDTH
            elif io == "OUT":
                dir = "DOWN"
                x = (
                    GLOBAL_OFFSET_X
                    + GLOBAL_TILE_MARGIN
                    + tile_x * GLOBAL_TILE_WIDTH
                    + (track_id + 1) * GLOBAL_ARROW_DISTANCE
                )
                y = (
                    GLOBAL_OFFSET_Y
                    + tile_y * GLOBAL_TILE_WIDTH
                    + GLOBAL_TILE_WIDTH
                    - GLOBAL_TILE_MARGIN
                )
        elif side == "Left":
            if io == "IN":
                dir = "RIGHT"
                x = GLOBAL_OFFSET_X + tile_x * GLOBAL_TILE_WIDTH
                y = (
                    GLOBAL_OFFSET_Y
                    + GLOBAL_TILE_MARGIN
                    + tile_y * GLOBAL_TILE_WIDTH
                    + (track_id + 1 + GLOBAL_NUM_TRACK) * GLOBAL_ARROW_DISTANCE
                )
            elif io == "OUT":
                dir = "LEFT"
                x = GLOBAL_OFFSET_X + tile_x * GLOBAL_TILE_WIDTH + GLOBAL_TILE_MARGIN
                y = (
                    GLOBAL_OFFSET_Y
                    + GLOBAL_TILE_MARGIN
                    + tile_y * GLOBAL_TILE_WIDTH
                    + (track_id + 1) * GLOBAL_ARROW_DISTANCE
                )
        self.draw_arrow(
            draw=draw,
            x=x,
            y=y,
            dir=dir,
            color=color,
            width=width,
            source_port=source_port,
            sink_port=sink_port,
        )
    
    def find_last_sb(self, routing_result_graph, node):
        found_sb = False
        found_port = False

        curr_node = node
        while not found_sb and not found_port:
            assert len(routing_result_graph.sources[curr_node]) == 1, (
                curr_node,
                routing_result_graph.sources[curr_node],
            )

            source = routing_result_graph.sources[curr_node][0]

            if isinstance(source, TileNode) or source.route_type == RouteType.PORT:
                found_port = True
            elif source.route_type == RouteType.SB:
                found_sb = True

            curr_node = source

        if found_sb:
            return curr_node
        else:
            return None
        

    def draw_reg_on_tile(self, draw, tile_x, tile_y, reg_name, track_id):

        if "NORTH" in reg_name:
            x = (
                GLOBAL_OFFSET_X
                + GLOBAL_TILE_MARGIN
                + tile_x * GLOBAL_TILE_WIDTH
                + (track_id + 1 + GLOBAL_NUM_TRACK) * GLOBAL_ARROW_DISTANCE
            )
            y = GLOBAL_OFFSET_Y + tile_y * GLOBAL_TILE_WIDTH
        elif "EAST" in reg_name:
            x = GLOBAL_OFFSET_X + tile_x * GLOBAL_TILE_WIDTH + GLOBAL_TILE_WIDTH
            y = (
                GLOBAL_OFFSET_Y
                + GLOBAL_TILE_MARGIN
                + tile_y * GLOBAL_TILE_WIDTH
                + (track_id + 1 + GLOBAL_NUM_TRACK) * GLOBAL_ARROW_DISTANCE
            )
        elif "SOUTH" in reg_name:
            x = (
                GLOBAL_OFFSET_X
                + GLOBAL_TILE_MARGIN
                + tile_x * GLOBAL_TILE_WIDTH
                + (track_id + 1) * GLOBAL_ARROW_DISTANCE
            )
            y = GLOBAL_OFFSET_Y + tile_y * GLOBAL_TILE_WIDTH + GLOBAL_TILE_WIDTH
        elif "WEST" in reg_name:
            x = GLOBAL_OFFSET_X + tile_x * GLOBAL_TILE_WIDTH
            y = (
                GLOBAL_OFFSET_Y
                + GLOBAL_TILE_MARGIN
                + tile_y * GLOBAL_TILE_WIDTH
                + (track_id + 1) * GLOBAL_ARROW_DISTANCE
            )

        pw = (GLOBAL_TILE_WIDTH - 2 * GLOBAL_TILE_MARGIN) / 20
        xy = [(x - pw, y - pw), (x + pw, y - pw), (x + pw, y + pw), (x - pw, y + pw)]
        draw.polygon(xy=xy, fill="Red", outline="Black", width=1)

    def create_tile(self, draw, x, y, color_tile = "lightgrey", w=GLOBAL_TILE_WIDTH, width=2):
        color_line = "Black"
        pr = 0.4
        px = GLOBAL_OFFSET_X + x * GLOBAL_TILE_WIDTH + GLOBAL_TILE_MARGIN
        py = GLOBAL_OFFSET_Y + y * GLOBAL_TILE_WIDTH + GLOBAL_TILE_MARGIN
        pw = GLOBAL_TILE_WIDTH - 2 * GLOBAL_TILE_MARGIN
        xy = [(px, py), (px + pw, py), (px + pw, py + pw), (px, py + pw)]
        txy = (px + int(pw * pr), py + int(pw * 0.4))
        t2xy = (px + int(pw * pr), py + int(pw * 0.6))
        draw.polygon(xy=xy, fill=color_tile, outline=color_line, width=width)

    def add_loc(self, draw, x, y):
        px = GLOBAL_OFFSET_X + x * GLOBAL_TILE_WIDTH + GLOBAL_TILE_MARGIN
        py = GLOBAL_OFFSET_Y + y * GLOBAL_TILE_WIDTH + GLOBAL_TILE_MARGIN
        pw = GLOBAL_TILE_WIDTH - 2 * GLOBAL_TILE_MARGIN
        cxy = (px + int(pw * 0.05), py + int(pw * 0.05))
        draw.text(xy=cxy, text=f"({x},{y})", fill="Black")
    
    def draw_all_tiles(self, draw, img):
        tmp = Image.new("RGB", (GLOBAL_TILE_WIDTH + 2 * GLOBAL_OFFSET_X, 
            GLOBAL_TILE_WIDTH * 3 + 2 * GLOBAL_OFFSET_Y), "White")
        draw1 = ImageDraw.Draw(tmp)
        #io
        self.create_tile(draw = draw1, x=0, y=0, color_tile = "lightgreen")
        box1 = self.create_box(0, 0)
        region1 = tmp.crop(box1)

        #pe
        self.create_tile(draw = draw1, x=0, y=1, color_tile = "lightblue")
        
        for i in range(4):
            side = pycyclone.SwitchBoxSide(i)
            for io in ["IN", "OUT"]:
                for i in range(5):
                    self.draw_arrow_on_tile(
                        draw1,
                        tile_x=0,
                        tile_y=1,
                        side=side.name,
                        io=io,
                        track_id=i % GLOBAL_NUM_TRACK,
                    )
        box2 = self.create_box(0, 1)
        region2 = tmp.crop(box2)

        #mem
        self.create_tile(draw = draw1, x=0, y=2, color_tile = "lightyellow")

        for i in range(4):
            side = pycyclone.SwitchBoxSide(i)
            for io in ["IN", "OUT"]:
                for i in range(GLOBAL_NUM_TRACK):
                    self.draw_arrow_on_tile(
                        draw1,
                        tile_x=0,
                        tile_y=2,
                        side=side.name,
                        io=io,
                        track_id=i,
                    )
        box3 = self.create_box(0, 2)
        region3 = tmp.crop(box3)


        for x in range(self.W_):
            for y in range(self.H_):
                box = self.create_box(x,y)
                if y == 0:
                    img.paste(region1, box)
                elif x % 4 == 3:
                    img.paste(region3, box)
                else:
                    img.paste(region2, box)
                self.add_loc(draw = draw, x = x, y = y)

        # return self.rt_Qt()


    def create_tile_types(self, width = 2):
        temp = dict()
        w = GLOBAL_TILE_WIDTH - 2 * GLOBAL_TILE_MARGIN
        sx = 0
        ex = w
        dy = w//self.count
        w = GLOBAL_TILE_WIDTH - 2 * GLOBAL_TILE_MARGIN
        ex = w
        dy = w//self.count
        tmp = Image.new("RGB", (ex, dy * 10), "White")

        draw = ImageDraw.Draw(tmp)
        ind = 0
        for tile_type in TileType:
            if tile_type == TileType.PE:
                color_tile = "dodgerblue"
                color_line = "Black"
                pr = 0.4
            elif tile_type == TileType.MEM:
                color_tile = "gold"
                color_line = "Black"
                pr = 0.4
            elif tile_type == TileType.POND:
                color_tile = "Khaki"
                color_line = "Black"
                pr = 0.4
            elif tile_type == TileType.IO1 or tile_type == TileType.IO16:
                color_tile = "palegreen"
                color_line = "Black"
                pr = 0.4
            elif tile_type == TileType.REG:
                color_tile = "salmon"
                color_line = "Black"
                pr = 0.4
            else:
                color_tile = "lightgrey"
                color_line = "Black"
                pr = 0.4
            sy = ind * dy
            ey = (ind + 1) * dy
            xy = ((sx, sy), (sx, ey), (ex, ey), (ex, sy))
            draw.polygon(xy=xy, fill=color_tile, outline=color_line, width=width)
            box = (sx, sy, ex, ey)
            temp[tile_type] = tmp.crop(box)

        return temp
            

    def draw_used_tiles(self, width=2):
        for loc in self.tile_hist:
            (x, y) = loc
            cont = self.tile_hist[loc]
            w = GLOBAL_TILE_WIDTH - 2 * GLOBAL_TILE_MARGIN
            sx = GLOBAL_OFFSET_X + x * GLOBAL_TILE_WIDTH + GLOBAL_TILE_MARGIN
            ex = sx + w
            by = GLOBAL_OFFSET_Y + y * GLOBAL_TILE_WIDTH + GLOBAL_TILE_MARGIN

            dy = w//self.count
            for i in range(len(cont)):
                tile_type = cont[i].ty
                tile_id = cont[i].id
                sy = by + i * dy
                ey = by + (i+1)*dy
                box = (sx, sy, ex, ey)
                self.img_.paste(self.tmp[tile_type], box)

    def label_used_tiles(self, width=2):
        for loc in self.tile_hist:
            (x, y) = loc
            cont = self.tile_hist[loc]
            w = GLOBAL_TILE_WIDTH - 2 * GLOBAL_TILE_MARGIN
            sx = GLOBAL_OFFSET_X + x * GLOBAL_TILE_WIDTH + GLOBAL_TILE_MARGIN
            ex = sx + w
            by = GLOBAL_OFFSET_Y + y * GLOBAL_TILE_WIDTH + GLOBAL_TILE_MARGIN

            dy = w//self.count
            for i in range(len(cont)):
                tile_type = cont[i].ty
                tile_id = cont[i].id
                sy = by + i * dy
                ey = by + (i+1)*dy

                txy1 = (sx + int(w * 0.3), by + int(dy * 0.4) + i * dy)
                txy2 = (sx + int(w * 0.6), by + int(dy * 0.4) + i * dy)
                self.draw_.text(xy=txy1, text=str(tile_type).split("TileType.")[1], fill="Black")
                self.draw_.text(xy=txy2, text=tile_id, fill="Black")
            cxy = (sx + int(w * 0.05), by + int(w * 0.05))
            self.draw_.text(xy=cxy, text=f"({x},{y})", fill="Black")

    def draw_used_routes_n(self, sgs, width, routing_result_graph):
        for sg_id in sgs:
            sg = sgs[sg_id]
            if sg.width == width and (sg.settled or sg.picked):
                color = sg.color

                if sg.picked:
                    color = (255, 0, 0, 255)

                for node in sg.nodes:
                    if node.route_type == RouteType.SB:

                        source_port = False
                        sink_port = False
                        ind = sg.nodes.index(node)
                        if ind == 1:
                            source_port = True
                        
                        if ind == len(sg.nodes) - 2:
                            sink_port = True

                        self.draw_arrow_on_tile(
                            self.draw_,
                            node.x,
                            node.y,
                            side_map[node.side],
                            io_map[node.io],
                            node.track,
                            color=color,
                            width=6,
                            source_port=source_port,
                            sink_port=sink_port,
                        )

                        node_pre = sg.nodes[ind - 1]
                        if node_pre.route_type == RouteType.SB:
                            if node_pre.x == node.x and node_pre.y == node.y:
                                self.draw_arrow_between_sb(self.draw_, node, node_pre, color=color, width=6)
                        # last_sb = self.find_last_sb(routing_result_graph, node)

                        # if last_sb:
                        #     self.draw_arrow_between_sb(
                        #         self.draw_, node, last_sb, color=color, width=6
                        #     )

                    elif node.route_type == RouteType.REG and node.bit_width == width:
                        self.draw_reg_on_tile(self.draw_, node.x, node.y, node.reg_name, node.track)
            elif sg.width == width and not sg.settled:
                for node in sg.nodes:
                    if node.route_type == RouteType.REG and node.bit_width == width:
                        self.draw_reg_on_tile(self.draw_, node.x, node.y, node.reg_name, node.track)

    def draw_used_routes(self, routing_result_graph, width):
        color = lambda: (
            random.randint(64, 128),
            random.randint(64, 255),
            random.randint(64, 255),
            255,
        )
        net_colors = {}

        for node in routing_result_graph.get_routes():
            if node.route_type == RouteType.SB and node.bit_width == width:
                if node.net_id not in net_colors:
                    net_colors[node.net_id] = color()

                source_port = False
                sink_port = False
                for source in routing_result_graph.sources[node]:
                    if (
                        isinstance(source, RouteNode)
                        and source.route_type == RouteType.PORT
                    ):
                        source_port = True
                for sink in routing_result_graph.sinks[node]:
                    if isinstance(sink, RouteNode) and sink.route_type == RouteType.PORT:
                        sink_port = True

                self.draw_arrow_on_tile(
                    self.draw_,
                    node.x,
                    node.y,
                    side_map[node.side],
                    io_map[node.io],
                    node.track,
                    color=net_colors[node.net_id],
                    width=6,
                    source_port=source_port,
                    sink_port=sink_port,
                )

                last_sb = self.find_last_sb(routing_result_graph, node)

                if last_sb:
                    self.draw_arrow_between_sb(
                        self.draw_, node, last_sb, color=net_colors[node.net_id], width=6
                    )
            elif node.route_type == RouteType.REG and node.bit_width == width:
                self.draw_reg_on_tile(self.draw_, node.x, node.y, node.reg_name, node.track)

    ################### NEW CODE ######################
    def create_box(self, x, y):
        return (int(GLOBAL_OFFSET_X + GLOBAL_TILE_WIDTH * x), int(GLOBAL_TILE_WIDTH * y + GLOBAL_OFFSET_Y), 
                int(GLOBAL_TILE_WIDTH * (x + 1) + GLOBAL_OFFSET_X), int(GLOBAL_TILE_WIDTH * (y + 1) + GLOBAL_OFFSET_Y))

    def create_rect(self, x, y):
        px = GLOBAL_OFFSET_X + x * GLOBAL_TILE_WIDTH
        py = GLOBAL_OFFSET_Y + y * GLOBAL_TILE_WIDTH
        pw = GLOBAL_TILE_WIDTH
        xy = [(px, py), (px + pw, py), (px + pw, py + pw), (px, py + pw)]
        return xy

    def tile_pickup(self, tile):
        box = self.create_box(tile[0], tile[1])
        reg = self.img_.crop(box)
        self.buf_.append(TILE_BLOCK(tile, reg))

    def tile_putback(self, tb):
        box = self.create_box(tb.loc[0], tb.loc[1])
        self.img_.paste(tb.reg_img, box)

    def restore_buf(self):
        for i in range(len(self.buf_) - 1, -1, -1):
            self.tile_putback(self.buf_[i])

    def high_light_tile(self, tile):
        r = 0.2
        wid = 8
        d = GLOBAL_TILE_WIDTH_INNER * 0.2
        x = tile[0]
        y = tile[1]
        x1 = GLOBAL_OFFSET_X + GLOBAL_TILE_WIDTH * x + GLOBAL_TILE_MARGIN
        x2 = x1 + GLOBAL_TILE_WIDTH_INNER
        y1 = GLOBAL_OFFSET_Y + GLOBAL_TILE_WIDTH * y + GLOBAL_TILE_MARGIN
        y2 = y1 + GLOBAL_TILE_WIDTH_INNER
        self.draw_.line(xy=[(x1, y1), (x1 + d, y1)], fill="red", width=wid)
        self.draw_.line(xy=[(x1, y1), (x1, y1 + d)], fill="red", width=wid)
        self.draw_.line(xy=[(x1, y2), (x1 + d, y2)], fill="red", width=wid)
        self.draw_.line(xy=[(x1, y2), (x1, y2 - d)], fill="red", width=wid)
        self.draw_.line(xy=[(x2, y1), (x2 - d, y1)], fill="red", width=wid)
        self.draw_.line(xy=[(x2, y1), (x2, y1 + d)], fill="red", width=wid)
        self.draw_.line(xy=[(x2, y2), (x2 - d, y2)], fill="red", width=wid)
        self.draw_.line(xy=[(x2, y2), (x2, y2 - d)], fill="red", width=wid)

    def set_bg(self):
        bg_img = Image.new("RGB", (self.width_, self.height_), "White")
        bg_draw = ImageDraw.Draw(bg_img)
        self.draw_all_tiles(bg_draw, bg_img)
        self.ent_box = (0, 0, self.width_, self.height_)
        self.bg_ = bg_img.crop(self.ent_box)
        self.load_background()
        

    def load_background(self):
        self.img_.paste(self.bg_, self.ent_box)
        self.buf_.clear()


    def draw_simple(self, i = 0, j = 0):
        color_tile = "lightgrey"
        color_line = "Black"
        pr = 0.4
        px = 0
        py = 0
        pw = GLOBAL_TILE_WIDTH
        xy = [(px, py), (px + pw, py), (px + pw, py + pw), (px, py + pw)]
        txy = (px + int(pw * pr), py + int(pw * 0.4))
        t2xy = (px + int(pw * pr), py + int(pw * 0.6))
        self.draw_.polygon(xy=xy, fill=color_tile, outline=color_line, width=2)
        return self.rt_Qt()

    def dosth(self, tile):
        if tile[0] < 0:
            return
        else:
            self.draw_simple(tile[0], tile[1])
    

    def hight_light_route(self, segs):
        for sg in segs:
            if sg.settled:
                color = (200, 200, 0, 255)

                for node in sg.nodes:
                    if node.route_type == RouteType.SB:

                        source_port = False
                        sink_port = False
                        ind = sg.nodes.index(node)
                        if ind == 1:
                            source_port = True
                        
                        if ind == len(sg.nodes) - 2:
                            sink_port = True

                        self.tile_pickup((node.x, node.y))

                        self.draw_arrow_on_tile(
                            self.draw_,
                            node.x,
                            node.y,
                            side_map[node.side],
                            io_map[node.io],
                            node.track,
                            color=color,
                            width=6,
                            source_port=source_port,
                            sink_port=sink_port,
                        )

                        node_pre = sg.nodes[ind - 1]
                        if node_pre.route_type == RouteType.SB:
                            if node_pre.x == node.x and node_pre.y == node.y:
                                self.draw_arrow_between_sb(self.draw_, node, node_pre, color=color, width=6)

                    # elif node.route_type == RouteType.REG:
                    #     self.draw_reg_on_tile(self.draw_, node.x, node.y, node.reg_name, node.track)

    def select_tile(self, tile, segs):
        self.restore_buf()
        self.buf_.clear()
        if tile[0] < 0:
            return
        else:
            self.hight_light_route(segs)

            self.tile_pickup(tile)
            self.high_light_tile(tile)
            return
        
    def set_count(self, count):
        self.count = count
        self.tmp = self.create_tile_types()
        ty = self.tmp[TileType.IO16]
        return
    
    def set_tile_hist(self, th):
        self.tile_hist = th
        return
    
    def show_pot_sb(self, pot_sbs):
        for sb in pot_sbs:
            side = side_map[sb.side]
            io = io_map[sb.io]
            tile_x = sb.x
            tile_y = sb.y
            track_id = sb.track

            if side == "Top":
                if io == "IN":
                    dir = "DOWN"
                    x = (
                        GLOBAL_OFFSET_X
                        + GLOBAL_TILE_MARGIN
                        + tile_x * GLOBAL_TILE_WIDTH
                        + (track_id + 1) * GLOBAL_ARROW_DISTANCE
                    )
                    y = GLOBAL_OFFSET_Y + tile_y * GLOBAL_TILE_WIDTH
                elif io == "OUT":
                    dir = "UP"
                    x = (
                        GLOBAL_OFFSET_X
                        + GLOBAL_TILE_MARGIN
                        + tile_x * GLOBAL_TILE_WIDTH
                        + (track_id + 1 + GLOBAL_NUM_TRACK) * GLOBAL_ARROW_DISTANCE
                    )
                    y = GLOBAL_OFFSET_Y + GLOBAL_TILE_MARGIN + tile_y * GLOBAL_TILE_WIDTH
            elif side == "Right":
                if io == "IN":
                    dir = "LEFT"
                    x = GLOBAL_OFFSET_X + tile_x * GLOBAL_TILE_WIDTH + GLOBAL_TILE_WIDTH
                    y = (
                        GLOBAL_OFFSET_Y
                        + GLOBAL_TILE_MARGIN
                        + tile_y * GLOBAL_TILE_WIDTH
                        + (track_id + 1) * GLOBAL_ARROW_DISTANCE
                    )
                elif io == "OUT":
                    dir = "RIGHT"
                    x = (
                        GLOBAL_OFFSET_X
                        + tile_x * GLOBAL_TILE_WIDTH
                        + GLOBAL_TILE_WIDTH
                        - GLOBAL_TILE_MARGIN
                    )
                    y = (
                        GLOBAL_OFFSET_Y
                        + GLOBAL_TILE_MARGIN
                        + tile_y * GLOBAL_TILE_WIDTH
                        + (track_id + 1 + GLOBAL_NUM_TRACK) * GLOBAL_ARROW_DISTANCE
                    )
            elif side == "Bottom":
                if io == "IN":
                    dir = "UP"
                    x = (
                        GLOBAL_OFFSET_X
                        + GLOBAL_TILE_MARGIN
                        + tile_x * GLOBAL_TILE_WIDTH
                        + (track_id + 1 + GLOBAL_NUM_TRACK) * GLOBAL_ARROW_DISTANCE
                    )
                    y = GLOBAL_OFFSET_Y + tile_y * GLOBAL_TILE_WIDTH + GLOBAL_TILE_WIDTH
                elif io == "OUT":
                    dir = "DOWN"
                    x = (
                        GLOBAL_OFFSET_X
                        + GLOBAL_TILE_MARGIN
                        + tile_x * GLOBAL_TILE_WIDTH
                        + (track_id + 1) * GLOBAL_ARROW_DISTANCE
                    )
                    y = (
                        GLOBAL_OFFSET_Y
                        + tile_y * GLOBAL_TILE_WIDTH
                        + GLOBAL_TILE_WIDTH
                        - GLOBAL_TILE_MARGIN
                    )
            elif side == "Left":
                if io == "IN":
                    dir = "RIGHT"
                    x = GLOBAL_OFFSET_X + tile_x * GLOBAL_TILE_WIDTH
                    y = (
                        GLOBAL_OFFSET_Y
                        + GLOBAL_TILE_MARGIN
                        + tile_y * GLOBAL_TILE_WIDTH
                        + (track_id + 1 + GLOBAL_NUM_TRACK) * GLOBAL_ARROW_DISTANCE
                    )
                elif io == "OUT":
                    dir = "LEFT"
                    x = GLOBAL_OFFSET_X + tile_x * GLOBAL_TILE_WIDTH + GLOBAL_TILE_MARGIN
                    y = (
                        GLOBAL_OFFSET_Y
                        + GLOBAL_TILE_MARGIN
                        + tile_y * GLOBAL_TILE_WIDTH
                        + (track_id + 1) * GLOBAL_ARROW_DISTANCE
                    )
            self.draw_sb_box(
                draw=self.draw_,
                x=x,
                y=y,
                dir=dir,
                color="Blue",
            )