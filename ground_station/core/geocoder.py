"""
Global Place Search & Geocoding Engine for USV Ground Station.
Supports direct GPS coordinate parsing, built-in offline maritime ports database,
and online OpenStreetMap Nominatim geocoding in a non-blocking background thread.
"""

import os
import re
import json
import math
import urllib.request
import urllib.parse
from typing import List, Dict, Any, Optional, Tuple
from PyQt5.QtCore import QObject, pyqtSignal, QThread


# Built-in High-Precision Maritime Ports & Strategic Waterways Database
OFFLINE_MARITIME_DATABASE: List[Dict[str, Any]] = [
    # Americas
    {"name": "Miami Harbor & PortMiami", "region": "Florida, USA", "lat": 25.7743, "lon": -80.1706, "type": "port"},
    {"name": "San Francisco Bay & Golden Gate", "region": "California, USA", "lat": 37.8200, "lon": -122.4200, "type": "port"},
    {"name": "Port of New York & New Jersey", "region": "New York, USA", "lat": 40.6698, "lon": -74.1264, "type": "port"},
    {"name": "Port of Los Angeles / Long Beach", "region": "California, USA", "lat": 33.7432, "lon": -118.2673, "type": "port"},
    {"name": "Seattle Harbor (Elliott Bay)", "region": "Washington, USA", "lat": 47.6025, "lon": -122.3486, "type": "port"},
    {"name": "Norfolk Naval Station", "region": "Virginia, USA", "lat": 36.9538, "lon": -76.3054, "type": "naval_base"},
    {"name": "San Diego Naval Bay", "region": "California, USA", "lat": 32.6847, "lon": -117.1661, "type": "naval_base"},
    {"name": "Pearl Harbor Naval Station", "region": "Hawaii, USA", "lat": 21.3469, "lon": -157.9431, "type": "naval_base"},
    {"name": "Panama Canal (Miraflores Locks)", "region": "Panama", "lat": 8.9972, "lon": -79.5931, "type": "canal"},
    {"name": "Rio de Janeiro Harbor", "region": "Brazil", "lat": -22.9035, "lon": -43.1753, "type": "port"},
    {"name": "Buenos Aires Port", "region": "Argentina", "lat": -34.5833, "lon": -58.3667, "type": "port"},
    {"name": "Vancouver Harbor", "region": "British Columbia, Canada", "lat": 49.2925, "lon": -123.1098, "type": "port"},

    # Europe & Mediterranean
    {"name": "Port of Rotterdam", "region": "Netherlands", "lat": 51.9560, "lon": 4.1420, "type": "port"},
    {"name": "Port of Antwerp-Bruges", "region": "Belgium", "lat": 51.2800, "lon": 4.3300, "type": "port"},
    {"name": "Port of Hamburg", "region": "Germany", "lat": 53.5353, "lon": 9.9678, "type": "port"},
    {"name": "HM Naval Base Portsmouth", "region": "United Kingdom", "lat": 50.8038, "lon": -1.1097, "type": "naval_base"},
    {"name": "Port of Plymouth (Devonport)", "region": "United Kingdom", "lat": 50.3667, "lon": -4.1833, "type": "naval_base"},
    {"name": "Port of Southampton", "region": "United Kingdom", "lat": 50.8980, "lon": -1.4010, "type": "port"},
    {"name": "Strait of Dover / English Channel", "region": "UK / France", "lat": 51.1275, "lon": 1.3134, "type": "strait"},
    {"name": "Strait of Gibraltar", "region": "Gibraltar / Spain", "lat": 36.1408, "lon": -5.3536, "type": "strait"},
    {"name": "Port of Brest (Marine Nationale)", "region": "France", "lat": 48.3833, "lon": -4.4833, "type": "naval_base"},
    {"name": "Port of Marseille", "region": "France", "lat": 43.3360, "lon": 5.3480, "type": "port"},
    {"name": "Port of Genoa", "region": "Italy", "lat": 44.4056, "lon": 8.9222, "type": "port"},
    {"name": "Taranto Naval Base", "region": "Italy", "lat": 40.4760, "lon": 17.2280, "type": "naval_base"},
    {"name": "Piraeus Port (Athens)", "region": "Greece", "lat": 37.9430, "lon": 23.6370, "type": "port"},
    {"name": "Kiel Canal (Baltic Entrance)", "region": "Germany", "lat": 54.3644, "lon": 10.1558, "type": "canal"},
    {"name": "Bosporus Strait (Istanbul)", "region": "Turkey", "lat": 41.1172, "lon": 29.0711, "type": "strait"},

    # Middle East & Africa
    {"name": "Port of Lagos (Apapa & Tin Can Island)", "region": "Lagos, Nigeria", "lat": 6.4400, "lon": 3.3650, "type": "port"},
    {"name": "Port of Onne (Port Harcourt)", "region": "Rivers State, Nigeria", "lat": 4.7130, "lon": 7.1550, "type": "port"},
    {"name": "Suez Canal (Port Said Entrance)", "region": "Egypt", "lat": 31.2653, "lon": 32.3019, "type": "canal"},
    {"name": "Port of Alexandria", "region": "Egypt", "lat": 31.1833, "lon": 29.8667, "type": "port"},
    {"name": "Port of Jebel Ali (Dubai)", "region": "United Arab Emirates", "lat": 25.0113, "lon": 55.0617, "type": "port"},
    {"name": "Strait of Hormuz", "region": "Oman / Iran", "lat": 26.5667, "lon": 56.2500, "type": "strait"},
    {"name": "Bab-el-Mandeb Strait", "region": "Yemen / Djibouti", "lat": 12.5833, "lon": 43.3333, "type": "strait"},
    {"name": "Port of Mombasa (Kilindini Harbour)", "region": "Kenya", "lat": -4.0667, "lon": 39.6667, "type": "port"},
    {"name": "Port of Dakar", "region": "Senegal", "lat": 14.6760, "lon": -17.4260, "type": "port"},
    {"name": "Port of Abidjan", "region": "Côte d'Ivoire", "lat": 5.2750, "lon": -4.0150, "type": "port"},
    {"name": "Port of Cape Town", "region": "South Africa", "lat": -33.9189, "lon": 18.4233, "type": "port"},
    {"name": "Port of Durban", "region": "South Africa", "lat": -29.8587, "lon": 31.0218, "type": "port"},

    # Asia & Oceania
    {"name": "Port of Singapore & Keppel Harbor", "region": "Singapore", "lat": 1.2644, "lon": 103.8222, "type": "port"},
    {"name": "Strait of Malacca", "region": "Malaysia / Indonesia", "lat": 2.5000, "lon": 101.5000, "type": "strait"},
    {"name": "Port of Shanghai (Yangshan)", "region": "China", "lat": 30.6270, "lon": 122.0620, "type": "port"},
    {"name": "Port of Hong Kong (Victoria Harbour)", "region": "Hong Kong", "lat": 22.2908, "lon": 114.1722, "type": "port"},
    {"name": "Tokyo Bay & Port of Yokohama", "region": "Japan", "lat": 35.4437, "lon": 139.6380, "type": "port"},
    {"name": "Yokosuka Naval Base", "region": "Japan", "lat": 35.2917, "lon": 139.6644, "type": "naval_base"},
    {"name": "Port of Busan", "region": "South Korea", "lat": 35.1028, "lon": 129.0403, "type": "port"},
    {"name": "Sydney Harbour (Port Jackson)", "region": "New South Wales, Australia", "lat": -33.8568, "lon": 151.2153, "type": "port"},
    {"name": "HMAS Stirling (Fleet Base West)", "region": "Western Australia", "lat": -32.2031, "lon": 115.6881, "type": "naval_base"},
    {"name": "Port of Auckland (Waitematā)", "region": "New Zealand", "lat": -36.8406, "lon": 174.7675, "type": "port"},
    {"name": "Mumbai Port & Naval Dockyard", "region": "India", "lat": 18.9220, "lon": 72.8347, "type": "port"},
]


class GeocodeWorker(QThread):
    """Background worker for asynchronous HTTP geocoding lookup."""
    results_ready = pyqtSignal(list)

    def __init__(self, query: str, parent=None):
        super().__init__(parent)
        self.query = query.strip()

    def run(self):
        results = []
        if not self.query:
            self.results_ready.emit(results)
            return

        # 1. Check direct coordinates (instant parsing)
        coord = PlaceGeocoder.parse_coordinates(self.query)
        if coord:
            lat, lon = coord
            results.append({
                "name": f"GPS Coordinate ({lat:.4f}°, {lon:.4f}°)",
                "region": "Direct Entry",
                "lat": lat,
                "lon": lon,
                "type": "coordinate"
            })

        # 2. Check offline maritime database (case-insensitive substring match)
        q_lower = self.query.lower()
        for item in OFFLINE_MARITIME_DATABASE:
            if q_lower in item["name"].lower() or q_lower in item["region"].lower():
                results.append(item)
                if len(results) >= 5:
                    break

        # 3. Query OpenStreetMap Nominatim if network is available and query is not coordinate
        if not coord and len(self.query) >= 3:
            try:
                url = f"https://nominatim.openstreetmap.org/search?q={urllib.parse.quote(self.query)}&format=json&limit=5"
                req = urllib.request.Request(
                    url,
                    headers={"User-Agent": "USV-Ground-Station/1.0 (Autonomous Maritime Operations)"}
                )
                with urllib.request.urlopen(req, timeout=2.5) as resp:
                    data = json.loads(resp.read().decode('utf-8'))
                    for r in data:
                        name = r.get("display_name", "")
                        # Shorten name if too long
                        parts = [p.strip() for p in name.split(",")]
                        short_name = ", ".join(parts[:2]) if len(parts) >= 2 else name
                        region = ", ".join(parts[2:4]) if len(parts) > 3 else (parts[-1] if len(parts) > 2 else "")
                        try:
                            lat = float(r.get("lat", 0))
                            lon = float(r.get("lon", 0))
                            # Avoid duplicates with offline results
                            if not any(abs(item["lat"] - lat) < 0.01 and abs(item["lon"] - lon) < 0.01 for item in results):
                                results.append({
                                    "name": short_name,
                                    "region": region,
                                    "lat": lat,
                                    "lon": lon,
                                    "type": r.get("type", "location")
                                })
                        except (ValueError, TypeError):
                            pass
            except Exception:
                # Silently fall back to offline database when network is offline/DNS fails
                pass

        self.results_ready.emit(results)


class PlaceGeocoder(QObject):
    """
    Geocoding controller managing coordinate parsing, offline lookup,
    and background OSM Nominatim queries.
    """
    results_ready = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker: Optional[GeocodeWorker] = None

    def search(self, query: str):
        """Initiate background search for a place or coordinate."""
        if self._worker and self._worker.isRunning():
            self._worker.terminate()
            self._worker.wait()

        self._worker = GeocodeWorker(query, self)
        self._worker.results_ready.connect(self._on_worker_results)
        self._worker.start()

    def _on_worker_results(self, results: list):
        self.results_ready.emit(results)

    @staticmethod
    def parse_coordinates(query: str) -> Optional[Tuple[float, float]]:
        """
        Parse raw GPS coordinates from various string formats:
        - Decimal Degrees: '37.82, -122.42' or '37.82 -122.42'
        - Signed / Cardinal: '37.82N 122.42W' or '37.82 N, 122.42 W'
        - DMS: '37°49\'12"N 122°25\'14"W'
        """
        q = query.strip()

        # Decimal degrees: standard float pair (e.g. "37.82, -122.42" or "37.82 -122.42")
        dd_match = re.match(r"^([+-]?\d+(?:\.\d+)?)[,\s]+([+-]?\d+(?:\.\d+)?)$", q)
        if dd_match:
            try:
                lat = float(dd_match.group(1))
                lon = float(dd_match.group(2))
                if -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0:
                    return lat, lon
            except ValueError:
                pass

        # Cardinal decimal degrees (e.g. "37.82 N 122.42 W" or "37.82N, 122.42W")
        card_match = re.match(
            r"^(\d+(?:\.\d+)?)\s*([NSns])[,\s]+(\d+(?:\.\d+)?)\s*([EWew])$", q
        )
        if card_match:
            try:
                lat = float(card_match.group(1))
                if card_match.group(2).upper() == 'S':
                    lat = -lat
                lon = float(card_match.group(3))
                if card_match.group(4).upper() == 'W':
                    lon = -lon
                if -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0:
                    return lat, lon
            except ValueError:
                pass

        return None
