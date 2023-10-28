#  Copyright (c) 2013 Phil Birkelbach; 2018-2019 Garrett Herschleb
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

from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *

import math
import time
import logging

import pyavtools.fix as fix
from pyefis import common

log = logging.getLogger(__name__)

# TODO:
#   Check TAS quality and revert to turn rate indication
#   Fix quality indications
#   Add quality flags to indicate the actual failures
#   Remove internal assignments of database items.  Should be a normal
#      Qt widget and these things done externally.
#   Add configuration for bank angle tick sizes

class AI(QGraphicsView):
    def __init__(self, parent=None,data=None):
        super(AI, self).__init__(parent)
        self.myparent = parent

        # The following information is meant to be configurable from the screen
        # definition file
        self.fontSize = 30
        # Number of degrees shown from top to bottom
        self.pitchDegreesShown = 60
        # Pitch tick mark configurations
        self.minorDiv = 1   # Degrees between minor divisions
        self.majorDiv = 5  # Degrees between major divisions
        self.numberedDiv = 10 # Degrees between numbered divisions
        # Line widths of the pitch tick marks
        self.minorDivWidth = 10
        self.majorDivWidth = 40
        self.numberedDivWidth = 50
        self.visiblePitchAngle = 15 # Amount of visible pitch angle marks
        self.pitchOpacity = 0.6
        # Bank angle tick indicators
        self.bankMarkSize = 10
        # Standard rate turn bank angle indicators.
        self.drawBankMarkers = True
        self.bankAngleRadius = None # Radius of the bank angle markings
        self.bankAngleMaximum = 25  # Largest bank angle that will be indicated

        self.setStyleSheet("border: 0px")
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setRenderHint(QPainter.Antialiasing)
        self.setFocusPolicy(Qt.NoFocus)

        if data:
            pitch = data['PITCH']
            roll = data["ROLL"]
            alat = data["ALAT"]
            tas = data["TAS"]
            self._pitchAngle = pitch.value
            self._rollAngle = roll.value
            self._AIOld = roll.old
            self._AIBad = roll.bad
            self._AIFail = roll.fail
            self._latAccel = alat.value
            self._tas = tas.value

        else:
            pitch = fix.db.get_item("PITCH")
            pitch.valueChanged[float].connect(self.setPitchAngle)
            pitch.oldChanged[bool].connect(self.setAIOld)
            pitch.badChanged[bool].connect(self.setAIBad)
            pitch.failChanged[bool].connect(self.setAIFail)
            self._pitchAngle = pitch.value
            roll = fix.db.get_item("ROLL")
            roll.valueChanged[float].connect(self.setRollAngle)
            roll.oldChanged[bool].connect(self.setAIOld)
            roll.badChanged[bool].connect(self.setAIBad)
            roll.failChanged[bool].connect(self.setAIFail)
            self._rollAngle = roll.value
            self._AIOld = roll.old
            self._AIBad = roll.bad
            self._AIFail = roll.fail
            alat = fix.db.get_item("ALAT")
            alat.valueChanged[float].connect(self.setLateralAcceleration)
            self._latAccel = alat.value
            tas = fix.db.get_item("TAS")
            tas.valueChanged[float].connect(self.setTrueAirspeed)
            self._tas = tas.value
        # We store all the pitch tick marks and text in a list so that
        # we can adjust the opacity of the items.
        self.pitchItems = []

    def resizeEvent(self, event):
        #Setup the scene that we use for the background of the AI
        sceneHeight = self.height() * 4.5
        sceneWidth = math.sqrt(self.width() * self.width() +
                               self.height() * self.height())
        self.pixelsPerDeg = self.height() / self.pitchDegreesShown
        self.scene = QGraphicsScene(0, 0, sceneWidth, sceneHeight)
        # Setup default values
        if self.bankAngleRadius is None:
            self.bankAngleRadius = self.height() / 3
        # Get a failure scene ready in case it's needed
        self.fail_scene = QGraphicsScene(0, 0, sceneWidth, sceneHeight)
        self.fail_scene.addRect(0,0, sceneWidth, sceneHeight, QPen(QColor(Qt.white)), QBrush(QColor(50,50,50)))
        font = QFont("FixedSys", 80, QFont.Bold)
        t = self.fail_scene.addSimpleText("XXX", font)
        t.setPen (QPen(QColor(Qt.red)))
        t.setBrush (QBrush(QColor(Qt.red)))
        r = t.boundingRect()
        t.setPos ((sceneWidth-r.width())/2, (sceneHeight-r.height())/2)

        #Draw the Blue and Brown rectangles
        gradientBlue = QLinearGradient(0, 0, 0, sceneHeight / 2)
        gradientBlue.setColorAt(0.7, QColor(0, 51, 102))
        gradientBlue.setColorAt(1.0, QColor(51, 153, 255))
        gradientBlue.setSpread(0)
        self.blue_pen = QPen(QColor(Qt.blue))
        self.gblue_brush = QBrush(gradientBlue)
        gradientLGray = QLinearGradient(0, 0, 0, sceneHeight / 2)
        gradientLGray.setColorAt(0.7, QColor(100, 100, 100))
        gradientLGray.setColorAt(1.0, QColor(153, 153, 153))
        gradientLGray.setSpread(0)
        self.gray_sky = QBrush(gradientLGray)
        if self._AIOld or self._AIBad:
            brush = self.gray_sky
        else:
            brush = self.gblue_brush
        self.sky_rect = self.scene.addRect(0, 0, sceneWidth, sceneHeight / 2, self.blue_pen, brush)
        self.setScene(self.scene)
        gradientBrown = QLinearGradient(0, sceneHeight / 2, 0, sceneHeight)
        gradientBrown.setColorAt(0.0, QColor(105, 46, 1))
        gradientBrown.setColorAt(0.3, QColor(244, 164, 96))
        gradientBrown.setSpread(0)
        self.brown_pen = QPen(QColor(160, 82, 45))  # Brown Color
        self.gbrown_brush = QBrush(gradientBrown)
        gradientDGray = QLinearGradient(0, sceneHeight / 2, 0, sceneHeight)
        gradientDGray.setColorAt(0.0, QColor(20, 20, 20))
        gradientDGray.setColorAt(0.2, QColor(75, 75, 75))
        gradientDGray.setSpread(0)
        self.gray_land = QBrush(gradientDGray)
        if self._AIOld or self._AIBad:
            brush = self.gray_land
        else:
            brush = self.gbrown_brush
        self.land_rect = self.scene.addRect(0, sceneHeight / 2 + 1, sceneWidth, sceneHeight,
                           self.brown_pen, brush)

        self.setScene(self.scene)

        #Draw the main horizontal line
        pen = QPen(QColor(Qt.white))
        pen.setWidth(2)
        self.scene.addLine(0, sceneHeight / 2, sceneWidth, sceneHeight / 2, pen)
        # draw the degree hash marks
        pen.setColor(Qt.white)
        w = self.scene.width()
        h = self.scene.height()
        f = QFont()
        f.setPixelSize(self.fontSize)

        # Draw the tick mark lines on the scene
        for i in range(-90, 91):
            if i == 0:  # Don't draw a line at zero
                pass
            elif i % self.numberedDiv == 0:
                left = w / 2 - self.numberedDivWidth / 2
                right = w / 2 + self.numberedDivWidth / 2
                y = h / 2 - self.pixelsPerDeg * i

                l = self.scene.addLine(left, y, right, y, pen)
                l.setZValue(1)
                self.pitchItems.append((i, l))
                t = self.scene.addText(str(i))
                t.setFont(f)
                self.scene.setFont(f)
                t.setDefaultTextColor(Qt.white)
                t.setX(right + 5)
                t.setY(y - t.boundingRect().height() / 2)
                t.setZValue(1)
                self.pitchItems.append((i, t))

                t = self.scene.addText(str(i))
                t.setFont(f)
                self.scene.setFont(f)
                t.setDefaultTextColor(Qt.white)
                t.setX(left - (t.boundingRect().width() + 5))
                t.setY(y - t.boundingRect().height() / 2)
                t.setZValue(1)
                self.pitchItems.append((i, t))

            elif i % self.majorDiv == 0:
                left = w / 2 - self.majorDivWidth / 2
                right = w / 2 + self.majorDivWidth / 2
                y = h / 2 - self.pixelsPerDeg * i
                l = self.scene.addLine(left, y, right, y, pen)
                l.setZValue(1)
                self.pitchItems.append((i, l))

            elif i % self.minorDiv == 0:
                left = w / 2 - self.minorDivWidth / 2
                right = w / 2 + self.minorDivWidth / 2
                y = h / 2 - self.pixelsPerDeg * i
                l = self.scene.addLine(left, y, right, y, pen)
                l.setZValue(1)
                self.pitchItems.append((i, l))
        self.setPitchItems()

        # Draws the static overlay stuff to a pixmap
        self.map = QPixmap(self.width(), self.height())
        self.map.fill(Qt.transparent)
        p = QPainter(self.map)
        p.setRenderHint(QPainter.Antialiasing)
        # change width and height to the view instead of the scene
        w = self.width()
        h = self.height()
        r = self.bankAngleRadius
        p.setPen(QColor(Qt.black))
        p.setBrush(QColor(Qt.yellow))
        p.drawRect(QRectF(w / 4, h / 2 - 3, w / 6, 6))
        p.drawRect(QRectF(w - w / 4 - w / 6, h / 2 - 3, w / 6, 6))
        p.drawEllipse(QRectF(w / 2 - 3, h / 2 - 3, 9, 9))
        # p.setPen(QColor(Qt.black))
        # p.setBrush(QColor(Qt.white))

        m = self.bankMarkSize
        p.setBrush(QColor(Qt.white))
        p.translate(w / 2, h/2 - r)
        triangle = QPolygonF([QPointF(m,  m*2),
                             QPointF(-m, m*2),
                             QPointF(0,  m/2)])
        p.drawPolygon(triangle)


        self.overlay = self.map.toImage()

        self.redraw()

    # the pitchItems list contains a tuple that represents all of the tick marks
    # and text of the Pitch graducations.  The first item of the tuple is the angle
    # and the second is the item reference.  We use this to make the tick marks
    # disappear when they are a certain distance from the current pitch angle
    def setPitchItems(self):
        for each in self.pitchItems:
            if abs(each[0] - self._pitchAngle) < self.visiblePitchAngle:
                each[1].setOpacity(self.pitchOpacity)
            else:
                each[1].setOpacity(0)

    def redraw(self):
        self.resetTransform()
        self.centerOn(self.scene.width() / 2,
                      self.scene.height() / 2 +
                      self._pitchAngle * self.pixelsPerDeg * - 1.0)
        self.rotate(self._rollAngle * -1.0)

# We use the paintEvent to draw on the viewport the parts that aren't moving.
    def paintEvent(self, event):
        super(AI, self).paintEvent(event)
        w = self.width()
        h = self.height()
        r = self.bankAngleRadius
        m = self.bankMarkSize
        p = QPainter(self.viewport())
        p.setRenderHint(QPainter.Antialiasing)
        # Put the static overlay image on the view
        p.drawImage(self.rect(), self.overlay)

        pen = QPen(Qt.white)
        pen.setWidth(1)
        p.setPen(pen)
        p.setBrush(QColor(Qt.white))
        marks = QPen(Qt.white)

        p.translate(w / 2, h / 2)

        # Slip / Skid ball
        p.setPen(QColor(Qt.black))
        p.setBrush(QColor(Qt.white))
        p.drawEllipse(QPointF(self._latAccel * -m*12, -r + m*3), m*0.8, m*0.8)

        p.rotate(self._rollAngle * -1.0)
        # Add moving Bank Angle Markers
        marks.setWidth(2)
        p.setPen(marks)
        p.setBrush(QColor(Qt.white))
        smallMarks = [10, 20, 45]
        largeMarks = [30, 60]
        shortLine = QLineF(0, -r, 0, -(r-m))
        longLine = QLineF(0, -(r+m), 0, -(r-m))
        for angle in smallMarks:
            p.rotate(angle)
            p.drawLine(shortLine)
            p.rotate(- 2 * angle)
            p.drawLine(shortLine)
            p.rotate(angle)
        for angle in largeMarks:
            p.rotate(angle)
            p.drawLine(longLine)
            p.rotate(- 2 * angle)
            p.drawLine(longLine)
            p.rotate(angle)
        triangle = QPolygonF([QPointF(m/2, -(r+m/2)),
                             QPointF(-m/2, -(r+m/2)),
                             QPointF(0, -(r - m/2))])
        p.drawPolygon(triangle)
        # Draw standard rate turn markers
        if self.drawBankMarkers:
            a = math.degrees(math.atan(self._tas/364.0))
            if a > self.bankAngleMaximum:
                a = self.bankAngleMaximum
            diamond = QPolygonF([QPointF(0, -r),
                                QPointF(-m*0.8, -(r+m*0.8)),
                                QPointF(-0, -r - m*1.6),
                                QPointF(m*0.8, -(r+m*0.8))])
            p.setBrush(Qt.transparent)
            p.rotate(a)
            p.drawPolygon(diamond)
            p.rotate(-2 * a)
            p.drawPolygon(diamond)

    # We don't want this responding to keystrokes
    def keyPressEvent(self, event):
        pass

    # Don't want it acting with the mouse scroll wheel either
    def wheelEvent(self, event):
        pass

    def setRollAngle(self, angle):
        if angle != self._rollAngle and self.isVisible() and (not self._AIFail):
            self._rollAngle = common.bounds(-180, 180, angle)
            self.redraw()

    def getRollAngle(self):
        return self._rollAngle

    rollAngle = property(getRollAngle, setRollAngle)

    def setLateralAcceleration(self, value):
        if value != self._latAccel and self.isVisible():
            self._latAccel = common.bounds(-0.3, 0.3, value)
            self.update()

    def setTrueAirspeed(self, value):
        if value != self._tas and self.isVisible():
            self._tas = value
            self.update()


    def setAIFail(self, fail):
        log.debug("Set AI Fail")
        if fail != self._AIFail:
            self._AIFail = fail
            if hasattr(self, 'fail_scene'):
                if fail:
                    self.resetTransform()
                    self.setScene (self.fail_scene)
                else:
                    self.setScene (self.scene)
                    # Initially set to grey
                    # we may have old data while recovering
                    if hasattr(self, 'sky_rect'):
                        self.sky_rect.setBrush (self.gray_sky)
                        self.land_rect.setBrush (self.gray_land)
                    self.redraw()

    def setAIOld(self, old):
        log.debug("Set AI Old")
        if old != self._AIOld:
            self._AIOld = old
            if hasattr(self, 'sky_rect'):
                if old:
                    self.sky_rect.setBrush (self.gray_sky)
                    self.land_rect.setBrush (self.gray_land)
                    #self.old_text.show()
                else:
                    self.sky_rect.setBrush (self.gblue_brush)
                    self.land_rect.setBrush (self.gbrown_brush)
                    #self.old_text.hide()
                    self.redraw()

    def setAIBad(self, bad):
        log.debug("Set AI Bad")
        if bad != self._AIBad:
            self._AIBad = bad
            if hasattr(self, 'sky_rect'):
                if bad:
                    self.sky_rect.setBrush (self.gray_sky)
                    self.land_rect.setBrush (self.gray_land)
                    #self.bad_text.show()
                else:
                    self.sky_rect.setBrush (self.gblue_brush)
                    self.land_rect.setBrush (self.gbrown_brush)
                    #self.bad_text.hide()
                    self.redraw()

    def setPitchAngle(self, angle):
        if angle != self._pitchAngle and self.isVisible() and (not self._AIFail):
            self._pitchAngle = common.bounds(-90, 90, angle)
            self.setPitchItems()
            self.redraw()

    def getPitchAngle(self):
        return self._pitchAngle

    def setData(self,item,value):
        if item == 'PITCH':
            self.setPitchAngle(value)
        elif item == 'ROLL':
            self.setRollAngle(value)
        elif item == 'ALAT':
            self.setLateralAcceleration(value)
        elif item == 'TAS':
            self.setTrueAirspeed(value)

    pitchAngle = property(getPitchAngle, setPitchAngle)


class FDTarget(QGraphicsView):
    def __init__(self, center, pixelsPerDeg, parent=None):
        super(FDTarget, self).__init__(parent)
        self.setStyleSheet("background-color: rgba(0, 0, 0, 0%); border: 0px")
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setRenderHint(QPainter.Antialiasing)
        self.setFocusPolicy(Qt.NoFocus)
        self.aicenter = center
        self.pixelsPerDeg = pixelsPerDeg

    def resizeEvent(self, event):
        self.w = self.width()
        self.h = self.height()
        polyheight = 8
        self.poly_points = [(-self.w/2,-polyheight/2)
                           ,( self.w/2,-polyheight/2)
                           ,( self.w/2, polyheight/2)
                           ,(-self.w/2, polyheight/2)]

        self.scene = QGraphicsScene(0, 0, self.w*2, self.w*2)
        pen = QPen(QColor(Qt.black))
        brush = QBrush (QColor (Qt.magenta))
        ps = [QPointF (x,y) for x,y in self.poly_points]
        fdpoly = QPolygonF (ps)
        self.poly = self.scene.addPolygon (fdpoly, pen, brush)
        self.poly.setX(self.w)
        self.poly.setY(self.w)

        self.setScene(self.scene)
        self.aicenter.setX (self.aicenter.x()-self.w/2)
        self.aicenter.setY (self.aicenter.y()-self.h/2)
        self.centerOn (self.w, self.w)

    def update(self, fdpitch, fdroll):
        self.move (self.aicenter.x(), (self.aicenter.y() - fdpitch * self.pixelsPerDeg))
        roll = fdroll * math.pi / 180
        sinroll = math.sin(roll)
        cosroll = math.cos(roll)
        ps = [QPointF (cosroll*x - sinroll*y, sinroll*x + cosroll*y) for x,y in self.poly_points]
        fdpoly = QPolygonF (ps)
        self.poly.setPolygon (fdpoly)
