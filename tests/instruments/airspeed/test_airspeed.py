import pytest
from unittest import mock
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QBrush, QPaintEvent
from pyefis.instruments import airspeed
import pyefis.hmi as hmi


@pytest.fixture
def app(qtbot):
    test_app = QApplication.instance()
    if test_app is None:
        test_app = QApplication([])
    return test_app

def test_aux_not_set_for_airspeed(fix, qtbot):
    fix.db.get_item("IAS").set_aux_value("Vs", None)
    fix.db.get_item("IAS").set_aux_value("Vs0", None)
    fix.db.get_item("IAS").set_aux_value("Vno", None)
    fix.db.get_item("IAS").set_aux_value("Vne", None)
    fix.db.get_item("IAS").set_aux_value("Vfe", None)
    widget = airspeed.Airspeed()
    assert widget.Vs == 0
    assert widget.Vs0 == 0
    assert widget.Vno == 0
    assert widget.Vne == 200
    assert widget.Vfe == 0

def test_aux_not_set_for_airspeed_tape(fix, qtbot):
    fix.db.get_item("IAS").set_aux_value("Vs", None)
    fix.db.get_item("IAS").set_aux_value("Vs0", None)
    fix.db.get_item("IAS").set_aux_value("Vno", None)
    fix.db.get_item("IAS").set_aux_value("Vne", None)
    fix.db.get_item("IAS").set_aux_value("Vfe", None)
    widget = airspeed.Airspeed_Tape()
    assert widget.Vs == 0
    assert widget.Vs0 == 0
    assert widget.Vno == 0
    assert widget.Vne == 200
    assert widget.Vfe == 0

def test_numerical_airspeed(fix, qtbot):
    widget = airspeed.Airspeed()
    assert widget.getRatio() == 1
    qtbot.addWidget(widget)
    widget.resize(201, 200)
    widget.show()
    qtbot.waitExposed(widget)
    qtbot.wait(500)
    widget.resize(200, 201)
    widget.paintEvent(None)
    assert widget.item.key == "IAS"
    assert widget.Vs == 45
    fix.db.get_item("IAS").fail = True
    fix.db.get_item("IAS").fail = False
    fix.db.get_item("IAS").old = True
    fix.db.get_item("IAS").old = False
    fix.db.set_value("IAS", "20")
    widget.paintEvent(None)
    widget.setAsOld(True)
    widget.setAsBad(True)
    widget.setAsFail(True)
    assert widget.getAirspeed() == 20
    # Test branch
    widget.setAirspeed(20)
    widget.setAirspeed(41)
    assert widget._airspeed == 41
    qtbot.wait(200)


def test_numerical_airspeed_tape(qtbot):
    widget = airspeed.Airspeed_Tape(font_percent=0.5)
    qtbot.addWidget(widget)
    widget.redraw()
    widget.resize(50, 200)
    widget.show()
    event = QPaintEvent(widget.rect())
    widget.paintEvent(event)
    assert widget.Vs0 == 40
    assert widget.getAirspeed() == 20
    widget.setAirspeed(40)  # redraw()
    widget.keyPressEvent(None)
    widget.wheelEvent(None)
    assert widget._airspeed == 40
    # Test branch
    widget.setAirspeed(40)
    widget.setAirspeed(41)
    assert widget._airspeed == 41

def test_numerical_airspeed_box(fix, qtbot):
    hmi.initialize({})
    widget = airspeed.Airspeed_Box()
    qtbot.addWidget(widget)
    widget.resize(50, 50)
    widget.show()
    fix.db.set_value("TAS", 100)
    widget.setMode(1)
    widget.setMode(0)
    assert widget.modeText == "TAS"
    assert widget.valueText == "100"
    fix.db.set_value("GS", 80)
    widget.setMode(1)
    assert widget.modeText == "GS"
    assert widget.valueText == "80"
    assert widget._modeIndicator == 1
    fix.db.set_value("IAS", 140)
    widget.setMode(2)
    assert widget.modeText == "IAS"
    assert widget.valueText == "140"
    widget.setMode("")
    assert widget._modeIndicator == 0
    widget.setMode("")
    assert widget._modeIndicator == 1
    widget.setMode("")
    assert widget._modeIndicator == 2
    widget.setMode("")
    assert widget._modeIndicator == 0
    widget.setMode(0)
    fix.db.get_item("TAS").fail = True
    fix.db.set_value("TAS", 101)
    assert widget.valueText == "XXX"
    fix.db.get_item("TAS").fail = False
    fix.db.get_item("TAS").bad = True
    fix.db.set_value("TAS", 102)
    assert widget.valueText == ""
    widget.paintEvent(None)
