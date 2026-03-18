import rhinoscriptsyntax as rs
import Rhino
import Rhino.Geometry
import scriptcontext as sc
import System.Collections.Generic
import random
import math

def create_rigid_stick_pile():
    """
    Creates a pile of sticks by simulating dropping them vertically.
    Sticks are long, thin prismatic shapes that tumble and pile naturally.
    Prevents floating and overlapping by raycasting against previously placed sticks.
    """
    # 1. User Inputs
    num_sticks = rs.GetInteger("Number of sticks", 80, 1, 2000)
    if num_sticks is None: return False

    # Stick Dimensions (long and thin)
    stick_length = rs.GetReal("Stick length", 30.0, 5.0, 200.0)
    if stick_length is None: return False

    stick_thickness = rs.GetReal("Stick thickness (square cross-section)", 1.5, 0.1, 20.0)
    if stick_thickness is None: return False

    # Pile Radius
    pile_radius = rs.GetReal("Pile Radius", 40.0)
    if pile_radius is None: return False

    center = rs.GetPoint("Select center point")
    if not center: return False

    rs.EnableRedraw(False)
    rs.StatusBarProgressMeterShow("Stacking Sticks", 0, num_sticks, True, True)

    placed_meshes = []

    # Stick cross-section half-dims
    half_l = stick_length / 2.0
    half_t = stick_thickness / 2.0

    # Create the base mesh (elongated box) geometry once to clone
    # Stick is long along X, square cross-section in Y-Z
    base_stick = Rhino.Geometry.Mesh.CreateFromBox(
        Rhino.Geometry.Box(Rhino.Geometry.Plane.WorldXY,
        Rhino.Geometry.Interval(-half_l, half_l),  # Length along X
        Rhino.Geometry.Interval(-half_t, half_t),   # Thickness Y
        Rhino.Geometry.Interval(-half_t, half_t)),   # Thickness Z
        1, 1, 1
    )

    try:
        for i in range(num_sticks):
            rs.StatusBarProgressMeterUpdate(i, True)

            if i % 10 == 0:
                rs.Prompt("Stacking stick {} of {}...".format(i+1, num_sticks))

            # 1. Spawn Position
            # Gaussian distribution for natural conical piling
            angle = random.uniform(0, 2 * math.pi)
            r_dist = abs(random.gauss(0, pile_radius / 2.5))

            dx = r_dist * math.cos(angle)
            dy = r_dist * math.sin(angle)

            spawn_x = center.X + dx
            spawn_y = center.Y + dy

            # 2. Orientation - sticks get random rotation on ALL axes for chaotic tumble
            rot_z = random.uniform(0, 360)
            # Tilt from horizontal: mostly flat but some steep angles
            # Use a distribution biased towards flatter angles for natural piling
            rot_x = random.gauss(0, 25)  # Mostly flat, occasional steep tilt
            rot_y = random.gauss(0, 25)

            # 3. Create Candidate Mesh
            temp_mesh = base_stick.Duplicate()

            # Rotate around X (tilt forward/back)
            xform_rx = Rhino.Geometry.Transform.Rotation(
                math.radians(rot_x), Rhino.Geometry.Vector3d.XAxis, Rhino.Geometry.Point3d.Origin)
            temp_mesh.Transform(xform_rx)

            # Rotate around Y (tilt side to side)
            xform_ry = Rhino.Geometry.Transform.Rotation(
                math.radians(rot_y), Rhino.Geometry.Vector3d.YAxis, Rhino.Geometry.Point3d.Origin)
            temp_mesh.Transform(xform_ry)

            # Rotate around Z (spin)
            xform_rz = Rhino.Geometry.Transform.Rotation(
                math.radians(rot_z), Rhino.Geometry.Vector3d.ZAxis, Rhino.Geometry.Point3d.Origin)
            temp_mesh.Transform(xform_rz)

            # Move to XY position (at Z=0 initially)
            xform_move = Rhino.Geometry.Transform.Translation(spawn_x, spawn_y, 0)
            temp_mesh.Transform(xform_move)

            # 4. Collision Detection (The Drop)
            highest_hit_z = center.Z  # Ground level

            if len(placed_meshes) > 0:
                # For sticks, we need MORE sample points along the length
                # to catch collisions properly with the elongated shape.

                # Get ALL mesh vertices as test points (8 for a box)
                # Plus additional sample points along the stick's length
                test_points = []
                bbox = temp_mesh.GetBoundingBox(True)

                # Use all 8 vertices of the mesh
                for v in temp_mesh.Vertices:
                    test_points.append(Rhino.Geometry.Point3d(v))

                # Add bounding box center
                bb_center = bbox.Center
                test_points.append(Rhino.Geometry.Point3d(bb_center.X, bb_center.Y, bbox.Min.Z))

                # Add midpoints along the stick length (interpolate between end vertices)
                # For better coverage, add midpoints between vertex pairs
                verts = [Rhino.Geometry.Point3d(v) for v in temp_mesh.Vertices]
                if len(verts) >= 2:
                    # Add midpoints between pairs of vertices for denser coverage
                    for vi in range(len(verts)):
                        for vj in range(vi + 1, len(verts)):
                            mid = Rhino.Geometry.Point3d(
                                (verts[vi].X + verts[vj].X) / 2.0,
                                (verts[vi].Y + verts[vj].Y) / 2.0,
                                min(verts[vi].Z, verts[vj].Z)
                            )
                            test_points.append(mid)

                # Raycast Vector: Down
                down_vec = Rhino.Geometry.Vector3d(0, 0, -1)

                # 4a. Check rays from NEW stick DOWN to OLD pile
                for pt in test_points:
                    ray = Rhino.Geometry.Ray3d(
                        Rhino.Geometry.Point3d(pt.X, pt.Y, 10000), down_vec)

                    hits = Rhino.Geometry.Intersect.Intersection.RayShoot(ray, placed_meshes, 1)
                    if hits and len(hits) > 0:
                        hit_pt = hits[0]
                        if hit_pt.Z > highest_hit_z:
                            highest_hit_z = hit_pt.Z

                # 4b. Check rays from OLD sticks UP to NEW stick
                # Prevents old stick corners from penetrating new stick faces.
                new_bbox_xy = temp_mesh.GetBoundingBox(True)

                up_vec = Rhino.Geometry.Vector3d(0, 0, 1)

                # Filter candidates by bounding box overlap in XY
                close_meshes = []
                for pm in placed_meshes:
                    pm_bbox = pm.GetBoundingBox(True)
                    if pm_bbox.Max.X < new_bbox_xy.Min.X or pm_bbox.Min.X > new_bbox_xy.Max.X:
                        continue
                    if pm_bbox.Max.Y < new_bbox_xy.Min.Y or pm_bbox.Min.Y > new_bbox_xy.Max.Y:
                        continue
                    close_meshes.append(pm)

                for pm in close_meshes:
                    for v in pm.Vertices:
                        # Raycast DOWN from high Z at vertex XY against NEW mesh
                        ray_check = Rhino.Geometry.Ray3d(
                            Rhino.Geometry.Point3d(v.X, v.Y, 1000), down_vec)
                        hits = Rhino.Geometry.Intersect.Intersection.MeshRay(temp_mesh, ray_check)
                        if hits >= 0.0:
                            hit_pt_on_mesh = ray_check.PointAt(hits)
                            required_z = v.Z + (0 - hit_pt_on_mesh.Z)
                            if required_z > highest_hit_z:
                                highest_hit_z = required_z

            # 5. Place it
            # The mesh was created centered at origin with Z from -half_t to +half_t.
            # After rotation, the bounding box bottom may have shifted.
            # We need to find the CURRENT lowest Z of the mesh and raise it to highest_hit_z.

            current_bbox = temp_mesh.GetBoundingBox(True)
            current_min_z = current_bbox.Min.Z

            # We want the bottom of the stick to sit at highest_hit_z
            z_offset = highest_hit_z - current_min_z

            xform_final = Rhino.Geometry.Transform.Translation(0, 0, z_offset)
            temp_mesh.Transform(xform_final)

            placed_meshes.append(temp_mesh)

    except Exception as e:
        print("Error: {}".format(e))

    finally:
        # Bake meshes
        rs.StatusBarProgressMeterShow("Baking Meshes", 0, len(placed_meshes), True, True)

        for i, m in enumerate(placed_meshes):
            rs.StatusBarProgressMeterUpdate(i, True)
            sc.doc.Objects.AddMesh(m)

        rs.StatusBarProgressMeterHide()
        rs.EnableRedraw(True)
        sc.doc.Views.Redraw()
        print("Stacked {} sticks.".format(len(placed_meshes)))

    return True

if __name__ == "__main__":
    create_rigid_stick_pile()
