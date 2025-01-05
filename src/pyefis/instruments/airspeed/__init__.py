#  Copyright (c) 2013 Neil Domalik, 2018-2019 Garrett Herschleb
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

import sys
import time

from PyQt6.QtGui import *
from PyQt6.QtCore import *
from PyQt6.QtWidgets import *

import pyavtools.fix as fix
import pyefis.hmi as hmi
from pyefis.instruments.NumericalDisplay import NumericalDisplay
from pyefis.instruments import helpers


class Airspeed(QWidget):
    FULL_WIDTH = 400

    def __init__(
        self,
        parent=None,
        font_percent=0.07,
        bg_color=Qt.GlobalColor.black,
        font_family="DejaVu Sans Condensed",
    ):
        super(Airspeed, self).__init__(parent)
        self.setStyleSheet("border: 0px")
        self.font_family = font_family
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.font_percent = font_percent
        self.bg_color = bg_color
        self._airspeed = 0
        self.item = fix.db.get_item("IAS")
        self._airspeed = self.item.value
        self.item.valueChanged[float].connect(self.setAirspeed)
        self.item.oldChanged[bool].connect(self.repaint)
        self.item.badChanged[bool].connect(self.repaint)
        self.item.failChanged[bool].connect(self.repaint)

        # V Speeds need to be init before paint
        self.Vs = self.item.get_aux_value("Vs")
        if self.Vs is None:
            self.Vs = 0
        self.Vs0 = self.item.get_aux_value("Vs0")
        if self.Vs0 is None:
            self.Vs0 = 0
        self.Vno = self.item.get_aux_value("Vno")
        if self.Vno is None:
            self.Vno = 0
        self.Vne = self.item.get_aux_value("Vne")
        if self.Vne is None:
            self.Vne = 200
        self.Vfe = self.item.get_aux_value("Vfe")
        if self.Vfe is None:
            self.Vfe = 0

    def getRatio(self):
        # Return X for 1:x specifying the ratio for this instrument
        return 1

    def paintEvent(self, event):
        w = self.width()
        h = self.height()
        s = w
        if w > h:
            s = h
        dial = QPainter(self)
        dial.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw the Black Background
        dial.fillRect(0, 0, w, h, QColor(self.bg_color))

        # Setup Pens
        f = QFont(self.font_family)
        fs = int(round(self.font_percent * s))
        f.setPixelSize(fs)
        fontMetrics = QFontMetricsF(f)

        dialPen = QPen(QColor(Qt.GlobalColor.white))
        dialPen.setWidthF(s * 0.01)

        needleBrush = QBrush(QColor(Qt.GlobalColor.white))

        vnePen = QPen(QColor(Qt.GlobalColor.red))
        vnePen.setWidthF(s * 0.025)

        vsoPen = QPen(QColor(Qt.GlobalColor.white))
        vsoPen.setWidthF(s * 0.015)

        vnoPen = QPen(QColor(Qt.GlobalColor.green))
        vnoPen.setWidthF(s * 0.015)

        yellowPen = QPen(QColor(Qt.GlobalColor.yellow))
        yellowPen.setWidthF(s * 0.015)

        # Dial Setup

        # VSpeed to angle for drawArc
        Vs0_angle = (-(((self.Vs0 - 30) * 2.5) + 26) + 90) * 16
        Vs_angle = (-(((self.Vs - 30) * 2.5) + 26) + 90) * 16
        Vfe_angle = (-(((self.Vfe - 30) * 2.5) + 25) + 90) * 16
        Vno_angle = (-(((self.Vno - 30) * 2.5) + 25) + 90) * 16
        Vne_angle = (-(((self.Vne - 30) * 2.5) + 25) + 90) * 16

        radius = int(round(min(w, h) * 0.45))
        diameter = radius * 2
        inner_offset = 3
        center_x = w / 2
        center_y = h / 2

        # Vspeeds Arcs
        dial.setPen(vnoPen)
        dial_rect = QRectF(center_x - radius, center_y - radius, diameter, diameter)
        dial.drawArc(dial_rect, qRound(Vs_angle), qRound(-(Vs_angle - Vno_angle)))
        dial.setPen(vsoPen)
        inner_rect = QRectF(
            center_x - radius + inner_offset,
            center_y - radius + inner_offset,
            diameter - inner_offset * 3,
            diameter - inner_offset * 3,
        )
        dial.drawArc(inner_rect, qRound(Vs0_angle), qRound(-(Vs0_angle - Vfe_angle)))
        dial.setPen(yellowPen)
        dial.drawArc(dial_rect, qRound(Vno_angle), qRound(-(Vno_angle - Vne_angle)))
        dial.save()
        dial.setPen(dialPen)
        dial.setFont(f)
        dial.translate(center_x, center_y)
        count = 0
        a_s = 0
        while count < 360:
            if count % 25 == 0 and a_s <= 140:
                dial.drawLine(0, -radius, 0, -(radius - 15))
                x = fontMetrics.horizontalAdvance(str(a_s)) / 2
                y = f.pixelSize()
                dial.drawText(qRound(-x), qRound(-(radius - 15 - y)), str(a_s))
                a_s += 10
                if count == 0:
                    a_s = 30
                    count = count + 19
                    dial.rotate(19)
            elif count % 12.5 == 0 and a_s <= 140:
                dial.drawLine(0, -(radius), 0, -(radius - 10))
            if count == (-Vne_angle / 16) + 90:
                dial.setPen(vnePen)
                dial.drawLine(0, -(radius), 0, -(radius - 15))
                dial.setPen(dialPen)
            dial.rotate(0.5)
            count += 0.5

        if self.item.fail:
            warn_font = QFont(self.font_family, 30, QFont.Weight.Bold)
            dial.resetTransform()
            dial.setPen(QPen(QColor(Qt.GlobalColor.red)))
            dial.setBrush(QBrush(QColor(Qt.GlobalColor.red)))
            dial.setFont(warn_font)
            dial.drawText(0, 0, w, h, Qt.AlignmentFlag.AlignCenter, "XXX")
            dial.restore()
            return

        if self.item.old or self.item.bad:
            warn_font = QFont(self.font_family, 30, QFont.Weight.Bold)
            dial.setPen(QPen(QColor(Qt.GlobalColor.gray)))
            dial.setBrush(QBrush(QColor(Qt.GlobalColor.gray)))
        else:
            dial.setPen(QPen(QColor(Qt.GlobalColor.white)))
            dial.setBrush(QBrush(QColor(Qt.GlobalColor.white)))
        # Needle Movement
        needle = QPolygon(
            [QPoint(5, 0), QPoint(0, +5), QPoint(-5, 0), QPoint(0, -(radius - 15))]
        )

        if self.airspeed <= 30:  # Airspeeds Below 30 Knots
            needle_angle = self._airspeed * 0.83
        else:  # Airspeeds above 30 Knots
            needle_angle = (self._airspeed - 30) * 2.5 + 25

        dial.rotate(needle_angle)
        dial.drawPolygon(needle)

        """ Not sure if this is needed
        if self.item.bad:
            dial.resetTransform()
            dial.setPen (QPen(QColor(255, 150, 0)))
            dial.setBrush (QBrush(QColor(255, 150, 0)))
            dial.setFont (warn_font)
            dial.drawText (0,0,w,h, Qt.AlignmentFlag.AlignCenter, "BAD")
        elif self.item.old:
            dial.resetTransform()
            dial.setPen (QPen(QColor(255, 150, 0)))
            dial.setBrush (QBrush(QColor(255, 150, 0)))
            dial.setFont (warn_font)
            dial.drawText (0,0,w,h, Qt.AlignmentFlag.AlignCenter, "OLD")
        """

        dial.restore()

    def getAirspeed(self):
        return self._airspeed

    def setAirspeed(self, airspeed):
        if airspeed != self._airspeed:
            self._airspeed = airspeed
            self.update()

    airspeed = property(getAirspeed, setAirspeed)

    def setAsOld(self, b):
        pass

    def setAsBad(self, b):
        pass

    def setAsFail(self, b):
        pass


class Airspeed_Tape(QGraphicsView):
    def __init__(
        self, parent=None, font_percent=None, font_family="DejaVu Sans Condensed"
    ):
        super(Airspeed_Tape, self).__init__(parent)
        self.myparent = parent
        self.font_family = font_family
        self.font_mask = "000"
        self.update_period = None
        self.font_percent = font_percent
        # self.setStyleSheet("background-color: rgba(32, 32, 32, 0%)")
        self.setStyleSheet("background: transparent")
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.item = fix.db.get_item("IAS")
        self._airspeed = self.item.value

        # V Speeds
        self.Vs = self.item.get_aux_value("Vs")
        if self.Vs is None:
            self.Vs = 0
        self.Vs0 = self.item.get_aux_value("Vs0")
        if self.Vs0 is None:
            self.Vs0 = 0
        self.Vno = self.item.get_aux_value("Vno")
        if self.Vno is None:
            self.Vno = 0
        self.Vne = self.item.get_aux_value("Vne")
        if self.Vne is None:
            self.Vne = 200
        self.Vfe = self.item.get_aux_value("Vfe")
        if self.Vfe is None:
            self.Vfe = 0

        self.max = int(round(self.Vne * 1.25))

        self.backgroundOpacity = 0.3
        self.foregroundOpacity = 0.6
        self.pph = 10  # Pixels per unit
        self.fontsize = 15
        self.majorDiv = 10
        self.minorDiv = 5

    def resizeEvent(self, event):
        if self.font_percent:
            self.fontsize = qRound(self.width() * self.font_percent)
        self.pph = self.height() / 100
        w = self.width()
        h = self.height()
        self.markWidth = w / 5
        f = QFont(self.font_family)
        if self.font_mask:
            self.fontsize = helpers.fit_to_mask(
                self.width() * 0.50,
                self.height() * 0.05,
                self.font_mask,
                self.font_family,
            )
            f.setPointSizeF(self.fontsize)
        else:
            f.setPixelSize(self.fontsize)
        tape_height = self.max * self.pph + h
        tape_start = self.max * self.pph + h / 2

        dialPen = QPen(QColor(Qt.GlobalColor.white))

        self.scene = QGraphicsScene(0, 0, w, tape_height)
        x = self.scene.addRect(
            0, 0, w, tape_height, QPen(QColor(32, 32, 32)), QBrush(QColor(32, 32, 32))
        )
        x.setOpacity(self.backgroundOpacity)

        # Add Markings
        # Green Bar
        r = QRectF(
            QPointF(0, -self.Vno * self.pph + tape_start),
            QPointF(self.markWidth, -self.Vs0 * self.pph + tape_start),
        )
        x = self.scene.addRect(r, QPen(QColor(0, 155, 0)), QBrush(QColor(0, 155, 0)))
        x.setOpacity(self.foregroundOpacity)

        # White Bar
        r = QRectF(
            QPointF(self.markWidth / 2, -self.Vfe * self.pph + tape_start),
            QPointF(self.markWidth, -self.Vs0 * self.pph + tape_start),
        )
        x = self.scene.addRect(r, QPen(Qt.GlobalColor.white), QBrush(Qt.GlobalColor.white))
        x.setOpacity(self.foregroundOpacity)

        # Yellow Bar
        r = QRectF(
            QPointF(0, -self.Vno * self.pph + tape_start),
            QPointF(self.markWidth, -self.Vne * self.pph + tape_start),
        )
        x = self.scene.addRect(r, QPen(Qt.GlobalColor.yellow), QBrush(Qt.GlobalColor.yellow))
        x.setOpacity(self.foregroundOpacity)

        # Draw the little white lines and the text
        for i in range(self.max, -1, -1):
            if i % self.majorDiv == 0:
                l = self.scene.addLine(
                    0,
                    (-i * self.pph) + tape_start,
                    w / 2,
                    (-i * self.pph) + tape_start,
                    dialPen,
                )
                l.setOpacity(self.foregroundOpacity)
                t = self.scene.addText(str(i))
                t.setFont(f)
                self.scene.setFont(f)
                t.setDefaultTextColor(QColor(Qt.GlobalColor.white))
                t.setX(w - t.boundingRect().width())
                t.setY(((-i * self.pph) + tape_start) - t.boundingRect().height() / 2)
                t.setOpacity(self.foregroundOpacity)
            elif i % self.minorDiv == 0:
                l = self.scene.addLine(
                    0,
                    (-i * self.pph) + tape_start,
                    w / 3,
                    (-i * self.pph) + tape_start,
                    dialPen,
                )
                l.setOpacity(self.foregroundOpacity)
        # Red Line
        vnePen = QPen(QColor(Qt.GlobalColor.red))
        vnePen.setWidth(4)
        l = self.scene.addLine(
            0,
            -self.Vne * self.pph + tape_start,
            30,
            -self.Vne * self.pph + tape_start,
            vnePen,
        )
        l.setOpacity(self.foregroundOpacity)

        self.numerical_display = NumericalDisplay(self)
        nbh = w / 2
        self.numerical_display.resize(qRound(w / 2), qRound(nbh))
        self.numeric_box_pos = QPoint(qRound(w - w / 2), qRound(h / 2 - nbh / 2))
        self.numerical_display.move(self.numeric_box_pos)
        self.numeric_box_pos.setY(qRound(self.numeric_box_pos.y() + nbh / 2))
        self.numerical_display.show()
        self.numerical_display.value = self._airspeed
        self.setAsOld(self.item.old)
        self.setAsBad(self.item.bad)
        self.setAsFail(self.item.fail)

        self.setScene(self.scene)
        self.centerOn(self.scene.width() / 2, -self._airspeed * self.pph + tape_start)
        self.item.valueChanged[float].connect(self.setAirspeed)
        self.item.oldChanged[bool].connect(self.setAsOld)
        self.item.badChanged[bool].connect(self.setAsBad)
        self.item.failChanged[bool].connect(self.setAsFail)

    def redraw(self):
        if not self.isVisible():
            return
        tape_start = self.max * self.pph + self.height() / 2

        self.resetTransform()
        self.centerOn(self.scene.width() / 2, -self._airspeed * self.pph + tape_start)
        self.numerical_display.value = self._airspeed

    #  Index Line that doesn't move to make it easy to read the airspeed.
    def paintEvent(self, event):
        super(Airspeed_Tape, self).paintEvent(event)
        w = self.width()
        h = self.height()
        p = QPainter(self.viewport())
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        marks = QPen(Qt.GlobalColor.white, 1)
        p.translate(self.numeric_box_pos.x(), self.numeric_box_pos.y())
        p.setPen(marks)
        p.setBrush(QBrush(Qt.GlobalColor.black))
        triangle_size = w / 8
        p.drawConvexPolygon(
            QPolygon(
                [
                    QPoint(0, qRound(-triangle_size - 3)),
                    QPoint(0, qRound(triangle_size - 2)),
                    QPoint(qRound(-triangle_size), -1),
                ]
            )
        )

    def getAirspeed(self):
        return self._airspeed

    def setAirspeed(self, airspeed):
        if airspeed != self._airspeed:
            self._airspeed = airspeed
            self.redraw()

    airspeed = property(getAirspeed, setAirspeed)

    def setAsOld(self, b):
        self.numerical_display.old = b

    def setAsBad(self, b):
        self.numerical_display.bad = b

    def setAsFail(self, b):
        self.numerical_display.fail = b

    # We don't want this responding to keystrokes
    def keyPressEvent(self, event):
        pass

    # Don't want it acting with the mouse scroll wheel either
    def wheelEvent(self, event):
        pass


class Airspeed_Box(QWidget):
    """Represents a simple numeric display type gauge.  The benefit of using this
    over a normal text display is that this will change colors properly when
    limits are reached or when failures occur"""

    def __init__(self, parent=None, font_family="DejaVu Sans Condensed"):
        super(Airspeed_Box, self).__init__(parent)
        self.font_family = font_family
        self.modes = ["TAS", "GS", "IAS"]
        self._modeIndicator = 0
        self.fix_items = [fix.db.get_item(mode) for mode in self.modes]
        self.fix_item = self.fix_items[self._modeIndicator]
        self.valueText = str(int(self.fix_item.value))
        self.fix_item.valueChanged[float].connect(self.setASData)

        self.alignment = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        self.valueAlignment = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        self.small_font_percent = 0.4
        self.color = Qt.GlobalColor.white
        self.modeText = self.modes[self._modeIndicator]
        hmi.actions.setAirspeedMode.connect(self.setMode)

    def resizeEvent(self, event):
        self.bigFont = QFont(self.font_family)
        self.bigFont.setPixelSize(qRound(self.height() * self.small_font_percent))
        self.smallFont = QFont(self.font_family)
        self.smallFont.setPixelSize(qRound(self.height() * self.small_font_percent))
        qm = QFontMetrics(self.smallFont)

        self.modeTextRect = QRectF(0, 0, self.width() - 5, self.height() * 0.4)
        self.valueTextRect = QRectF(
            0, self.height() * 0.5, self.width() - 5, self.height() * 0.4
        )

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        pen = QPen()
        pen.setWidth(1)
        pen.setCapStyle(Qt.PenCapStyle.FlatCap)
        p.setPen(pen)

        # Draw Mode
        pen.setColor(self.color)
        p.setPen(pen)
        p.setFont(self.bigFont)
        opt = QTextOption(self.alignment)
        p.drawText(self.modeTextRect, self.modeText, opt)

        # Draw Value
        p.setFont(self.smallFont)
        opt = QTextOption(self.valueAlignment)
        p.drawText(self.valueTextRect, self.valueText, opt)

    def setMode(self, Mode):
        if Mode == "":
            self.fix_item.valueChanged[float].disconnect(self.setASData)
            self._modeIndicator += 1
            if self._modeIndicator == 3:
                self._modeIndicator = 0
        else:
            if Mode != self._modeIndicator:
                self.fix_item.valueChanged[float].disconnect(self.setASData)
                if Mode == 0:
                    self._modeIndicator = 0
                elif Mode == 1:
                    self._modeIndicator = 1
                elif Mode == 2:
                    self._modeIndicator = 2

        self.modeText = self.modes[self._modeIndicator]
        self.fix_item = self.fix_items[self._modeIndicator]
        self.fix_item.valueChanged[float].connect(self.setASData)
        self.setASData(self.fix_item.value)
        self.update()

    def setASData(self, d):
        if self.fix_item.fail:
            self.valueText = "XXX"
        elif self.fix_item.bad or self.fix_item.old:
            self.valueText = ""
        else:
            self.valueText = str(int(round(d)))
        if self.isVisible():
            self.update()
