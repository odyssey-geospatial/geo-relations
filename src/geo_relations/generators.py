import shapely
import numpy as np


class RelationGenerator:

    """
    Generate pairs of geometries having particular types of spatial relationships.
    
    Args:
    	fodder: geopandas data farme with columns 'type' and 'geom'
        bounds: [xmin, xmax, ymin, ymax]: box in which shapes will be placed
        scale: approximate size of returned LineStrings and Polygons
    """

    def __init__(self, fodder=None, bounds=[0, 0, 100, 100], scale=10):
        self.fodder = fodder
        self.xmin = bounds[0]
        self.ymin = bounds[1]
        self.xmax = bounds[2]
        self.ymax = bounds[3]
        self.scale = scale
        

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
        """

        if relation == 'point-on-linestring':
            gen_func = self._point_on_linestring
            def test_func(a, b): return a.distance(b) < self.scale * 0.00001

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
            def test_func(a, b): return a.touches(b)

        else:
            raise ValueError('Unknown relation: %s' % relation)

        ok = False
        n_attempts = 0
        while not ok:
            if n_attempts >= max_attempts:
                break
            n_attempts += 1
            a, b = gen_func(sense)
            result = test_func(a, b)
            if result == sense:
                ok = True
                
        if ok is True:
            final_a, final_b = self.reposition([a, b])
        else:
            final_a, final_b = None, None

        return final_a, final_b


    def pick_a_random(self, gtype):
        ix = np.random.choice(np.where(self.fodder['type'] == gtype)[0])
        return self.fodder.iloc[ix]['geom']

    
    def rescale(self, g0):
        xmin, ymin, xmax, ymax = g0.bounds
        g1 = shapely.affinity.translate(g0, xoff=-xmin, yoff=-ymin)
        iscale = max(xmax - xmin, ymax - ymin)
        oscale = self.scale * (np.random.random() * 1.5 + 0.5)
        factor = oscale / iscale
        g2 = shapely.affinity.scale(g1, xfact=factor, yfact=factor)
        return g2

    
    def reposition(self, geoms):
        if type(geoms) != list:
            geoms = [geoms]
        if len(geoms) == 1:
            [xmin, ymin, xmax, ymax] = geoms[0].bounds
        else:
            [xmin, ymin, xmax, ymax] = geoms[0].union(geoms[1]).bounds
        width = xmax - xmin
        height = ymax - ymin
        new_xmin = np.random.random() * (self.xmax - width) + self.xmin
        new_ymin = np.random.random() * (self.ymax - height) + self.ymin
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
        if sense == True:
            b0 = self.pick_a_random('LineString')
            bb = self.rescale(b0)
            d = np.random.random() * bb.length
            aa = shapely.line_interpolate_point(bb, d)
        else:
            b0 = self.pick_a_random('LineString')
            bb = self.rescale(b0)
            [xmin, ymin, xmax, ymax] = bb.bounds
            if np.random.random() < 0.5:
                px = xmin - np.random.random() * self.scale * 2.0
            else:
                px = xmax + np.random.random() * self.scale * 2.0
            if np.random.random() < 0.5:
                py = ymin - np.random.random() * self.scale * 2.0
            else:
                py = ymax + np.random.random() * self.scale * 2.0
            aa = shapely.Point(px, py)
        return aa, bb


    def _point_in_polygon(self, sense):
        if sense == True:
            b0 = self.pick_a_random('Polygon')
            bb = self.rescale(b0)
            [xmin, xmax, ymin, ymax] = bb.bounds
            px = np.random.random() * (xmax - xmin) + xmin
            py = np.random.random() * (ymax - ymin) + ymin
            aa = shapely.Point(px, py)
        else:
            b0 = self.pick_a_random('Polygon')
            bb = self.rescale(b0)
            [xmin, ymin, xmax, ymax] = bb.bounds
            if np.random.random() < 0.5:
                px = xmin - np.random.random() * self.scale * 2.0
            else:
                px = xmax + np.random.random() * self.scale * 2.0
            if np.random.random() < 0.5:
                py = ymin - np.random.random() * self.scale * 2.0
            else:
                py = ymax + np.random.random() * self.scale * 2.0
            aa = shapely.Point(px, py)
        return aa, bb


    def _linestring_intersects_linestring(self, sense):
        if sense == True:
            a0 = self.pick_a_random('LineString')
            a1 = self.rescale(a0)
            point_a = a1.interpolate(np.random.random() * a1.length)
            
            b0 = self.pick_a_random('LineString')
            b1 = self.rescale(b0)
            point_b = b1.interpolate(np.random.random() * b1.length)
            
            dx = point_b.xy[0][0] - point_a.xy[0][0]
            dy = point_b.xy[1][0] - point_a.xy[1][0]
            b2 = shapely.affinity.translate(b1, xoff=-dx, yoff=-dy)
            return a1, b2
        else:
            aa = self.reposition(self.rescale(self.pick_a_random('LineString')))
            bb = self.reposition(self.rescale(self.pick_a_random('LineString')))
            return aa, bb

    
    def _linestring_intersects_polygon(self, sense):
        if sense == True:
            b0 = self.pick_a_random('Polygon')
            b1 = self.rescale(b0)
            xmin, ymin, xmax, ymax = b1.bounds
            for i in range(20):
                x = np.random.random() * (xmax - xmin) + xmin
                y = np.random.random() * (ymax - ymin) + ymin
                point_in_b = shapely.Point(x, y)
                if b1.contains(point_in_b):
                    break
            a0 = self.pick_a_random('LineString')
            a1 = self.rescale(a0)
            point_on_a = a1.interpolate(np.random.random() * a1.length)
            dx = point_in_b.xy[0][0] - point_on_a.xy[0][0]
            dy = point_in_b.xy[1][0] - point_on_a.xy[1][0]
            a2 = shapely.affinity.translate(a1, xoff=dx, yoff=dy)
            return a2, b1
        else:
            aa = self.reposition(self.rescale(self.pick_a_random('LineString')))
            bb = self.reposition(self.rescale(self.pick_a_random('Polygon')))
            return aa, bb


    def _polygon_intersects_polygon(self, sense):
        if sense == True:
            a0 = self.pick_a_random('Polygon')
            a1 = self.rescale(a0)
            xmin, ymin, xmax, ymax = a1.bounds
            for i in range(20):
                x = np.random.random() * (xmax - xmin) + xmin
                y = np.random.random() * (ymax - ymin) + ymin
                point_in_a = shapely.Point(x, y)
                if a1.contains(point_in_a):
                    break
                    
            b0 = self.pick_a_random('Polygon')
            b1 = self.rescale(b0)
            xmin, ymin, xmax, ymax = b1.bounds
            for i in range(20):
                x = np.random.random() * (xmax - xmin) + xmin
                y = np.random.random() * (ymax - ymin) + ymin
                point_in_b = shapely.Point(x, y)
                if b1.contains(point_in_b):
                    break
                    
            dx = point_in_b.xy[0][0] - point_in_a.xy[0][0]
            dy = point_in_b.xy[1][0] - point_in_a.xy[1][0]
            b2 = shapely.affinity.translate(b1, xoff=-dx, yoff=-dy)
            return a1, b2
        else:
            aa = self.reposition(self.rescale(self.pick_a_random('Polygon')))
            bb = self.reposition(self.rescale(self.pick_a_random('Polygon')))
            return aa, bb


    def _polygon_borders_polygon(self, sense):
        # Kind of a special case. We don't want to rely on completely
        # random sampling to happen to pick two bordering polygons.
        # So instead we go through the list of polygons systematically.
        if sense == True:
            indices = np.random.permutation(np.where(self.fodder['type'] == 'Polygon')[0])
            a_index = indices[0]
            a0 = self.fodder.iloc[a_index]['geom']
            for b_index in indices[1:]:
                b0 = self.fodder.iloc[b_index]['geom']
                if b0.touches(a0):
                    break

            # Shift the shapes so their joint bounding box is at the origin.
            xmin, ymin, xmax, ymax = a0.union(b0).bounds
            a1 = shapely.affinity.translate(a0, xoff=-xmin, yoff=-ymin)
            b1 = shapely.affinity.translate(b0, xoff=-xmin, yoff=-ymin)

            # Scale the shapes jointly.
            xmin, ymin, xmax, ymax = a1.union(b1).bounds
            iscale = max(xmax - xmin, ymax - ymin)
            oscale = self.scale * (np.random.random() * 1.5 + 0.5)
            factor = oscale / iscale * 2.0
            a2 = shapely.affinity.scale(a1, xfact=factor, yfact=factor, origin=(0, 0))
            b2 = shapely.affinity.scale(b1, xfact=factor, yfact=factor, origin=(0, 0))
            
            return a2, b2
        else:
            aa = self.reposition(self.rescale(self.pick_a_random('Polygon')))
            bb = self.reposition(self.rescale(self.pick_a_random('Polygon')))
            return aa, bb
