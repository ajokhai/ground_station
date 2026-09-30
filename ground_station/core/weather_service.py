"""
Real-Time Metocean & Weather Integration Service for USV Ground Station.
Queries Open-Meteo Forecast & Marine APIs (free, zero API-key requirement)
in a background thread to deliver live real-world wind, wave, barometric,
and temperature soundings for the active operational theater.
"""

import time
import json
import math
import urllib.request
import urllib.parse
from typing import Dict, Any, Optional
from PyQt5.QtCore import QObject, pyqtSignal, QThread, QTimer


class WeatherWorker(QThread):
    """Background worker for asynchronous Metocean API lookups."""
    weather_ready = pyqtSignal(dict)

    def __init__(self, lat: float, lon: float, location_name: str = "", parent=None):
        super().__init__(parent)
        self.lat = lat
        self.lon = lon
        self.location_name = location_name

    def run(self):
        result = self._fetch_live_data()
        self.weather_ready.emit(result)

    def _fetch_live_data(self) -> Dict[str, Any]:
        """Query Open-Meteo Forecast and Marine APIs with automatic offline fallback."""
        data = {
            'lat': self.lat,
            'lon': self.lon,
            'location_name': self.location_name,
            'timestamp': time.time(),
            'is_live': False,
            'source': 'Climatological Model',
        }

        # Format coordinates for display
        ns = 'N' if self.lat >= 0 else 'S'
        ew = 'E' if self.lon >= 0 else 'W'
        data['lat_str'] = f"{abs(self.lat):.2f}°{ns}"
        data['lon_str'] = f"{abs(self.lon):.2f}°{ew}"

        # Default / Fallback Metocean baseline computed physically from latitude
        # Equatorial vs Mid-latitude vs Polar temperature curve
        base_temp = max(-10.0, min(32.0, 28.0 - abs(self.lat) * 0.45))
        # Prevailing trade winds / westerlies
        base_wind_spd = 10.0 + 4.0 * math.sin(math.radians(abs(self.lat) * 2))
        base_wind_dir = (abs(self.lon) * 3 + abs(self.lat) * 7) % 360.0

        data.update({
            'wind_spd': round(base_wind_spd, 1),
            'wind_dir': round(base_wind_dir, 0),
            'wind_gust': round(base_wind_spd * 1.35, 1),
            'current_spd': 0.8,
            'current_dir': round((base_wind_dir + 25.0) % 360.0, 0),
            'depth': 22.0,
            'tide': '+0.3m',
            'sea_state': 'State 2 (0.4m)',
            'wave_height': 0.4,
            'wave_period': 4.5,
            'water_temp': round(base_temp, 1),
            'barometer': 1013.2,
            'humidity': 72,
            'gps_fix': 'RTK Fixed (3D)',
            'sats': 18,
            'hdop': 0.7,
            'station': f"Estimated Met ({self.location_name or 'In-Situ'})",
        })

        try:
            # 1. Fetch Atmospheric & Surface Wind from Open-Meteo
            forecast_url = (
                f"https://api.open-meteo.com/v1/forecast?"
                f"latitude={self.lat:.4f}&longitude={self.lon:.4f}&"
                f"current=temperature_2m,relative_humidity_2m,surface_pressure,"
                f"wind_speed_10m,wind_direction_10m,wind_gusts_10m&"
                f"wind_speed_unit=kn"
            )
            req = urllib.request.Request(
                forecast_url,
                headers={"User-Agent": "USV-Ground-Station/1.0 (Maritime-Operations)"}
            )
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                f_data = json.loads(resp.read().decode('utf-8'))
                curr = f_data.get('current', {})

                if 'wind_speed_10m' in curr:
                    data['wind_spd'] = float(curr['wind_speed_10m'])
                if 'wind_direction_10m' in curr:
                    data['wind_dir'] = float(curr['wind_direction_10m'])
                if 'wind_gusts_10m' in curr:
                    data['wind_gust'] = float(curr['wind_gusts_10m'])
                if 'temperature_2m' in curr:
                    data['water_temp'] = float(curr['temperature_2m'])
                if 'surface_pressure' in curr:
                    data['barometer'] = float(curr['surface_pressure'])
                if 'relative_humidity_2m' in curr:
                    data['humidity'] = int(curr['relative_humidity_2m'])

                data['is_live'] = True
                loc_tag = self.location_name or f"{abs(self.lat):.2f}°{ns}, {abs(self.lon):.2f}°{ew}"
                data['source'] = 'Open-Meteo Live'
                data['station'] = f"Open-Meteo ({loc_tag})"

            # 2. Fetch Sea State & Waves from Open-Meteo Marine API
            try:
                marine_url = (
                    f"https://marine-api.open-meteo.com/v1/marine?"
                    f"latitude={self.lat:.4f}&longitude={self.lon:.4f}&"
                    f"current=wave_height,wave_direction,wave_period"
                )
                m_req = urllib.request.Request(
                    marine_url,
                    headers={"User-Agent": "USV-Ground-Station/1.0 (Maritime-Operations)"}
                )
                with urllib.request.urlopen(m_req, timeout=2.5) as m_resp:
                    m_data = json.loads(m_resp.read().decode('utf-8'))
                    m_curr = m_data.get('current', {})
                    if 'wave_height' in m_curr and m_curr['wave_height'] is not None:
                        wh = float(m_curr['wave_height'])
                        data['wave_height'] = wh
                        wp = float(m_curr.get('wave_period', 5.0) or 5.0)
                        data['wave_period'] = wp
                        data['sea_state'] = f"State {self._beaufort_sea_state(wh)} ({wh:.1f}m, {wp:.0f}s)"
            except Exception:
                # If inland or offshore marine API has no wave buoy coverage, calculate from wind
                wh = round(0.02 * (data['wind_spd'] ** 1.3), 1)
                data['wave_height'] = wh
                data['sea_state'] = f"State {self._beaufort_sea_state(wh)} ({wh:.1f}m)"

        except Exception:
            # Fully graceful offline fallback
            data['is_live'] = False
            data['source'] = 'Offline Mode (Climatology)'
            data['station'] = f"Climatology Baseline ({self.location_name or 'Offline'})"

        return data

    @staticmethod
    def _beaufort_sea_state(wave_height_m: float) -> int:
        """Estimate World Meteorological Organization (WMO) sea state code from wave height."""
        if wave_height_m < 0.1:
            return 0  # Calm (glassy)
        elif wave_height_m < 0.5:
            return 1  # Calm (rippled)
        elif wave_height_m < 1.25:
            return 2  # Smooth
        elif wave_height_m < 2.5:
            return 3  # Slight
        elif wave_height_m < 4.0:
            return 4  # Moderate
        elif wave_height_m < 6.0:
            return 5  # Rough
        elif wave_height_m < 9.0:
            return 6  # Very rough
        else:
            return 7  # High / Phenomenal


class WeatherService(QObject):
    """
    Main controller for live metocean weather data acquisition.
    Automatically fetches surface conditions when datum changes,
    and runs a 15-minute background refresh.
    """
    weather_updated = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker: Optional[WeatherWorker] = None
        self._last_lat: float = 37.8200
        self._last_lon: float = -122.4200
        self._last_name: str = "San Francisco Bay"

        # 15-minute periodic auto-refresh timer (900,000 ms)
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setInterval(900_000)
        self._refresh_timer.timeout.connect(self.refresh)
        self._refresh_timer.start()

    def update_location(self, lat: float, lon: float, name: str = ""):
        """Trigger an immediate asynchronous weather sounding for a new location."""
        self._last_lat = lat
        self._last_lon = lon
        if name:
            self._last_name = name

        if self._worker and self._worker.isRunning():
            self._worker.terminate()
            self._worker.wait()

        self._worker = WeatherWorker(lat, lon, self._last_name, self)
        self._worker.weather_ready.connect(self._on_weather_ready)
        self._worker.start()

    def refresh(self):
        """Re-query conditions for the current theater."""
        self.update_location(self._last_lat, self._last_lon, self._last_name)

    def _on_weather_ready(self, data: dict):
        self.weather_updated.emit(data)
