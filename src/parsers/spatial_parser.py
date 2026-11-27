from pathlib import Path
from typing import List, Dict, Any, Optional
import geopandas as gpd

class SpatialParser:
    """Parses spatial datasets (GeoJSON, Shapefile, GeoPackage) using GeoPandas."""

    def __init__(self):
        self.layers: Dict[str, gpd.GeoDataFrame] = {}

    def parse(self, file_path: Path, source_id: Optional[str] = None) -> Dict[str, Any]:
        file_path = Path(file_path)
        source_name = source_id or file_path.stem

        try:
            gdf = gpd.read_file(file_path)
        except Exception as e:
            return {
                "source_id": source_name,
                "filename": file_path.name,
                "error": str(e),
                "content_type": "spatial_error"
            }

        # Store layer in memory
        self.layers[source_name] = gdf

        geom_types = gdf.geom_type.value_counts().to_dict()
        columns = [c for c in gdf.columns if c != "geometry"]
        crs_str = str(gdf.crs) if gdf.crs else "Unknown"
        total_bounds = gdf.total_bounds.tolist() if not gdf.empty else []

        # Generate summary description for retrieval
        summary_text = (
            f"Spatial Layer: {source_name}\n"
            f"Filename: {file_path.name}\n"
            f"Features: {len(gdf)}\n"
            f"Geometry Types: {geom_types}\n"
            f"CRS: {crs_str}\n"
            f"Bounding Box: {total_bounds}\n"
            f"Attribute Columns: {', '.join(columns)}\n"
        )

        return {
            "source_id": source_name,
            "filename": file_path.name,
            "layer_name": source_name,
            "num_features": len(gdf),
            "geom_types": geom_types,
            "crs": crs_str,
            "total_bounds": total_bounds,
            "columns": columns,
            "text": summary_text,
            "content_type": "spatial",
        }

    def get_layer(self, source_id: str) -> Optional[gpd.GeoDataFrame]:
        return self.layers.get(source_id)
