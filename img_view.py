# encoding: utf-8
# https://blog.csdn.net/weixin_44821251/article/details/106290132#comments_18071440
'''
@author: LCS
@file: img_view.py
@time: 2020/5/22 12:12
'''

# important data structures
# rh: loc to routeTile[] at this loc
# th: loc to th_Node[]: ty, id, nets, width
# blk_id_list: id to tileNode(old)
# tr_map: tile_id to routeTile[]
# sg: sg_id to routeTile[]
# net_to_seg: net_id to sg_id

import grid

from PySide2.QtWidgets import QApplication, QWidget, QFileDialog, QMessageBox
from PySide2.QtUiTools import QUiLoader
from PySide2.QtGui import QPainter, QBrush, QColor
from PySide2.QtCore import Qt, QRect
from PySide2 import QtWidgets
from PySide2 import QtCore
from PySide2 import QtGui

from pnr_graph import (
    RoutingResultGraph,
    construct_graph,
    TileType,
    RouteType,
    TileNode,
    RouteNode,
)

import pythunder
import pycyclone

import tile_hist
from graph_pro import Design
from pnr_graph import TileType

import time
import string
import os

GLOBAL_TILE_WIDTH = 200
GLOBAL_TILE_MARGIN = 40 #each side is 40 pixs
GLOBAL_TILE_WIDTH_INNER = GLOBAL_TILE_WIDTH - 2 * GLOBAL_TILE_MARGIN
GLOBAL_OFFSET_X = 20 #outer margin
GLOBAL_OFFSET_Y = 20
GLOBAL_NUM_TRACK = 5
GLOBAL_ARROW_DISTANCE = GLOBAL_TILE_WIDTH_INNER // (GLOBAL_NUM_TRACK * 2 + 1)

class PICK_TILE:
    def __init__(self, loc, is_tile, is_working_tile):
        self.loc = loc
        self.is_tile = is_tile
        self.is_working_tile = is_working_tile
        self.is_valid_target = is_tile and (not is_working_tile)

class potential_sb:
    def __init__(self, x, y, io, side, track, width, net):
        self.x = x
        self.y = y
        self.io = io
        self.side = side
        self.track = track
        self.width = width
        self.net = net

class INFO_WIN(QWidget):
    def __init__(self, label):
        super().__init__()
        self.label = label

    def display_text(self, text):
        self.label.setText(text)
        return

class IMG_WIN(QWidget):
    def __init__(self, qw, graphicsView):
        super().__init__()
        self.graphicsView=graphicsView
        self.p = qw

        self.graphicsView.setStyleSheet("padding: 0px; border: 0px;")  # 内边距和边界去除
        self.scene = QtWidgets.QGraphicsScene(self)
        self.graphicsView.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)  # 改变对齐方式

        self.graphicsView.setSceneRect(0, 0, self.graphicsView.viewport().width(),
                                          self.graphicsView.height())  # 设置图形场景大小和图形视图大小一致
        self.graphicsView.setScene(self.scene)

        self.scene.mousePressEvent = self.scene_MousePressEvent  # 接管图形场景的鼠标事件
        # self.scene.mouseReleaseEvent = self.scene_mouseReleaseEvent
        self.scene.mouseMoveEvent = self.scene_mouseMoveEvent
        self.scene.wheelEvent = self.scene_wheelEvent        

        self.ratio = 1  # 缩放初始比例
        self.zoom_step = 0.1  # 缩放步长
        self.zoom_max = 3  # 缩放最大值
        self.zoom_min = 0.3  # 缩放最小值
        self.pixmapItem=None

        # self.tile_x = 5
        # self.tile_y = 4
        # self.img_draw = grid.IMG_DRAW((self.tile_x, self.tile_y))
        self.started = False
        self.empty_tile = PICK_TILE((-1, -1), False, False)
        self.selected_tile = self.empty_tile
        self.target_tile = self.empty_tile


    ######################## IMG CREATION #################

    # refresh for the update on the display
    def refresh_img(self):
        if not self.started:
            self.display_message("WARN:","please load the files before start")
            return

        img = self.img_draw.rt_Qt()
        self.org = img
        if self.pixmapItem != None:
            originX = self.pixmapItem.x()
            originY = self.pixmapItem.y()
        else:
            originX, originY = 0, 0  # 坐标基点

        self.scene.clear()
        self.pixmap = QtGui.QPixmap.fromImage(img)

        self.pixmapItem = self.scene.addPixmap(self.pixmap)
        self.pixmapItem.setScale(self.ratio)  # 缩放
        self.pixmapItem.setPos(originX, originY)

    def load_img(self, x, y, count):
        self.started = True

        self.tile_x = x
        self.tile_y = y
        self.count = count
        self.img_draw = grid.IMG_DRAW((self.tile_x, self.tile_y))
        self.img_draw.set_count(self.count)

        self.reload_img()


    # reload for updates in the design file
    def reload_img(self):
        if not self.started:
            self.display_message("WARN:","please load the files before start")
            return

        self.img_draw.set_tile_hist(self.p.design.th)
        self.img_draw.load_background()
        self.img_draw.draw_used_tiles()
        # self.img_draw.draw_used_routes(self.p.design.result_graph, self.p.design_width)
        self.img_draw.draw_used_routes_n(self.p.design.sg, self.p.design_width, self.p.design.result_graph)
        self.img_draw.label_used_tiles()

        if self.p.edit_mode and not self.p.change_placement:
            self.img_draw.show_pot_sb(self.p.pot_sbs)

        img = self.img_draw.rt_Qt()
        self.org = img
        if self.pixmapItem != None:
            originX = self.pixmapItem.x()
            originY = self.pixmapItem.y()
        else:
            originX, originY = 0, 0  # 坐标基点

        self.scene.clear()
        self.pixmap = QtGui.QPixmap.fromImage(img)

        self.pixmapItem = self.scene.addPixmap(self.pixmap)
        self.pixmapItem.setScale(self.ratio)  # 缩放
        self.pixmapItem.setPos(originX, originY)




    ######################## INTERFACE #################

    def display_message(self, title, mesg):
        self.p.display_message(title, mesg)
        return

    def display_text(self, mesg):
        st = ""
        if self.p.edit_mode:
            st += "Edit:\n"
            if self.p.change_placement:
                st += "P\n"
            else:
                st += "R\n"
        else:
            st += "View:\n"
        st += "Current Width: " + str(self.p.design_width) + "\n"
        st += "========\n"
        st += mesg
        self.p.display_text(st)
        return
    
    def get_tile_info(self, p_tile):
        s = "\n"
        if p_tile.is_tile:
            s = "tile: " + str(p_tile.loc[0]) + " " + str(p_tile.loc[1]) + "\n"
            if p_tile.is_working_tile:
                info = self.p.design.th[p_tile.loc]

                for i in info:
                    tile_type = i.ty
                    tile_id = i.id
                    tile_seg = i.width
                    s += tile_type.name + ": " + tile_id + "\n" + "width " + str(tile_seg) + ": "
                    for k in i.nets:
                        s += str(k) + " "
                    s += "\n --------\n"
            s += "SB ports:\n"
            if p_tile.loc in self.p.design.rh:
                print(len(self.p.design.rh[p_tile.loc]))
                for port in self.p.design.rh[p_tile.loc]:
                    if port.bit_width == self.p.design_width:
                        s += port.net_id + " side " + str(port.side) + " track " + str(port.track)
                        if port.io:
                            s += " out\n"
                        else:
                            s+= " in\n"

        return s
    
    def show_selected_tile(self):
        s = self.get_tile_info(self.selected_tile)
        if self.p.edit_mode and self.p.change_placement:
            s += "SET TO:\n"
            s += self.get_tile_info(self.target_tile)
        self.display_text(s)

    def get_tile(self, pos):
        tile = (-1, -1)
        w = self.pixmap.size().width() * (self.ratio)
        h = self.pixmap.size().height() * (self.ratio)
        x1 = self.pixmapItem.pos().x()  # 图元左位置
        x2 = self.pixmapItem.pos().x() + w  # 图元右位置
        y1 = self.pixmapItem.pos().y()  # 图元上位置
        y2 = self.pixmapItem.pos().y() + h  # 图元下位置
        XT = self.tile_x *GLOBAL_TILE_WIDTH
        YT = self.tile_y *GLOBAL_TILE_WIDTH
        x = pos.x()
        y = pos.y()

        if x < x1 or x > x2 or y < y1 or y > y2: #outside
            return tile
        #pos in image space
        dx = (x - x1) / self.ratio 
        dy = (y - y1) / self.ratio

        dx -= GLOBAL_OFFSET_X
        dy -= GLOBAL_OFFSET_Y

        if dx < 0 or dy < 0 or dx > XT or dy > YT:
            return tile
        else:
            px = dx // GLOBAL_TILE_WIDTH
            py = dy // GLOBAL_TILE_WIDTH
            ddx = dx - px * GLOBAL_TILE_WIDTH
            ddy = dy - py * GLOBAL_TILE_WIDTH
            out_x = ddx < GLOBAL_TILE_MARGIN or ddx > GLOBAL_TILE_MARGIN + GLOBAL_TILE_WIDTH_INNER
            out_y = ddy < GLOBAL_TILE_MARGIN or ddy > GLOBAL_TILE_MARGIN + GLOBAL_TILE_WIDTH_INNER
            if  out_x or out_y:
                return tile
            else:
                return (dx // GLOBAL_TILE_WIDTH, dy // GLOBAL_TILE_WIDTH)
            

    def get_sb_box_cent(self, sb):
        side = sb.side
        io = sb.io
        tile_x = sb.x
        tile_y = sb.y
        track_id = sb.track
        pw = GLOBAL_TILE_MARGIN * 0.5

        if side == 3:
            if io == 0:
                dir = "DOWN"
                x = (
                    GLOBAL_OFFSET_X
                    + GLOBAL_TILE_MARGIN
                    + tile_x * GLOBAL_TILE_WIDTH
                    + (track_id + 1) * GLOBAL_ARROW_DISTANCE
                )
                y = GLOBAL_OFFSET_Y + tile_y * GLOBAL_TILE_WIDTH
            elif io == 1:
                dir = "UP"
                x = (
                    GLOBAL_OFFSET_X
                    + GLOBAL_TILE_MARGIN
                    + tile_x * GLOBAL_TILE_WIDTH
                    + (track_id + 1 + GLOBAL_NUM_TRACK) * GLOBAL_ARROW_DISTANCE
                )
                y = GLOBAL_OFFSET_Y + GLOBAL_TILE_MARGIN + tile_y * GLOBAL_TILE_WIDTH
        elif side == 0:
            if io == 0:
                dir = "LEFT"
                x = GLOBAL_OFFSET_X + tile_x * GLOBAL_TILE_WIDTH + GLOBAL_TILE_WIDTH
                y = (
                    GLOBAL_OFFSET_Y
                    + GLOBAL_TILE_MARGIN
                    + tile_y * GLOBAL_TILE_WIDTH
                    + (track_id + 1) * GLOBAL_ARROW_DISTANCE
                )
            elif io == 1:
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
        elif side == 1:
            if io == 0:
                dir = "UP"
                x = (
                    GLOBAL_OFFSET_X
                    + GLOBAL_TILE_MARGIN
                    + tile_x * GLOBAL_TILE_WIDTH
                    + (track_id + 1 + GLOBAL_NUM_TRACK) * GLOBAL_ARROW_DISTANCE
                )
                y = GLOBAL_OFFSET_Y + tile_y * GLOBAL_TILE_WIDTH + GLOBAL_TILE_WIDTH
            elif io == 1:
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
        elif side == 2:
            if io == 0:
                dir = "RIGHT"
                x = GLOBAL_OFFSET_X + tile_x * GLOBAL_TILE_WIDTH
                y = (
                    GLOBAL_OFFSET_Y
                    + GLOBAL_TILE_MARGIN
                    + tile_y * GLOBAL_TILE_WIDTH
                    + (track_id + 1 + GLOBAL_NUM_TRACK) * GLOBAL_ARROW_DISTANCE
                )
            elif io == 1:
                dir = "LEFT"
                x = GLOBAL_OFFSET_X + tile_x * GLOBAL_TILE_WIDTH + GLOBAL_TILE_MARGIN
                y = (
                    GLOBAL_OFFSET_Y
                    + GLOBAL_TILE_MARGIN
                    + tile_y * GLOBAL_TILE_WIDTH
                    + (track_id + 1) * GLOBAL_ARROW_DISTANCE
                )
        if dir == "LEFT":
            x -= pw
        elif dir == "RIGHT":
            x += pw
        elif dir == "UP":
            y -= pw
        elif dir == "DOWN":
            y += pw
        
        return (x, y)
            
    def check_sb(self, pos):
        w = self.pixmap.size().width() * (self.ratio)
        h = self.pixmap.size().height() * (self.ratio)
        x1 = self.pixmapItem.pos().x()  # 图元左位置
        x2 = self.pixmapItem.pos().x() + w  # 图元右位置
        y1 = self.pixmapItem.pos().y()  # 图元上位置
        y2 = self.pixmapItem.pos().y() + h  # 图元下位置
        XT = self.tile_x *GLOBAL_TILE_WIDTH
        YT = self.tile_y *GLOBAL_TILE_WIDTH
        x = pos.x()
        y = pos.y()

        if x < x1 or x > x2 or y < y1 or y > y2: #outside
            return
        #pos in image space
        dx = (x - x1) / self.ratio 
        dy = (y - y1) / self.ratio
        pw = (GLOBAL_TILE_WIDTH - 2 * GLOBAL_TILE_MARGIN) / 25
        for pot_sb in self.p.pot_sbs:
            (x_c, y_c) = self.get_sb_box_cent(pot_sb)
            if (dx - x_c) * (dx - x_c) + (dy - y_c) * (dy - y_c) <= pw * pw:
                print(type(pot_sb), pot_sb)
                self.p.add_sb(pot_sb)
                return True
        
        return False


    def scene_MousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:  # 左键按下

            self.preMousePosition = event.scenePos()  # 获取鼠标当前位置
            # print(self.preMousePosition.x(), self.preMousePosition.y(), self.graphicsView.size())
            tile_loc = self.get_tile(self.preMousePosition)
            is_tile = tile_loc[0] >= 0
            is_working_tile = tile_loc in self.p.design.th
            s_tile = PICK_TILE(tile_loc, is_tile, is_working_tile)

            if  self.p.edit_mode and self.p.change_placement:
                self.target_tile = s_tile
            else:
                self.selected_tile = s_tile

            hl_segs = []
            if is_tile and is_working_tile:
                for th_node in self.p.design.th[tile_loc]:
                    if th_node.width == self.p.design_width:
                        for net in th_node.nets:
                            for seg_id in self.p.design.net_to_segs[net]:
                                s = self.p.design.sg[seg_id]
                                hl_segs.append(s)

            self.img_draw.select_tile(tile_loc, hl_segs)

            self.show_selected_tile()

            # try to add sb
            if self.p.edit_mode and not self.p.change_placement:
                if self.check_sb(self.preMousePosition):
                    return

        if event.button() == QtCore.Qt.RightButton:  # 右键按下
            print("鼠标右键单击")  # 响应测试语句
        
        self.refresh_img()


    def scene_mouseMoveEvent(self, event):
        if event.buttons() == QtCore.Qt.LeftButton:
            self.MouseMove = event.scenePos() - self.preMousePosition  # 鼠标当前位置-先前位置=单次偏移量
            self.preMousePosition = event.scenePos()  # 更新当前鼠标在窗口上的位置，下次移动用
            self.pixmapItem.setPos(self.pixmapItem.pos() + self.MouseMove)  # 更新图元位置

    # 定义滚轮方法。当鼠标在图元范围之外，以图元中心为缩放原点；当鼠标在图元之中，以鼠标悬停位置为缩放中心
    def scene_wheelEvent(self, event):
        angle = event.delta() / 8  # 返回QPoint对象，为滚轮转过的数值，单位为1/8度
        if angle > 0:
            self.ratio += self.zoom_step  # 缩放比例自加
            if self.ratio > self.zoom_max:
                self.ratio = self.zoom_max
            else:
                w = self.pixmap.size().width() * (self.ratio - self.zoom_step)
                h = self.pixmap.size().height() * (self.ratio - self.zoom_step)
                x1 = self.pixmapItem.pos().x()  # 图元左位置
                x2 = self.pixmapItem.pos().x() + w  # 图元右位置
                y1 = self.pixmapItem.pos().y()  # 图元上位置
                y2 = self.pixmapItem.pos().y() + h  # 图元下位置
                if event.scenePos().x() > x1 and event.scenePos().x() < x2 \
                        and event.scenePos().y() > y1 and event.scenePos().y() < y2:  # 判断鼠标悬停位置是否在图元中
                    self.pixmapItem.setScale(self.ratio)  # 缩放
                    a1 = event.scenePos() - self.pixmapItem.pos()  # 鼠标与图元左上角的差值
                    a2=self.ratio/(self.ratio- self.zoom_step)-1    # 对应比例
                    delta = a1 * a2
                    self.pixmapItem.setPos(self.pixmapItem.pos() - delta)

                else:
                    self.pixmapItem.setScale(self.ratio)  # 缩放
                    delta_x = (self.pixmap.size().width() * self.zoom_step) / 2  # 图元偏移量
                    delta_y = (self.pixmap.size().height() * self.zoom_step) / 2
                    self.pixmapItem.setPos(self.pixmapItem.pos().x() - delta_x,
                                           self.pixmapItem.pos().y() - delta_y)  # 图元偏移
        else:
            self.ratio -= self.zoom_step
            if self.ratio < self.zoom_min:
                self.ratio = self.zoom_min
            else:
                w = self.pixmap.size().width() * (self.ratio + self.zoom_step)
                h = self.pixmap.size().height() * (self.ratio + self.zoom_step)
                x1 = self.pixmapItem.pos().x()
                x2 = self.pixmapItem.pos().x() + w
                y1 = self.pixmapItem.pos().y()
                y2 = self.pixmapItem.pos().y() + h
                if event.scenePos().x() > x1 and event.scenePos().x() < x2 \
                        and event.scenePos().y() > y1 and event.scenePos().y() < y2:
                    self.pixmapItem.setScale(self.ratio)  # 缩放
                    a1 = event.scenePos() - self.pixmapItem.pos()  # 鼠标与图元左上角的差值
                    a2=self.ratio/(self.ratio+ self.zoom_step)-1    # 对应比例
                    delta = a1 * a2
                    self.pixmapItem.setPos(self.pixmapItem.pos() - delta)
                else:
                    self.pixmapItem.setScale(self.ratio)
                    delta_x = (self.pixmap.size().width() * self.zoom_step) / 2
                    delta_y = (self.pixmap.size().height() * self.zoom_step) / 2
                    self.pixmapItem.setPos(self.pixmapItem.pos().x() + delta_x, self.pixmapItem.pos().y() + delta_y)

class GUI(QWidget):
    def __init__(self):
        super().__init__()
        self.ui = QUiLoader().load('edi.ui')
        self.graphic=IMG_WIN(self, self.ui.graphicsView)	# 实例化IMG_WIN类

        self.label = INFO_WIN(self.ui.label)
        self.seg_dis = INFO_WIN(self.ui.segment)
        self.net_dis = INFO_WIN(self.ui.nets)
        self.ui.pushButton.clicked.connect(self.load_file)
        self.ui.switchButton.clicked.connect(self.switch_width)
        self.ui.setButton.clicked.connect(self.place)
        self.ui.editButton.clicked.connect(self.edit)
        self.ui.saveButton.clicked.connect(self.save_design)
        self.ui.rlButton.clicked.connect(self.reload_file)
        self.ui.A_bt.clicked.connect(self.pick_seg)
        self.ui.B_bt.clicked.connect(self.rm_last)
        self.ui.C_bt.clicked.connect(self.quit_seg)
        self.ui.D_bt.clicked.connect(self.set_seg)
        self.ui.lineEdit.returnPressed.connect(self.id_input)
        self.ui.reg_edit.returnPressed.connect(self.reg_input)
        self.rec = 0
        self.edit_mode = False
        self.change_placement = True
        self.highlight_net = False
        self.design_width = 1
        self.cur_seg = "-1"
        self.dirname = ""

    ################ FILE CODE #################
    def load_file(self):
        # USE later for loading
        filePath, _ = QFileDialog.getOpenFileName(
            self.ui,
            "Select design files",  # 标题
            r"E:\picture\test",  # 起始目录
            "Graphs(*.graph);;Route file(*.route);;All files(*.*)" #"file type (*.graph *.id_to_name *.packed *.place *route)"
        )
        if len(filePath) == 0:
            return
        print(filePath)
        self.dirname = os.path.dirname(filePath)
        self.process_path(self.dirname)

        self.ui.lineEdit.clear()
        self.seg_display("")

        # self.count = self.design.type_count
        self.count = 6
        (self.dim_x, self.dim_y) = self.design.get_dim()

        self.edit_mode = False
        self.change_placement = True
        self.graphic.load_img(self.dim_x, self.dim_y, self.count)
        self.id_input()
        self.show_free_nets()
        return
    
    def reload_file(self):
        self.save_design()
        self.process_path(self.dirname)
        return

    def process_path(self, filePath):
        dirname = filePath
        netlist = os.path.join(dirname, "design.packed")
        assert os.path.exists(netlist), netlist + " does not exist"
        placement = os.path.join(dirname, "design.place")
        assert os.path.exists(placement), placement + " does not exists"
        route = os.path.join(dirname, "design.route")
        assert os.path.exists(route), route + " does not exists"
        id_to_name_filename = os.path.join(dirname, "design.id_to_name")
        assert os.path.exists(id_to_name_filename), id_to_name_filename + " does not exists"

        graph1 = os.path.join(dirname, "1.graph")
        assert os.path.exists(graph1), route + " does not exists"
        graph16 = os.path.join(dirname, "16.graph")
        if not os.path.exists(graph16):
            graph16 = os.path.join(dirname, "17.graph")
        assert os.path.exists(graph16), route + " does not exists"

        self.design = Design(netlist, placement, route, id_to_name_filename, [graph1, graph16])
        # clk_info = self.design.sta()
        # self.display_message("MSG:", clk_info)
        return

    def save_design(self):
        if self.dirname == "":
            self.display_message("WARN:", "Please load a design\n")
        if self.edit_mode:
            self.display_message("WARN:", "Please finish editing before saving\n")
        for seg_id in self.design.sg:
            if not self.design.sg[seg_id].settled:
                self.display_message("WARN:", "Please finish editing before saving\n")
        
        self.save_place()
        self.save_route()
        self.display_message("MSG", "SUCCESS")
        # self.process_path(self.dirname)
        return        
    
    def save_place(self):
        place_f = os.path.join(self.dirname, "design.place")
        assert (os.path.exists(place_f))
        content = ""

        f = open(place_f, "r")
        lines = f.readlines()
        line_ind = 0
        while line_ind < len(lines):
            if line_ind < 2:
                content += lines[line_ind]
                line_ind += 1
            else:
                line = lines[line_ind].strip()
                line_ind += 1
                tokens = line.split("\t")
                t_id = tokens[-1][1:]
                node = self.design.tr_map[t_id][0]
                tokens[2] = str(node.x)
                tokens[3] = str(node.y)
                content += tokens[0] + "\t\t" + tokens[2] + "\t" + tokens[3] + "\t\t" + tokens[-1] + "\n"
        f.close()
        f = open(place_f, "w")
        f.write(content)
        f.close()
        return
        
    def save_route(self):
        route_f = os.path.join(self.dirname, "design.route")
        assert (os.path.exists(route_f))

        f = open(route_f, 'w')
        content = ""
        for net_id in self.design.net_to_segs:
            record_r = set()
            segments = self.design.net_to_segs[net_id]
            content += "Net ID: "+ net_id + " Segment Size: " + str(len(segments)) + "\n"
            i = 0
            for seg_id in segments:
                seg = self.design.sg[seg_id].nodes
                content += "Segment: " + str(i) + " Size: " + str(len(seg)) + "\n"
                for node in seg:
                    n = ""
                    if node.route_type == RouteType.SB:
                        n = "SB (" + str(node.track) + ", " + str(node.x) + ", " + str(node.y) + ", " + str(node.side) + ", " + str(node.io) + ", " + str(node.bit_width) + ")\n"
                    elif node.route_type == RouteType.PORT:
                        n = "PORT " + node.port + " (" + str(node.x) + ", " + str(node.y) + ", " + str(node.bit_width) + ")\n"
                    elif node.route_type == RouteType.RMUX:
                        n = "RMUX " + node.rmux_name + " (" + str(node.x) + ", " + str(node.y) + ", " + str(node.bit_width) + ")\n"
                    else:
                        n = "REG " + node.reg_name + " (" + str(node.track) + ", " + str(node.x) + ", " + str(node.y) + ", " + str(node.bit_width) + ")\n"
                    content += n
                i += 1
            content += "\n"
        f.write(content)
        f.close()
        return
    
    ################ IMAGE CODE #################
    def reload_img(self):
        # self.graphic.load_img(self.dim_x, self.dim_y, self.count)
        self.graphic.reload_img()
        return
    
    def refresh_img(self):
        self.graphic.refresh_img()
        return
    
    def switch_width(self):
        if self.design_width == 1:
            self.design_width = 17
        else:
            self.design_width = 1
        self.graphic.reload_img()
        self.graphic.show_selected_tile()
        return

    def highlight(self):
        if self.highlight_net:
            self.highlight_net = False
        else:
            self.highlight_net = True

        self.display_message("Check:", "do nothing\n")
        return

    ################ TILE CODE #################
    def edit(self):
        if self.edit_mode:
            self.display_message("WARN:", "Please load design first")
            return

        if not self.can_edit_tile():
            return

        self.change_placement = True
        self.edit_mode = True
        # self.display_text("In Edit Mode")
        self.graphic.show_selected_tile()
        return
    
    def can_edit_tile(self):
        p_tile = self.graphic.selected_tile
        if (not p_tile.is_tile) or (not p_tile.is_working_tile):
            return False
        if p_tile.loc[1] == 0: #cannot edit port tile
            return False 
        return True
    
    def place(self):
        if not self.edit_mode and not self.change_placement:
            return

        # no edit
        if self.graphic.selected_tile.loc == self.graphic.target_tile.loc:
            self.edit_mode = False
            self.graphic.show_selected_tile()
            return

        if not self.try_place():
            return
        
        self.place_tile()
        # self.display_text("Exit Edit Mode")
        self.graphic.show_selected_tile()
        return
    
    def place_tile(self):
        print("succeed!!!")
        self.edit_mode = False
        assert(self.graphic.selected_tile.loc in self.design.th)
        assert(self.graphic.target_tile.loc not in self.design.th)

        loc_ori = self.graphic.selected_tile.loc
        loc_new = self.graphic.target_tile.loc

        # update th
        val = self.design.th[self.graphic.selected_tile.loc]
        del self.design.th[self.graphic.selected_tile.loc]

        self.graphic.selected_tile = self.graphic.target_tile
        self.graphic.target_tile = self.graphic.empty_tile
        loc = self.graphic.selected_tile.loc
        key = (int(loc[0]), int(loc[1]))

        self.design.th[key] = val

        # update sg
        for th_n in val:
            for net_id in th_n.nets:
                for seg_id in self.design.net_to_segs[net_id]:
                    s = self.design.sg[seg_id]
                    if s.settled:
                        s.settled = False
                        # update rh
                        for n in s.nodes:
                            if n.route_type == RouteType.SB and n in self.design.rh[(n.x, n.y)]:
                                self.design.rh[(n.x, n.y)].remove(n)
                        del s.nodes[1:-1]

            # update tn
            t_n = self.design.blk_id_list[th_n.id]
            t_n.x = int(loc[0])
            t_n.y = int(loc[1])

            # update tr_map ?
            routes = self.design.tr_map[th_n.id]
            for r in routes:
                r.x = int(loc[0])
                r.y = int(loc[1])

        self.id_input()
        self.show_free_nets()
        self.reload_img()
        return

    def try_place(self):
        s_tile = self.graphic.selected_tile
        e_tile = self.graphic.target_tile
        if e_tile.is_working_tile or (not e_tile.is_tile):
            return False
        #some restrictions, may need further discussion
        source_type = [th_n.ty for th_n in self.design.th[s_tile.loc]]

        lim_type = TileType.PE
        if e_tile.loc[1] == 0: #currently unimplemented
            lim_type = TileType.IO1
            return False
        if e_tile.loc[0] % 4 == 3:
            lim_type = TileType.MEM

        if lim_type == TileType.PE:
            if TileType.MEM in source_type:
                return False
            else:
                return True
        if lim_type == TileType.MEM:
            if TileType.PE in source_type:
                return False
            else:
                return True

    def detector(self):
        self.label.display_text("detected: " + str(self.rec))
        self.rec += 1
        return
    

    def show_free_nets(self):
        s = "Free Nets: \n========\n"
        for seg_id in self.design.sg:
            if not self.design.sg[seg_id].settled:
                seg = self.design.sg[seg_id]
                s += "segment " + str(seg_id) + " in net " + str(seg.net) + " " + str(seg.width) + "\n"
        
        self.nets_display(s)


    def valid_reg_name(self, name):
        if len(name) < 3:
            return False
        if name[0] != "T":
            return False
        if not name[1].isdigit():
            return False
        if name[2] != "_":
            return False
        return True

    def reg_input(self):
        if not self.graphic.started:
            self.display_message("WARN:", "Please load design first")
            return
        
        if self.edit_mode:
            self.display_message("WARN:", "Please finish the current editing")
            return

        s = self.ui.reg_edit.text()

        if s == "Reg Edit" or s == "":
            return
        
        #input format: reg_id x y (reg_name)
        #or: reg_id reg_name
        r_input = s.split(" ")

        if r_input[0] not in self.design.blk_id_list:
            self.display_message("WARN:", "Invalid REG ID")
            return

        pre_x = self.design.blk_id_list[r_input[0]].x
        pre_y = self.design.blk_id_list[r_input[0]].y
        wid = self.design.tr_map[r_input[0]][0].bit_width

        x = -1
        y = -1
        n_reg_name = ""
        valid_input = True

        if len(r_input) == 2:
            if self.valid_reg_name(r_input[1]):
                n_reg_name = r_input[1]
                x = pre_x
                y = pre_y
            else:
                valid_input = False
        elif len(r_input) == 3:
            x = int(r_input[1])
            y = int(r_input[2])
            n_reg_name = self.design.tr_map[r_input[0]][0].reg_name
        elif len(r_input) == 4:
            x = int(r_input[1])
            y = int(r_input[2])
            if self.valid_reg_name(r_input[3]):
                n_reg_name = r_input[3]
            else:
                valid_input = False
        
        if not valid_input:
            self.display_message("WARN:", "Invalid input")
            return

        # if len(r_input) == 3:
        #     r_input.append(self.design.tr_map[r_input[0]][0].reg_name)

        # n_reg_name = r_input[3]

        if x < 0 or x >= self.dim_x or y < 1 or y >= self.dim_y:
            self.display_message("WARN:", "Invalid location")
            return

        s_check = False
        for th_n in self.design.th[(pre_x, pre_y)]:
            if th_n.id == r_input[0]:
                s_check = True
                break        
        assert(s_check)

        #check if the new location is occupied
        #occupied if there is a REG at the new location
        free = True
        if (x, y) in self.design.th:
            for th_n in self.design.th[(x, y)]:
                if th_n.ty == TileType.REG:
                    t_wid = th_n.width
                    if self.design.tr_map[th_n.id][0].reg_name == n_reg_name and t_wid == wid:
                        free = False
                        break
        
        if not free:
            self.display_message("WARN:", "The new location is occupied")
            return
        
        #occupied if there is a seg at the new location
        new_track = int(n_reg_name[1])
        if new_track < 0 or new_track > 4:
            self.display_message("WARN:", "Invalid track")
            return

        dir = n_reg_name[3:]
        new_dir = -1
        if dir == "NORTH":
            new_dir = 3
        elif dir == "SOUTH":
            new_dir = 1
        elif dir == "EAST":
            new_dir = 0
        elif dir == "WEST":
            new_dir = 2
        
        if new_dir == -1:
            self.display_message("WARN:", "Invalid direction")
            return
        
        net_ids = set()
        for r_n in self.design.tr_map[r_input[0]]:
            net_ids.add(r_n.net_id)

        if (x, y) in self.design.rh:
            for r_n in self.design.rh[(x, y)]:
                if r_n.route_type == RouteType.SB and r_n.io == 1:
                    if r_n.track == new_track and r_n.side == new_dir and r_n.bit_width == wid and r_n.net_id not in net_ids:
                        free = False
                        break

        if not free:
            self.display_message("WARN:", "The new location is occupied")
            return
        
        #finish checking, now we can move the REG
        self.design.blk_id_list[r_input[0]].x = x
        self.design.blk_id_list[r_input[0]].y = y

        for r_n in self.design.tr_map[r_input[0]]:
            r_n.x = x
            r_n.y = y
            r_n.track = new_track
            r_n.reg_name = n_reg_name
        
        ind = 0
        while ind < len(self.design.th[(pre_x, pre_y)]):
            if self.design.th[(pre_x, pre_y)][ind].id == r_input[0]:
                break
            ind += 1

        th_n = self.design.th[(pre_x, pre_y)].pop(ind)

        if len(self.design.th[(pre_x, pre_y)]) == 0:
            del self.design.th[(pre_x, pre_y)]
        
        if (x, y) not in self.design.th:
            self.design.th[(x, y)] = []

        self.design.th[(x, y)].append(th_n)
        for net_id in th_n.nets:
            for seg_id in self.design.net_to_segs[net_id]:
                sg = self.design.sg[seg_id]
                if sg.settled:
                    sg.settled = False
                    # update rh
                    for n in sg.nodes:
                        if n.route_type == RouteType.SB and n in self.design.rh[(n.x, n.y)]:
                            self.design.rh[(n.x, n.y)].remove(n)
                    del sg.nodes[1:-1]

        self.show_free_nets()
        self.id_input()
        self.reload_img()
        return

    def id_input(self):
        if not self.graphic.started:
            self.display_message("WARN:", "Please load design first")
            return

        s = self.ui.lineEdit.text()

        if s == "-1" or s == "info ID" or s == "":
            return

        info = ""
        if self.edit_mode and not self.change_placement:
            info += "----Edit----\n"
            s = self.cur_seg
        
        if s.isdigit():
            seg_id = int(s)
            if seg_id in self.design.sg:
                seg = self.design.sg[seg_id]
                info += "Segment " + s + ":\n"
                info += "Net_id: " + seg.net + " " + str(seg.width) + "\n"
                if seg.settled:
                    info += "Placed\n"
                else:
                    info += "Free\n"
                info += "Start: " + seg.start_t
                if seg.start_t[0] == "r":
                    info += " " + seg.nodes[0].reg_name

                info += " " + str(self.design.tr_map[seg.start_t][0].x)
                info += " " + str(self.design.tr_map[seg.start_t][0].y)
                info += "\n========\n"
                info += self.design.get_route_info(seg_id)
                info += "========\nEnd: " + seg.end_t
                if seg.end_t[0] == "r":
                    info += " " + seg.nodes[-1].reg_name
                
                info += " " + str(self.design.tr_map[seg.end_t][0].x)
                info += " " + str(self.design.tr_map[seg.end_t][0].y)
                info += "\n"
                self.seg_display(info)
                return
            else:
                self.display_message("WARN:", "Invalid segment id\n")
                return
        
        if s[0] == 'e' and s[1:].isdigit():
            net_id = s
            if net_id in self.design.net_to_segs:
                info += "Net " + s + ":\n"
                for seg_id in self.design.net_to_segs[net_id]:
                    info += "Seg " + str(seg_id)
                    seg = self.design.sg[seg_id]
                    if seg.settled:
                        info += " Placed\n"
                    else:
                        info += " Free\n"
                    info += "Start: " + seg.start_t + " End: " + seg.end_t + "\n"
                self.seg_display(info)
                return
            else:
                self.display_message("WARN:", "Invalid net id\n")
                return

        self.display_message("WARN:", "Invalid input\n")


    def pick_seg(self):
        if self.edit_mode:
            self.display_message("WARN:", "Please finish the current editing")
            return
        
        s = self.ui.lineEdit.text()
        can_pick = True
        if not s.isdigit():
            can_pick = False
        
        if int(s) not in self.design.sg:
            can_pick = False
        
        if not can_pick:
            self.display_message("WARN:", "Invalid Segment ID")
            return
        
        self.cur_seg = s

        self.design.sg[int(s)].picked = True
        if self.design.sg[int(s)].settled:
            self.design.sg[int(s)].settled = False
            for i in range(len(self.design.sg[int(s)].nodes) - 1, -1, -1):
                n = self.design.sg[int(s)].nodes[i]
                if n.route_type == RouteType.RMUX:
                    self.design.sg[int(s)].nodes.remove(n)
            
            # for i in self.design.sg[int(s)].nodes:
            #     print(i.route_type)
        self.change_placement = False
        self.edit_mode = True

        # print(self.design.sg[int(s)].nodes[0].route_type, self.design.sg[int(s)].nodes[-1].route_type)

        self.find_potential_sb()
        self.id_input()
        self.show_free_nets()
        self.reload_img()

        return
    
    def rm_last (self):
        assert(not self.change_placement)
        assert(self.edit_mode)

        seg_id = int(self.cur_seg)
        seg = self.design.sg[seg_id]
        nodes = seg.nodes

        if len(nodes) > 2:
            n = nodes.pop(-2)
            assert((n.x, n.y) in self.design.rh)
            self.design.rh[(n.x, n.y)].remove(n)
        
        self.find_potential_sb()
        self.id_input()
        self.reload_img()
        self.graphic.show_selected_tile()
        return
    
    def quit_seg(self):
        assert(not self.change_placement)
        assert(self.edit_mode)
        self.edit_mode = False

        s = self.cur_seg
        self.design.sg[int(s)].picked = False
        self.cur_seg = -1

        self.id_input()
        self.reload_img()
        return
    
    def set_seg(self):
        assert(not self.change_placement)
        assert(self.edit_mode)
        
        valid = self.check_valid_seg(int(self.cur_seg))
        if not valid:
            return
        
        self.display_message("MSG", "SUCCESS")
        self.expand_seg(int(self.cur_seg))
        
        # print("\nstart checking")

        # seg = self.design.sg[int(self.cur_seg)]
        # nodes = seg.nodes
        # for n in nodes:
        #     print(n.route_type)
        #     if n.route_type == RouteType.RMUX:
        #         print(n.rmux_name)
        # print("finish checking")


        self.edit_mode = False

        s = self.cur_seg
        self.design.sg[int(s)].settled = True
        self.design.sg[int(s)].picked = False

        self.cur_seg = "-1"

        self.id_input()
        self.show_free_nets()
        self.reload_img()

        return
    
    def add_sb(self, pot_sb):
        seg_id = int(self.cur_seg)
        seg = self.design.sg[seg_id]
        net = seg.net
        nodes = seg.nodes

        node = RouteNode(
            pot_sb.x,
            pot_sb.y,
            route_type=RouteType.SB,
            track=pot_sb.track,
            side=pot_sb.side,
            io=pot_sb.io,
            bit_width=pot_sb.width,
            net_id=pot_sb.net,
            kernel=nodes[0].kernel,
        )
        if (pot_sb.x, pot_sb.y) not in self.design.rh:
            self.design.rh[(pot_sb.x, pot_sb.y)] = set()
        self.design.rh[(pot_sb.x, pot_sb.y)].add(node)
        nodes.insert(-1, node)

        self.find_potential_sb()
        self.id_input()
        self.reload_img()
        return

    def find_potential_sb(self):
        assert(self.edit_mode and not self.change_placement)
        assert(self.cur_seg != "-1")

        sides = 4
        t_track = 5

        seg_id = int(self.cur_seg)
        seg = self.design.sg[seg_id]
        net = seg.net
        nodes = seg.nodes
        s_t_id = seg.start_t
        e_t_id = seg.end_t

        s_t = self.design.blk_id_list[s_t_id]
        e_t = self.design.blk_id_list[e_t_id]
        width = nodes[0].bit_width
        kernel = nodes[0].kernel

        p_list = []

        if len(nodes) == 2: #nothing here yet
            if s_t.tile_type == TileType.REG:
                dir = -1
                x = s_t.x
                y = s_t.y
                track = int(nodes[0].reg_name[1])
                if "EAST" in nodes[0].reg_name:
                    dir = 2
                    x += 1
                elif "SOUTH" in nodes[0].reg_name:
                    dir = 3
                    y += 1
                elif "WEST" in nodes[0].reg_name:
                    dir = 0
                    x -= 1
                elif "NORTH" in nodes[0].reg_name:
                    dir = 1
                    y -= 1   
                p_list.append(potential_sb(x, y, io=0, side=dir, track = track, width = width, net=net))
            elif s_t.tile_type == TileType.IO1 or s_t.tile_type == TileType.IO16:
                dir = 3
                y = 1
                x = s_t.x
                for i in range(t_track):
                    p_list.append(potential_sb(x, y, io=0, side=dir, track = i, width = width, net=net))
            else:
                x = s_t.x
                y = s_t.y
                for d in range(sides):
                    for i in range(t_track):
                        p_list.append(potential_sb(x, y, io=1, side=d, track = i, width = width, net=net))
        else: #extending on existing seg
            route = nodes[-2]
            x = route.x
            y = route.y
            if route.io: #an output sb
                dir = -1
                if route.side == 0:
                    x += 1
                    dir = 2
                elif route.side == 1:
                    y += 1
                    dir = 3
                elif route.side == 2:
                    x -= 1
                    dir = 0
                else:
                    y -= 1
                    dir = 1
                p_list.append(potential_sb(x, y, io = 0, side = dir, track = route.track, width = width, net=net))
            else: #an input sb | use Imran scheme
                i = route.track
                if route.side == 0:
                    p_list.append(potential_sb(x, y, io=1, side=2, track=i, width=width, net=net))
                    p_list.append(potential_sb(x, y, io=1, side=1, track=(2*t_track - 2 - i)%t_track, width=width, net=net))
                    p_list.append(potential_sb(x, y, io=1, side=3, track=(i + t_track - 1)%t_track, width=width, net=net))
                elif route.side == 3:
                    p_list.append(potential_sb(x, y, io=1, side=1, track=i, width=width, net=net))
                    p_list.append(potential_sb(x, y, io=1, side=2, track=(t_track - i)%t_track, width=width, net=net))
                    p_list.append(potential_sb(x, y, io=1, side=0, track=(i + 1)%t_track, width=width, net=net))
                elif route.side == 2:
                    p_list.append(potential_sb(x, y, io=1, side=0, track=i, width=width, net=net))
                    p_list.append(potential_sb(x, y, io=1, side=3, track=(t_track - i)%t_track, width=width, net=net))
                    p_list.append(potential_sb(x, y, io=1, side=1, track=(t_track + i - 1)%t_track, width=width, net=net))
                else:
                    p_list.append(potential_sb(x, y, io=1, side=3, track=i, width=width, net=net))
                    p_list.append(potential_sb(x, y, io=1, side=2, track=(i + 1)%t_track, width=width, net=net))
                    p_list.append(potential_sb(x, y, io=1, side=0, track=(2*t_track - 2 - i)%t_track, width=width, net=net))
        
        self.pot_sbs = self.confirm_pot(p_list)
        # self.pot_sbs = [potential_sb(2, 2, io=1, side=3, track = 2, width = width),potential_sb(2, 1, io=0, side=1, track = 3, width = width)]
        return 


    def confirm_pot(self, p_list):
        if len(p_list) == 0:
            return p_list

        c_p_list = []
        for p_sb in p_list:
            should_add = True
            if p_sb.x < 0 or p_sb.x >= self.dim_x:
                should_add = False
            if p_sb.y <= 0 or p_sb.y >= self.dim_y:
                should_add = False

            if (p_sb.x, p_sb.y) in self.design.rh:
                for r in self.design.rh[(p_sb.x, p_sb.y)]:
                    if r.io == p_sb.io and r.side == p_sb.side and r.track == p_sb.track and r.bit_width == p_sb.width:
                        if r.net_id != p_sb.net:
                            should_add = False
            
            if should_add:
                c_p_list.append(p_sb)
        
        return c_p_list


    def check_valid_seg(self, seg_id):
        v = True
        assert(seg_id in self.design.sg)
        seg = self.design.sg[seg_id]
        nodes = seg.nodes
        assert(nodes[0].route_type != RouteType.SB)
        assert(nodes[-1].route_type != RouteType.SB)
        assert(nodes[0].route_type != RouteType.RMUX)
        assert(nodes[-1].route_type != RouteType.RMUX)
        s_t_id = seg.start_t
        e_t_id = seg.end_t

        s_t = self.design.blk_id_list[s_t_id]
        e_t = self.design.blk_id_list[e_t_id]

        assert(nodes[0].x == s_t.x and nodes[0].y == s_t.y)
        assert(nodes[-1].x == e_t.x and nodes[-1].y == e_t.y)

        #check start
        if s_t.tile_type == TileType.IO1 or s_t.tile_type == TileType.IO16:
            if s_t.x != nodes[1].x or nodes[1].y != 1:
                v = False
                self.display_message("ERROR:", "Route failed for start io")
                return v
        elif s_t.tile_type == TileType.REG:
            dir = -1
            if "EAST" in nodes[0].reg_name:
                dir = 0
            elif "SOUTH" in nodes[0].reg_name:
                dir = 1
            elif "WEST" in nodes[0].reg_name:
                dir = 2
            elif "NORTH" in nodes[0].reg_name:
                dir = 3   
            assert(dir >= 0)

            if dir == 0:
                if s_t.x != nodes[1].x - 1 or s_t.y != nodes[1].y:
                    v = False
            elif dir == 1:
                if s_t.x != nodes[1].x or s_t.y != nodes[1].y - 1:
                    v = False
            elif dir == 2:
                if s_t.x != nodes[1].x + 1 or s_t.y != nodes[1].y:
                    v = False
            elif dir == 3:
                if s_t.x != nodes[1].x or s_t.y != nodes[1].y + 1:
                    v = False

            if not v:
                self.display_message("ERROR:", "Route failed for start reg")
                return v
        else:
            if s_t.x != nodes[1].x or s_t.y != nodes[1].y:
                v = False
                self.display_message("ERROR:", "Route failed for start regular")
                return v            

        #check end
        if e_t.tile_type == TileType.IO1 or e_t.tile_type == TileType.IO16:
            if e_t.x != nodes[-2].x or nodes[-2].y != 1:
                v = False
                self.display_message("ERROR:", "Route failed for end io")
                return v
        elif e_t.tile_type == TileType.REG:
            dir = -1
            if "EAST" in nodes[-1].reg_name:
                dir = 0
            elif "SOUTH" in nodes[-1].reg_name:
                dir = 1
            elif "WEST" in nodes[-1].reg_name:
                dir = 2
            elif "NORTH" in nodes[-1].reg_name:
                dir = 3   
            assert(dir >= 0)
            track = int(nodes[-1].reg_name[1])
            
            if e_t.x != nodes[-2].x or e_t.y != nodes[-2].y or track != nodes[-2].track or dir != nodes[-2].side:
                v = False
                self.display_message("ERROR:", "Route failed for end reg")
                return v
        else:
            if e_t.x != nodes[-2].x or e_t.y != nodes[-2].y:
                v = False
                self.display_message("ERROR:", "Route failed for end regular")
                return v 

        return v

    def expand_seg(self, seg_id):
        ind = 0
        seg = self.design.sg[seg_id]
        nodes = seg.nodes
        s_t_id = seg.start_t
        e_t_id = seg.end_t

        s_t = self.design.blk_id_list[s_t_id]
        e_t = self.design.blk_id_list[e_t_id]

        while ind < len(nodes):
            #start
            if ind == 0 and s_t.tile_type == TileType.REG:
                reg_name = nodes[0].reg_name
                dir = -1
                if "EAST" in reg_name:
                    dir = 0
                elif "SOUTH" in reg_name:
                    dir = 1
                elif "WEST" in reg_name:
                    dir = 2
                elif "NORTH" in reg_name:
                    dir = 3   
                rmux_name = str(dir) + "_"+ str(nodes[0].track)
                rmux_n = RouteNode(s_t.x, 
                                   s_t.y, 
                                   route_type=RouteType.RMUX,
                                   bit_width=nodes[0].bit_width,
                                   net_id=nodes[0].net_id,
                                   rmux_name=rmux_name,
                                   kernel=nodes[0].kernel)
                nodes.insert(1, rmux_n)
            
            #end
            elif ind == len(nodes) - 1 and (e_t.tile_type == TileType.IO1 or e_t.tile_type == TileType.IO16):
                if nodes[-2].route_type != RouteType.RMUX:
                    dir = -1
                    if nodes[-2].route_type == RouteType.REG:
                        reg_name = nodes[-2].reg_name

                        if "EAST" in reg_name:
                            dir = 0
                        elif "SOUTH" in reg_name:
                            dir = 1
                        elif "WEST" in reg_name:
                            dir = 2
                        elif "NORTH" in reg_name:
                            dir = 3  
                    else:
                        dir = nodes[-2].side
                    rmux_name = str(dir) + "_"+ str(nodes[-2].track)
                    rmux_n = RouteNode(e_t.x,
                                       1,
                                       route_type=RouteType.RMUX,
                                       bit_width=nodes[0].bit_width,
                                       net_id=nodes[0].net_id,
                                       rmux_name=rmux_name,
                                       kernel=nodes[0].kernel)
                    nodes.insert(-1, rmux_n)
            
            #bt two sb
            elif ind != len(nodes) - 1:
                if nodes[ind].route_type == RouteType.SB and nodes[ind + 1].route_type == RouteType.SB:
                    if nodes[ind].x != nodes[ind+1].x or nodes[ind].y != nodes[ind+1].y:
                        rmux_name = str(nodes[ind].side) + "_"+ str(nodes[ind].track)
                        rmux_n = RouteNode(nodes[ind].x,
                                        nodes[ind].y,
                                        route_type=RouteType.RMUX,
                                        bit_width=nodes[0].bit_width,
                                        net_id=nodes[0].net_id,
                                        rmux_name=rmux_name,
                                        kernel=nodes[0].kernel)
                        nodes.insert(ind + 1, rmux_n)
            
            ind += 1
        

    ################ MESG CODE #################
    def display_text(self, text):
        self.label.display_text(text)
        return
    
    def nets_display(self, text):
        self.net_dis.display_text(text)
        return

    def seg_display(self, text):
        self.seg_dis.display_text(text)
        return

    def display_message(self, titel,mesg):
        QMessageBox.about(self.ui, titel, mesg)
        return
    

if __name__ == '__main__':
    app = QApplication([])
    My_ui = GUI()
    My_ui.ui.show()
    app.exec_()
