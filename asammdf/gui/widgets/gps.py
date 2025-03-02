# -*- coding: utf-8 -*-
import io

import numpy as np
from PyQt5 import QtCore, QtWidgets
# from pyqtlet import L, MapWidget

from ..ui import resource_rc as resource_rc
from ..ui.gps import Ui_GPSDisplay


class GPS(Ui_GPSDisplay, QtWidgets.QWidget):
    timestamp_changed_signal = QtCore.pyqtSignal(object, float)

    def __init__(self, latitude_channel, longitude_channel, zoom=5, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)

        timebase = np.around(
            np.union1d(latitude_channel.timestamps, longitude_channel.timestamps), 9
        )
        self.latitude_signal = latitude_channel.interp(timebase)
        self.longitude_signal = longitude_channel.interp(timebase)
        if len(timebase):
            self.latitude = self.latitude_signal.samples[0]
            self.longitude = self.longitude_signal.samples[0]
        else:
            self.latitude = self.longitude = None

        self._min = self._max = 0

        self._inhibit = False

        if len(timebase):
            self._min = timebase[0]
            self._max = timebase[-1]
        else:
            self._min = float("inf")
            self._max = -float("inf")

        if self._min == float("inf"):
            self._min = self._max = 0

        self.timestamp.setRange(self._min, self._max)
        self.timestamp.setValue(self._min)
        self.min_t.setText(f"{self._min:.3f}s")
        self.max_t.setText(f"{self._max:.3f}s")

        self.mapWidget = MapWidget()
        self.map_layout.insertWidget(0, self.mapWidget)
        self.map_layout.setStretch(0, 1)
        self.map = L.map(self.mapWidget)
        self.map.setView([50.1364092, 8.5991296], zoom)

        L.tileLayer("https://{s}.tile.openstreetmap.fr/osmfr/{z}/{x}/{y}.png").addTo(
            self.map
        )

        if len(timebase):
            line = L.polyline(
                np.column_stack(
                    [self.latitude_signal.samples, self.longitude_signal.samples]
                ).tolist()
            )
            line.addTo(self.map)

            self.map.setView([self.latitude, self.longitude], zoom)
            print([self.latitude, abs(self.longitude)])
            self.marker = L.marker([self.latitude, self.longitude])
            self.map.addLayer(self.marker)
        else:
            self.marker = None

        self.timestamp.valueChanged.connect(self._timestamp_changed)
        self.timestamp_slider.valueChanged.connect(self._timestamp_slider_changed)
        self._update_values(self.timestamp.value())

        self.show()

    def _timestamp_changed(self, stamp):
        val = int((stamp - self._min) / (self._max - self._min) * 9999)

        if not self._inhibit:
            self._inhibit = True
            self.timestamp_slider.setValue(val)
        else:
            self._inhibit = False

        self._update_values(stamp)
        self.timestamp_changed_signal.emit(self, stamp)

    def _timestamp_slider_changed(self, stamp):
        factor = stamp / 9999
        val = (self._max - self._min) * factor + self._min

        if not self._inhibit:
            self._inhibit = True
            self.timestamp.setValue(val)
        else:
            self._inhibit = False

    def _update_values(self, stamp=None):
        if stamp is None:
            stamp = self.timestamp.value()

        try:
            self.latitude = self.latitude_signal.cut(stamp, stamp).samples[0]
            self.longitude = self.longitude_signal.cut(stamp, stamp).samples[0]
        except:
            return
        if self.marker is not None:
            self.marker.setLatLng([self.latitude, self.longitude])
            app = QtWidgets.QApplication.instance()
            app.processEvents()

    def to_config(self):

        config = {
            "latitude_channel": self.latitude_signal.name,
            "longitude_channel": self.longitude_signal.name,
            "zoom": self.map.getZoom(),
        }

        return config
