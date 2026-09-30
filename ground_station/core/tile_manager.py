"""
Slippy Map Tile Manager for USV Ground Station.
Provides asynchronous fetching, disk caching, coordinate reprojection,
and rendering of Satellite Imagery, Nautical ENC Charts, and Simulated Costmaps.
"""

import os
import math
from typing import Dict, Tuple, List, Optional
from PyQt5.QtCore import QObject, pyqtSignal, QUrl, QRectF, QPointF
from PyQt5.QtGui import QPixmap, QImage, QPainter, QColor
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply

from ground_station.core.georeference import GeoReference, LatLon


class TileManager(QObject):
    """
    Manages Web Mercator (EPSG:3857) map tiles with asynchronous network downloads,
    persistent on-disk caching, and local ENU coordinate reprojection.
    """
    tile_loaded = pyqtSignal(str, int, int, int)  # (layer_name, z, x, y)

    # Standard Tile Service URLs
    TILE_SERVERS = {
        'satellite': 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        'nautical_base': 'https://services.arcgisonline.com/arcgis/rest/services/Ocean/World_Ocean_Base/MapServer/tile/{z}/{y}/{x}',
        'openseamap': 'https://tiles.openseamap.org/seamark/{z}/{x}/{y}.png',
        'osm': 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
    }

    def __init__(self, cache_dir: Optional[str] = None, parent=None):
        super().__init__(parent)
        if cache_dir is None:
            self.cache_dir = os.path.expanduser('~/.cache/usv_ground_station/tiles')
        else:
            self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)

        self.nam = QNetworkAccessManager(self)
        self.nam.finished.connect(self._on_download_finished)

        self._memory_cache: Dict[Tuple[str, int, int, int], QPixmap] = {}
        self._pending_requests: Dict[QNetworkReply, Tuple[str, int, int, int, str]] = {}
        self._active_keys = set()

    # ─── Slippy Map Math ──────────────────────────────────────────────────────

    @staticmethod
    def latlon_to_tile(lat: float, lon: float, zoom: int) -> Tuple[int, int]:
        """Convert Latitude/Longitude to Slippy Map tile X, Y indices at zoom level."""
        lat_clamped = max(-85.05112878, min(85.05112878, lat))
        lon_clamped = max(-180.0, min(180.0, lon))
        lat_rad = math.radians(lat_clamped)
        n = 2.0 ** zoom
        xtile = int((lon_clamped + 180.0) / 360.0 * n)
        ytile = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
        xtile = max(0, min(int(n) - 1, xtile))
        ytile = max(0, min(int(n) - 1, ytile))
        return xtile, ytile

    @staticmethod
    def tile_to_latlon(x: int, y: int, zoom: int) -> Tuple[float, float]:
        """Convert Slippy Map tile top-left corner to Latitude/Longitude."""
        n = 2.0 ** zoom
        lon_deg = x / n * 360.0 - 180.0
        lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * y / n)))
        lat_deg = math.degrees(lat_rad)
        return lat_deg, lon_deg

    @staticmethod
    def zoom_from_scale(scale_px_per_meter: float, datum_lat: float = 37.8200) -> int:
        """Calculate optimal slippy map zoom level (1 - 19) from radar canvas scale."""
        cos_lat = max(0.01, math.cos(math.radians(datum_lat)))
        meters_per_pixel = 1.0 / max(1e-9, scale_px_per_meter)
        target_zoom = math.log2((156543.03392 * cos_lat) / meters_per_pixel)
        return max(1, min(19, int(round(target_zoom))))

    # ─── Tile Caching & Retrieval ─────────────────────────────────────────────

    def get_tile(self, layer: str, z: int, x: int, y: int) -> Optional[QPixmap]:
        """
        Retrieve tile from memory cache or disk cache.
        If not cached, queues an asynchronous network download.
        """
        key = (layer, z, x, y)
        if key in self._memory_cache:
            return self._memory_cache[key]

        # Check local disk cache
        disk_path = self._get_disk_path(layer, z, x, y)
        if os.path.exists(disk_path):
            try:
                pix = QPixmap(disk_path)
                if not pix.isNull():
                    self._memory_cache[key] = pix
                    return pix
            except Exception:
                pass

        # Queue network download
        self._request_tile(layer, z, x, y)
        return None

    def _get_disk_path(self, layer: str, z: int, x: int, y: int) -> str:
        layer_dir = os.path.join(self.cache_dir, layer, str(z), str(x))
        os.makedirs(layer_dir, exist_ok=True)
        return os.path.join(layer_dir, f"{y}.png")

    def _request_tile(self, layer: str, z: int, x: int, y: int):
        key = (layer, z, x, y)
        if key in self._active_keys:
            return
        self._active_keys.add(key)

        template = self.TILE_SERVERS.get(layer)
        if not template:
            self._active_keys.discard(key)
            return

        url_str = template.format(z=z, x=x, y=y)
        req = QNetworkRequest(QUrl(url_str))
        req.setRawHeader(b'User-Agent', b'USVGroundStation/1.0 (Autonomous Maritime Operations)')

        reply = self.nam.get(req)
        self._pending_requests[reply] = (layer, z, x, y, self._get_disk_path(layer, z, x, y))

    def _on_download_finished(self, reply: QNetworkReply):
        req_info = self._pending_requests.pop(reply, None)
        if not req_info:
            reply.deleteLater()
            return

        layer, z, x, y, disk_path = req_info
        key = (layer, z, x, y)
        self._active_keys.discard(key)

        if reply.error() == QNetworkReply.NoError:
            data = reply.readAll()
            img = QImage()
            if img.loadFromData(data):
                pix = QPixmap.fromImage(img)
                self._memory_cache[key] = pix

                # Save to disk asynchronously
                try:
                    with open(disk_path, 'wb') as f:
                        f.write(data)
                except Exception:
                    pass

                self.tile_loaded.emit(layer, z, x, y)

        reply.deleteLater()

    # ─── Viewport Tile Geometry Calculation ───────────────────────────────────

    def get_visible_tiles(
        self,
        min_wx: float, max_wx: float,
        min_wy: float, max_wy: float,
        georef: GeoReference,
        scale: float
    ) -> List[Tuple[int, int, int, QRectF]]:
        """
        Calculate all tile coordinates and their world coordinate bounding rects
        covering the visible screen area.
        Returns a list of (z, x, y, QRectF(world_min_x, world_max_y, world_width, world_height)).
        """
        zoom = self.zoom_from_scale(scale, georef.datum_lat)

        # Convert corners to Lat/Lon
        ll_bottom_left = georef.to_latlon(min_wx, min_wy)
        ll_top_right = georef.to_latlon(max_wx, max_wy)

        # Adaptively step down zoom level until tile count is manageable (<= 42 tiles)
        while zoom >= 1:
            x_min, y_min = self.latlon_to_tile(ll_top_right.lat, ll_bottom_left.lon, zoom)
            x_max, y_max = self.latlon_to_tile(ll_bottom_left.lat, ll_top_right.lon, zoom)

            max_idx = (1 << zoom) - 1
            x_start = max(0, min(x_min, x_max))
            x_end = min(max_idx, max(x_min, x_max))
            y_start = max(0, min(y_min, y_max))
            y_end = min(max_idx, max(y_min, y_max))

            tile_count = (x_end - x_start + 1) * (y_end - y_start + 1)
            if tile_count <= 42 or zoom == 1:
                break
            zoom -= 1

        tiles = []
        for tx in range(x_start, x_end + 1):
            for ty in range(y_start, y_end + 1):
                # Top-left of tile
                lat_tl, lon_tl = self.tile_to_latlon(tx, ty, zoom)
                # Bottom-right of tile
                lat_br, lon_br = self.tile_to_latlon(tx + 1, ty + 1, zoom)

                enu_tl = georef.to_enu(lat_tl, lon_tl)
                enu_br = georef.to_enu(lat_br, lon_br)

                wx = enu_tl.east
                wy = enu_tl.north
                ww = enu_br.east - enu_tl.east
                wh = enu_tl.north - enu_br.north

                rect = QRectF(wx, wy - wh, ww, wh)
                tiles.append((zoom, tx, ty, rect))

        return tiles
