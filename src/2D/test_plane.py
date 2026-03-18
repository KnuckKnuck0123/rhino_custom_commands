import rhinoscriptsyntax as rs
import Rhino
import scriptcontext

def get_plane(obj_id):
    if rs.IsCurve(obj_id):
        return rs.CurvePlane(obj_id)
    elif rs.IsSurface(obj_id):
        # get border
        crvs = rs.DuplicateSurfaceBorder(obj_id)
        if crvs:
            pl = rs.CurvePlane(crvs[0])
            rs.DeleteObjects(crvs)
            return pl
    return None

import math
print("Loaded")
