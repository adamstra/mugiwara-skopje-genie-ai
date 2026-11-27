from typing import Dict, Any, List, Optional
import geopandas as gpd
from shapely.geometry import Point, Polygon
import pyproj

class GISTool:
    """Executes spatial operations (spatial joins, buffer, distance, intersection) on GeoDataFrames."""

    def __init__(self, layers: Optional[Dict[str, gpd.GeoDataFrame]] = None):
        self.layers = layers or {}

    def register_layer(self, name: str, gdf: gpd.GeoDataFrame):
        self.layers[name] = gdf

    def count_points_in_polygon(self, points_layer: str, polygon_layer: str, polygon_id_col: Optional[str] = None) -> Dict[str, Any]:
        """Counts how many points from points_layer fall inside polygons from polygon_layer."""
        if points_layer not in self.layers or polygon_layer not in self.layers:
            return {"success": False, "error": f"Layer missing. Available: {list(self.layers.keys())}"}

        pts = self.layers[points_layer]
        polys = self.layers[polygon_layer]

        # Align CRS
        if pts.crs != polys.crs:
            pts = pts.to_crs(polys.crs)

        # Spatial Join
        joined = gpd.sjoin(pts, polys, how="inner", predicate="within")
        
        if polygon_id_col and polygon_id_col in polys.columns:
            counts = joined.groupby(polygon_id_col).size().to_dict()
        else:
            counts = {"total_inside": len(joined)}

        return {
            "success": True,
            "total_points": len(pts),
            "matched_points": len(joined),
            "counts": counts
        }

    def compute_buffer(self, layer_name: str, distance_meters: float) -> Optional[gpd.GeoDataFrame]:
        """Computes a buffer in meters around geometries (converting to metric CRS if needed)."""
        if layer_name not in self.layers:
            return None

        gdf = self.layers[layer_name]
        # If in geographic coords (e.g. EPSG:4326), reproject to appropriate UTM zone or Web Mercator (EPSG:3857)
        if gdf.crs and gdf.crs.is_geographic:
            projected = gdf.to_crs(epsg=3857)
            buffered = projected.buffer(distance_meters)
            return gpd.GeoDataFrame(gdf.drop(columns=["geometry"]), geometry=buffered, crs="EPSG:3857").to_crs(gdf.crs)
        else:
            buffered = gdf.buffer(distance_meters)
            return gpd.GeoDataFrame(gdf.drop(columns=["geometry"]), geometry=buffered, crs=gdf.crs)
