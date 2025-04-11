import shapely
import numpy as np
import geopandas


class RelationGenerator:

    """
    Generate pairs of geometries having particular types of spatial relationships.
    The shapes to be used are drawn from the input `fodder`, which 
    should be a `geopandas` data frame.
    
    Args:
    	fodder: Geopandas data farme with columns 'type' and 'geom'
        bounds: [xmin, xmax, ymin, ymax]: Box in which shapes will be placed
        margin: Objects will not be placed within this distance of region edge
        scale: Size range of objects as a fraction of min region extent
    """

    def __init__(
        self, 
        fodder:geopandas.geodataframe.GeoDataFrame=None, 
        bounds:list[float]=[0, 0, 100, 100], 
        margin:float=0.0,
        scale:list[float]=[0.1, 0.5]
    ):
        self.fodder = fodder
        self.xmin = bounds[0]
        self.ymin = bounds[1]
        self.xmax = bounds[2]
        self.ymax = bounds[3]
        self.min_scale = scale[0]
        self.max_scale = scale[1]
        self.margin = margin
        

    def generate(self, relation:str, sense:bool, max_attempts:int=20):
        """
        Generate a pair of shapes with a prescribed relationship.
        
        Args:
        	relation: Type of relationship
        	sense: Either `True` or `False`
        	max_attempts: How many times to try
        	
        The `max_attempts` parameter is required because generating some 
        types of relations depends on random sampling, which can possibly
        fail to produce the correct results. If it fails, return values
        are `None`.

        The `relation` parameter shoudl be one of the following.
            * `point-on-linestring`
            * `point-in-polygon`
            * `linestring-intersects-linestring`
            * `linestring-intersects-polygon`
            * `polygon-intersects-polygon`
            * `polygon-borders-polygon`

        If you use `polygon-borders-polygon`, you should be confident that `fodder` 
        actually contains polygons that border one another.  
        """

        if relation == 'point-on-linestring':
            gen_func = self._point_on_linestring
            def test_func(a, b): return a.distance(b) < (self.xmax - self.xmin) * 0.00001

        elif relation == 'point-in-polygon':
            gen_func = self._point_in_polygon
            def test_func(a, b): return a.within(b)

        elif relation == 'linestring-intersects-linestring':
            gen_func = self._linestring_intersects_linestring
            def test_func(a, b): return a.intersects(b)

        elif relation == 'linestring-intersects-polygon':
            gen_func = self._linestring_intersects_polygon
            def test_func(a, b): return a.intersects(b)

        elif relation == 'polygon-intersects-polygon':
            gen_func = self._polygon_intersects_polygon
            def test_func(a, b): return a.intersects(b)

        elif relation == 'polygon-borders-polygon':
            gen_func = self._polygon_borders_polygon
            def test_func(a, b): 
                region_area = (self.xmax - self.xmin) * (self.ymax - self.ymin)
                a_area_ok = a.area / region_area > 0.01
                b_area_ok = b.area / region_area > 0.01
                return (
                    a.geom_type == 'Polygon' and b.geom_type == 'Polygon'
                    and a_area_ok and b_area_ok
                    and a.touches(b)
                )

        else:
            raise ValueError('Unknown relation: %s' % relation)

        ok = False
        n_attempts = 0
        while not ok:
            if n_attempts >= max_attempts:
                break
            n_attempts += 1
            try:
                a, b = gen_func(sense)
            except:
                continue
            result = test_func(a, b)
            if result == sense:
                ok = True

        if ok is True:
            final_a, final_b = a, b
        else:
            final_a, final_b = None, None

        return final_a, final_b


    def pick_a_random(self, gtype):
        ix = np.random.choice(np.where(self.fodder['type'] == gtype)[0])
        return self.fodder.iloc[ix]['geom']

    
    def rescale(self, g0):
        xc = g0.centroid.xy[0][0]
        yc = g0.centroid.xy[1][0]
        g1 = shapely.affinity.translate(g0, xoff=-xc, yoff=-yc)
        xmin, ymin, xmax, ymax = g1.minimum_rotated_rectangle.bounds
        object_size = max(xmax - xmin, ymax - ymin)
        region_size = min(self.xmax - self.xmin, self.ymax - self.ymin)
        fraction = np.random.random() * (self.max_scale - self.min_scale) + self.min_scale
        new_size = region_size * fraction
        scale_factor = new_size / object_size
        g2 = shapely.affinity.scale(g1, xfact=scale_factor, yfact=scale_factor)
        return g2

    def rotate(self, g0):
        angle = np.random.random() * 360.0
        g1 = shapely.affinity.rotate(g0, angle=angle, origin=g0.centroid.coords[0])
        return(g1)
    
    def reposition(self, geoms):        
        if type(geoms) != list:
            geoms = [geoms]
        if len(geoms) == 1:
            [xmin, ymin, xmax, ymax] = geoms[0].bounds
        else:
            [xmin, ymin, xmax, ymax] = geoms[0].union(geoms[1]).bounds
        width = xmax - xmin
        height = ymax - ymin
        new_xmin = np.random.random() * (self.xmax - width - self.margin * 2) + self.xmin + self.margin
        new_ymin = np.random.random() * (self.ymax - height - self.margin * 2) + self.ymin + self.margin
        x_offset = new_xmin - xmin
        y_offset = new_ymin - ymin
        new_geoms = [
            shapely.affinity.translate(g, xoff=x_offset, yoff=y_offset)
            for g in geoms
        ]
        if len(new_geoms) == 1:
            return new_geoms[0]
        else:
            return new_geoms
        
            
    def _point_on_linestring(self, sense):
        b0 = self.pick_a_random('LineString')
        b1 = self.rotate(b0)
        b2 = self.rescale(b1)
        bb = self.reposition(b2)
        if sense == True:
            d = np.random.random() * bb.length
            aa = shapely.line_interpolate_point(bb, d)
        else:
            px = np.random.random() * (self.xmax - self.xmin - self.margin * 2) + self.xmin + self.margin
            py = np.random.random() * (self.ymax - self.ymin - self.margin * 2) + self.ymin + self.margin
            aa = shapely.Point(px, py)
        return aa, bb


    def _point_in_polygon(self, sense):
        b0 = self.pick_a_random('Polygon')
        b1 = self.rotate(b0)
        b2 = self.rescale(b1)
        bb = self.reposition(b2)
        [xmin, xmax, ymin, ymax] = bb.bounds
        if sense == True:
            px = np.random.random() * (xmax - xmin) + xmin
            py = np.random.random() * (ymax - ymin) + ymin
            aa = shapely.Point(px, py)
        else:
            px = np.random.random() * (self.xmax - self.xmin - self.margin * 2) + self.xmin + self.margin
            py = np.random.random() * (self.ymax - self.ymin - self.margin * 2) + self.ymin + self.margin
            aa = shapely.Point(px, py)
        return aa, bb


    def _linestring_intersects_linestring(self, sense):
        if sense == True:
            a0 = self.pick_a_random('LineString')
            a1 = self.rotate(a0)
            a2 = self.rescale(a1)
            point_a = a2.interpolate(np.random.random() * a2.length)

            b0 = self.pick_a_random('LineString')
            b1 = self.rotate(b0)
            b2 = self.rescale(b1)
            point_b = b2.interpolate(np.random.random() * b2.length)

            dx = point_b.xy[0][0] - point_a.xy[0][0]
            dy = point_b.xy[1][0] - point_a.xy[1][0]
            b3 = shapely.affinity.translate(b2, xoff=-dx, yoff=-dy)

            aa, bb = self.reposition([a2, b3])
            return aa, bb
        else:
            aa = self.reposition(self.rescale(self.rotate(self.pick_a_random('LineString'))))
            bb = self.reposition(self.rescale(self.rotate(self.pick_a_random('LineString'))))
            return aa, bb

    
    def _linestring_intersects_polygon(self, sense):
        if sense == True:
            b0 = self.rescale(self.rotate(self.pick_a_random('Polygon')))
            xmin, ymin, xmax, ymax = b0.bounds
            for i in range(20):
                x = np.random.random() * (xmax - xmin) + xmin
                y = np.random.random() * (ymax - ymin) + ymin
                point_in_b = shapely.Point(x, y)
                if b0.contains(point_in_b):
                    break
                    
            a0 = self.rescale(self.rotate(self.pick_a_random('LineString')))
            point_on_a = a0.interpolate(np.random.random() * a0.length)
            dx = point_in_b.xy[0][0] - point_on_a.xy[0][0]
            dy = point_in_b.xy[1][0] - point_on_a.xy[1][0]
            a1 = shapely.affinity.translate(a0, xoff=dx, yoff=dy)

            aa, bb = self.reposition([a1, b0])
            return aa, bb
        else:
            aa = self.reposition(self.rescale(self.rotate(self.pick_a_random('LineString'))))
            bb = self.reposition(self.rescale(self.rotate(self.pick_a_random('Polygon'))))
            return aa, bb


    def _polygon_intersects_polygon(self, sense):
        if sense == True:
            a0 = self.rescale(self.rotate(self.pick_a_random('Polygon')))
            xmin, ymin, xmax, ymax = a0.bounds
            for i in range(20):
                x = np.random.random() * (xmax - xmin) + xmin
                y = np.random.random() * (ymax - ymin) + ymin
                point_in_a = shapely.Point(x, y)
                if a0.contains(point_in_a):
                    break
                    
            b0 = self.rescale(self.rotate(self.pick_a_random('Polygon')))
            xmin, ymin, xmax, ymax = b0.bounds
            for i in range(20):
                x = np.random.random() * (xmax - xmin) + xmin
                y = np.random.random() * (ymax - ymin) + ymin
                point_in_b = shapely.Point(x, y)
                if b0.contains(point_in_b):
                    break
                    
            dx = point_in_b.xy[0][0] - point_in_a.xy[0][0]
            dy = point_in_b.xy[1][0] - point_in_a.xy[1][0]
            b1 = shapely.affinity.translate(b0, xoff=-dx, yoff=-dy)

            aa, bb = self.reposition([a0, b1])
            return aa, bb
        else:
            aa = self.reposition(self.rescale(self.rotate(self.pick_a_random('Polygon'))))
            bb = self.reposition(self.rescale(self.rotate(self.pick_a_random('Polygon'))))
            return aa, bb


    def _polygon_borders_polygon(self, sense):
        # First get two polygons that intersect one another, then 
        # create two adjscent polygons via intersecting and differencing. 
        if sense == True:
            aa, bb = self._polygon_intersects_polygon(True)
            c0 = aa.intersection(bb)
            d0 = aa.difference(bb)
            c_box = c0.minimum_rotated_rectangle.bounds
            c_size = max(c_box[2] - c_box[0], c_box[3] - c_box[1])
            d_box = d0.minimum_rotated_rectangle.bounds
            d_size = max(d_box[2] - d_box[0], d_box[3] - d_box[1])
            current_size = max(c_size, d_size)
            region_size = min(self.xmax - self.xmin, self.ymax - self.ymin)
            fraction = np.random.random() * (self.max_scale - self.min_scale) + self.min_scale
            new_size = region_size * fraction
            scale_factor = new_size / current_size
            c1 = shapely.affinity.scale(c0, xfact=scale_factor, yfact=scale_factor, origin=c0.centroid.coords[0])
            d1 = shapely.affinity.scale(d0, xfact=scale_factor, yfact=scale_factor, origin=c0.centroid.coords[0])
            aa, bb = self.reposition([c1, d1])
        else:
            aa = self.reposition(self.rescale(self.pick_a_random('Polygon')))
            bb = self.reposition(self.rescale(self.pick_a_random('Polygon')))
        return aa, bb
