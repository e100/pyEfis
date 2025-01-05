#  Copyright (c) 2013 Phil Birkelbach
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

from PyQt6.QtGui import *
from PyQt6.QtCore import *
from PyQt6.QtWidgets import *


from .abstract import AbstractGauge
from pyefis.instruments import helpers

class HorizontalBar(AbstractGauge):
    def __init__(self, parent=None, min_size=True, font_family="DejaVu Sans Condensed"):
        super(HorizontalBar, self).__init__(parent)
        self.font_family = font_family
        if min_size:
            self.setMinimumSize(100, 50)
        self.show_value = True
        self.show_units = True
        self.show_name = True
        self.segments = 0 
        self.segment_gap_percent = 0.01
        self.segment_alpha = 180
        self.bar_divisor = 4.5
    def getRatio(self):
        # Return X for 1:x specifying the ratio for this instrument
        return 2

    def resizeEvent(self, event):
        self.bigFont = QFont(self.font_family)
        self.section_size = self.height() / 12
        self.bigFont.setPixelSize( qRound(self.section_size * 4))
        if self.font_mask:
            self.bigFont.setPointSizeF(helpers.fit_to_mask(self.width()-5, self.section_size * 4, self.font_mask, self.font_family))
        self.smallFont = QFont(self.font_family)
        self.smallFont.setPixelSize(qRound(self.section_size * 2))
        if self.name_font_mask:
            self.smallFont.setPointSizeF(helpers.fit_to_mask(self.width(), self.section_size * 2.4, self.name_font_mask, self.font_family))
        self.unitsFont = QFont(self.font_family)
        self.unitsFont.setPixelSize(qRound(self.section_size * 2))
        if self.units_font_mask:
            self.unitsFont.setPointSizeF(helpers.fit_to_mask(self.width(), self.section_size * 2.4, self.name_font_mask, self.font_family))

        self.barHeight = self.section_size * self.bar_divisor
        self.barTop = self.section_size * 2.7
        self.nameTextRect = QRectF(1, 0, self.width(), self.section_size * 2.4)
        self.valueTextRect = QRectF(1, self.section_size * 8,
                                    self.width()-5, self.section_size * 4)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen()
        pen.setWidth(1)
        pen.setCapStyle(Qt.PenCapStyle.FlatCap)
        #pen.setColor(self.textColor)
        #p.setPen(pen)
        p.setFont(self.smallFont)
        if self.show_name: 
            if self.name_font_ghost_mask:
                opt = QTextOption(Qt.AlignmentFlag.AlignLeft)
                alpha = self.textColor.alpha()
                self.textColor.setAlpha(self.font_ghost_alpha)
                pen.setColor(self.textColor)
                p.setPen(pen)
                p.drawText(self.nameTextRect, self.name_font_ghost_mask, opt)
                self.textColor.setAlpha(alpha)
            pen.setColor(self.textColor)
            p.setPen(pen)
            p.drawText(self.nameTextRect, self.name)

        # Units
        p.setFont(self.unitsFont)
        opt = QTextOption(Qt.AlignmentFlag.AlignRight)
        if self.show_units: 
            if self.units_font_ghost_mask:
                alpha = self.textColor.alpha()
                self.textColor.setAlpha(self.font_ghost_alpha)
                pen.setColor(self.textColor)
                p.setPen(pen)
                p.drawText(self.valueTextRect, self.units_font_ghost_mask, opt)
                self.textColor.setAlpha(alpha)
            pen.setColor(self.textColor)
            p.setPen(pen)
            p.drawText(self.valueTextRect, self.units, opt)

        # Main Value
        p.setFont(self.bigFont)
        #pen.setColor(self.valueColor)
        #p.setPen(pen)
        opt = QTextOption(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom)
        if self.show_value: 
            if self.font_ghost_mask:
                alpha = self.valueColor.alpha()
                self.valueColor.setAlpha(self.font_ghost_alpha)
                pen.setColor(self.valueColor)
                p.setPen(pen)
                p.drawText(self.valueTextRect, self.font_ghost_mask, opt)
                self.valueColor.setAlpha(alpha)
            pen.setColor(self.valueColor)
            p.setPen(pen)
            p.drawText(self.valueTextRect, self.valueText, opt)

        # Draws the bar
        p.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        pen.setColor(self.safeColor)
        brush = self.safeColor
        p.setPen(pen)
        p.setBrush(brush)
        p.drawRect(QRectF(0, self.barTop, self.width(), self.barHeight))
        pen.setColor(self.warnColor)
        brush = self.warnColor
        p.setPen(pen)
        p.setBrush(brush)
        if(self.lowWarn):
            p.drawRect(QRectF(0, self.barTop,
                              self.interpolate(self.lowWarn, self.width()),
                              self.barHeight))
        if(self.highWarn):
            x = self.interpolate(self.highWarn, self.width())
            p.drawRect(QRectF(x, self.barTop,
                              self.width() - x, self.barHeight))
        pen.setColor(self.alarmColor)
        brush = self.alarmColor
        p.setPen(pen)
        p.setBrush(brush)
        if(self.lowAlarm):
            p.drawRect(QRectF(0, self.barTop,
                              self.interpolate(self.lowAlarm, self.width()),
                              self.barHeight))
        if(self.highAlarm):
            x = self.interpolate(self.highAlarm, self.width())
            p.drawRect(QRectF(x, self.barTop,
                              self.width() - x, self.barHeight))


        # Draw black bars to create segments
        if self.segments > 0:
            segment_gap = self.width() * self.segment_gap_percent
            segment_size = (self.width() - (segment_gap * (self.segments - 1)))/self.segments
            p.setRenderHint(QPainter.RenderHint.Antialiasing, False)
            pen.setColor(Qt.GlobalColor.black)
            p.setPen(pen)
            p.setBrush(Qt.GlobalColor.black)
            for segment in range(self.segments - 1):
                seg_left = ((segment + 1) * segment_size) + (segment * segment_gap)
                p.drawRect(QRectF(seg_left, self.barTop, segment_gap, self.barHeight))

        # Indicator Line
        pen.setColor(QColor(Qt.GlobalColor.darkGray))
        brush = QBrush(self.penColor)
        pen.setWidth(1)
        p.setPen(pen)
        p.setBrush(brush)
        x = self.interpolate(self._value, self.width())
        if x < 0: x = 0
        if x > self.width(): x = self.width()
        if not self.segments > 0:
            p.drawRect(QRectF(x-2, self.barTop-4, 4, self.barHeight+8))
        else:
            # IF segmented, darken the top part of the bars from the line up
            pen.setColor(QColor(0, 0, 0, self.segment_alpha))
            p.setPen(pen)
            p.setBrush(QColor(0, 0, 0, self.segment_alpha))
            p.drawRect(QRectF(x, self.barTop, self.width() - x, self.barHeight))

