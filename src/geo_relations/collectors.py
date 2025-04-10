import osmnx
import geopandas
import pyproj
import shapely


class OSMShapeCollector:
    """
    Collect shapes from a lon lat bounding box in OpenStreetMap
        
    Args:
        center_lon: Longitude of bounding box center.
        center_lat: Latitude of bounding box center.
        extent: Width and height of the bounding box in meters.

    The input parameters define a square bounding box
    from which shapes will be gathered.
    This package assumes that the only relevant characteristic of any
    geospatial entity is its shape. There is no attempt to capture information
    about what the shapes represent. They should just be considered featureless
    Points, LineStrings, and Polygons.
    """

    def __init__(self, center_lon:float, center_lat:float, extent:float):
        self.center_lon = center_lon
        self.center_lat = center_lat
        self.extent = extent

        # Define a local map projection.
        # Define the Local Transverse Mercator (LTM) CRS
        offset = (extent / 2)
        proj_def = f"""
        +proj=tmerc +lat_0={center_lat} +lon_0={center_lon} 
        +k=1.0 +x_0={offset} +y_0={offset} +datum=WGS84 +units=m +no_defs
        """
        ltm_crs = pyproj.CRS.from_proj4(proj_def)
        wgs84_crs = pyproj.CRS.from_epsg(4326)
        self.proj_forward = pyproj.Transformer.from_crs(wgs84_crs, ltm_crs, always_xy=True).transform
        self.proj_inverse = pyproj.Transformer.from_crs(ltm_crs, wgs84_crs, always_xy=True).transform
        
        # Define a polygon defining the bounding box for our area of interest.
        xx = [0, extent, extent, 0, 0]
        yy = [0, 0, extent, extent, 0]
        self.aoi = shapely.geometry.Polygon(list(zip(xx, yy)))

        # Get the bounds to be used for querying from OSM.
        lon0, lat0 = self.proj_inverse(0, 0)
        lon1, lat1 = self.proj_inverse(extent, extent)
        self.query_bounds = [lon0, lat0, lon1, lat1]

        # This will be the list of shapes.
        self.shapes = None


    def collect(self, types:list[str]):
        """
        Pull shapes from OSM.
        
        Args:
        	types: List of the types of shapes to pull

        The `types` parameter is a list of strings indicating which types of 
        shapes to pull from OSM. 
        Even though the attributes of the shapes are 
        not relevant in this package, it might help to know exactly what is being
        pulled. If `types` includes the following strings, here is what you will get:

        - `points`: A sampling of points. These are OSM entities of type "amenity". 
          Any such entities that is not a "Point" is replaced with its centroid.

        - `linestrings`: A sampling of road segments and linear water features.

        - `polygons`: A sampling of polygonal "landuse" objects.

        - `tiled_polygons`: Any level-8 administrative units. This is treated
          as a special case different from "polygons", because these types of entities
          tend to share borders, so they can be used to test for adjacency.

        - `multipoints``: Random groupings of Point objects

        - `multilinestrings`: Random groupings of LineString objects

        - `multipolygons`: Random groupings of Polygon objects

        All returned polygons will be in a local projected coordinate system, in meters.
        """

        points = []
        linestrings = []
        polygons = []
        multipoints = []
        multilinestrings = []
        multipolygons = []
        tiles = []

        if 'tiled-polygons' in types:
            # Get level-8 administrative units -- typically cities and towns.
            tags = {
                'boundary': 'administrative',
                'admin_level': '8'
            }
            df = osmnx.features.features_from_bbox(self.query_bounds, tags=tags).reset_index()
            iok = df['admin_level'] == '8'
            df = df[iok]

            # Only keep the portions that fall within our AOI, and that are a minimum fraction of their original.
            tiled_polygons = []
            for rec in df.itertuples():
                g1 = shapely.ops.transform(self.proj_forward, rec.geometry)
                g2 = g1.intersection(self.aoi)
                if g2.geom_type != 'Polygon':
                    continue
                if g2.area / g1.area > 0.2:
                    tiles.append(g2)

        if 'polygons' in types or 'multipolygons' in types:
            # Get landuse polygons.
            tags = { 'landuse': ['residential', 'commercial', 'industrial', 'retail', 'farmland']}
            landuse = osmnx.features.features_from_bbox(self.query_bounds, tags=tags).reset_index()

            # Get admin units.
            tags = {'boundary': 'administrative', 'admin_level': '8'}
            admin = osmnx.features.features_from_bbox(self.query_bounds, tags=tags).reset_index()
            iok = admin['admin_level'] == '8'
            admin = admin[iok]

            for source in [landuse, admin]:
                for rec in source.itertuples():
                    g0 = rec.geometry
                    g1 = shapely.ops.transform(self.proj_forward, g0)
                    g2 = g1.intersection(self.aoi)
                    if g2.geom_type != 'Polygon': # It can happen. 
                        continue
                    if g2.area / g1.area > 0.1 and g2.area > 10000.0:
                        polygons.append(g2)

        if "linestrings" in types or "multilinestrings" in types:
            # Get major roads and linear water features.
            tags = { 'highway': ['motorway', 'trunk', 'primary', 'secondary']}
            roads = osmnx.features.features_from_bbox(self.query_bounds, tags=tags).reset_index()
            tags = {"waterway": ["river", "stream", "canal"]}
            waterways = osmnx.features.features_from_bbox(self.query_bounds, tags=tags).reset_index()
            for source in [roads, waterways]:
                for rec in source.itertuples():
                    g0 = rec.geometry
                    g1 = shapely.ops.transform(self.proj_forward, g0)
                    g2 = g1.intersection(self.aoi)
                    if g2.geom_type != 'LineString':
                        continue
                    if g2.length / g1.length > 0.5 and g2.length > 500:
                        linestrings.append(g2)

        if "points" in types or "multipoints" in types:
            tags = {"amenity": True}
            amenities = osmnx.features.features_from_bbox(self.query_bounds, tags=tags).reset_index()
            for rec in amenities.itertuples():
                if rec.amenity in ['parking', 'parking_space']: # There are just too many of these.
                    continue
                g0 = rec.geometry
                if g0.geom_type == 'Point':
                    g1 = g0
                elif g0.geom_type == 'Polygon':
                    g1 = g0.centroid
                else:
                    continue
                g2 = shapely.ops.transform(self.proj_forward, g1)
                if g2.within(self.aoi):
                    points.append(g2)

        # Handle multi* objects.
        if "multipoints" in types:
            n_points = len(points)
            for i in range(100):
                sample_count = np.random.randint(8) + 2
                sample_indices = np.random.choice(n_points, sample_count, replace=False)
                mp = shapely.MultiPoint([points[i] for i in sample_indices])
                multipoints.append(mp)

        if "multilinestrings" in types:
            n_linestrings = len(linestrings)
            for i in range(100):
                sample_count = np.random.randint(8) + 2
                sample_indices = np.random.choice(n_linestrings, sample_count, replace=False)
                mp = shapely.MultiLineString([linestrings[i] for i in sample_indices])
                multilinestrings.append(mp)

        if "multipolygons" in types:
            n_polygons = len(polygons)
            for i in range(100):
                sample_count = np.random.randint(8) + 2
                sample_indices = np.random.choice(n_polygons, sample_count, replace=False)
                mp = shapely.MultiPolygon([polygons[i] for i in sample_indices])
                multipolygons.append(mp)

        # Put that together into a data frame.
        shapes = []
        if "points" in types:
            shapes += points
        if "linestrings" in types:
            shapes += linestrings
        if "polygons" in types:
            shapes += polygons
        if "multipoints" in types:
            shapes += multipoints
        if "multilinestrings" in types:
            shapes += multilinestrings
        if "multipolygons" in types:
            shapes += multipolygons
        if "tiled-polygons" in types:
            shapes += tiles
            
        shape_types = [g.geom_type for g in shapes]
        self.shapes = geopandas.GeoDataFrame({'type': shape_types, 'geom': shapes})

        # Return it.
        return self.shapes




        
