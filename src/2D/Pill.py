import Rhino
import scriptcontext as sc

def RunCommand():
    """
    Creates a 2D pill shape defined by its center point, total length, and width.
    The pill consists of two parallel lines capped by semi-circles.
    """
    # Prompt for base point (center of pill)
    pt_rc, center_pt = Rhino.Input.RhinoGet.GetPoint("Center point of pill", False)
    if pt_rc != Rhino.Commands.Result.Success:
        return pt_rc

    # Prompt for length
    rc, length = Rhino.Input.RhinoGet.GetNumber("Total length of pill", True, 10.0, 0.001, 100000.0)
    if rc != Rhino.Commands.Result.Success:
        return rc

    # Prompt for width
    rc, width = Rhino.Input.RhinoGet.GetNumber("Width of pill", True, 2.0, 0.001, 100000.0)
    if rc != Rhino.Commands.Result.Success:
        return rc

    if width >= length:
        print("Width must be strictly less than length for a pill shape.")
        return Rhino.Commands.Result.Failure

    # Get the active construction plane and set its origin to the chosen center point
    view = sc.doc.Views.ActiveView
    if view is None:
        return Rhino.Commands.Result.Failure
        
    plane = view.ActiveViewport.ConstructionPlane()
    plane.Origin = center_pt

    # Calculate dimensions
    radius = width / 2.0
    half_straight = (length - width) / 2.0

    # Define corners based on the plane
    p0 = plane.PointAt(-half_straight, radius)   # Top-left
    p1 = plane.PointAt(half_straight, radius)    # Top-right
    p2 = plane.PointAt(half_straight, -radius)   # Bottom-right
    p3 = plane.PointAt(-half_straight, -radius)  # Bottom-left

    # Create top and bottom line segments
    top_line = Rhino.Geometry.LineCurve(p0, p1)
    bottom_line = Rhino.Geometry.LineCurve(p2, p3)

    # Create right and left arcs
    # The right arc starts at p1, tangent aligns with the plane's X axis, and ends at p2
    right_arc = Rhino.Geometry.Arc(p1, plane.XAxis, p2)
    arc1_crv = Rhino.Geometry.ArcCurve(right_arc)

    # The left arc starts at p3, tangent aligns with the negative X axis, and ends at p0
    left_arc = Rhino.Geometry.Arc(p3, -plane.XAxis, p0)
    arc2_crv = Rhino.Geometry.ArcCurve(left_arc)

    # Join the curves into a single closed boundary
    curves = [top_line, arc1_crv, bottom_line, arc2_crv]
    joined_curves = Rhino.Geometry.Curve.JoinCurves(curves)

    if joined_curves and len(joined_curves) > 0:
        # Disable redraw during geometry addition
        sc.doc.Views.RedrawEnabled = False
        try:
            for crv in joined_curves:
                sc.doc.Objects.AddCurve(crv)
            print("Pill created with Length={} and Width={}.".format(length, width))
        finally:
            # Re-enable redraw
            sc.doc.Views.RedrawEnabled = True
            sc.doc.Views.Redraw()
    else:
        print("Failed to create the pill shape.")
        return Rhino.Commands.Result.Failure

    return Rhino.Commands.Result.Success

if __name__ == "__main__":
    RunCommand()
