"""Run in Rhino 8 Python 3. Uses a separate headless document, never user geometry.

Live viewport drawing and Undo still require the manual acceptance checklist.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "src"))

import Rhino
import System
from System.Collections.Generic import List
from array_tools.objects import capture_sources


def run():
    doc = Rhino.RhinoDoc.CreateHeadless(None)
    source = None
    RG = Rhino.Geometry
    try:
        first = doc.Objects.AddPoint(RG.Point3d(1, 2, 3))
        second = doc.Objects.AddPoint(RG.Point3d(4, 5, 6))
        members = List[System.Guid]()
        members.Add(first)
        members.Add(second)
        original_group = doc.Groups.Add(members)
        source = capture_sources(doc, [first])
        assert source.count == 2, "Selecting a group member must capture its unit"
        before = doc.Objects.Count
        source.set_preview_style('Shaded', System.Drawing.Color.Orange)
        assert source._conduit.style == 'Shaded'
        assert source._conduit.color == System.Drawing.Color.Orange
        source.set_preview_style('Wireframe', System.Drawing.Color.Cyan)
        source.preview([RG.Transform.Translation(10, 0, 0)])
        source.clear_preview()
        assert doc.Objects.Count == before, "Preview must not add document objects"
        added = source.create([RG.Transform.Translation(10, 0, 0),
                               RG.Transform.Translation(20, 0, 0)])
        assert len(added) == 4
        group_ids = [list(doc.Objects.FindId(i).Attributes.GetGroupList()) for i in added]
        assert group_ids[0] == group_ids[1]
        assert group_ids[2] == group_ids[3]
        assert group_ids[0] != group_ids[2]
        assert all(original_group not in ids for ids in group_ids)
        assert doc.Objects.FindId(first) is not None
        assert doc.Objects.FindId(second) is not None
        source.dispose()
        source = None

        geometry = List[RG.GeometryBase]()
        geometry.Add(RG.Point(RG.Point3d(1, 0, 0)))
        attributes = List[Rhino.DocObjects.ObjectAttributes]()
        attributes.Add(Rhino.DocObjects.ObjectAttributes())
        definition = doc.InstanceDefinitions.Add("ArrayToolsCheck", "", RG.Point3d.Origin,
                                                 geometry, attributes)
        block = doc.Objects.AddInstanceObject(definition, RG.Transform.Translation(2, 0, 0))
        source = capture_sources(doc, [block])
        added = source.create([RG.Transform.Translation(10, 0, 0)])
        instance = doc.Objects.FindId(added[0])
        assert isinstance(instance, Rhino.DocObjects.InstanceObject)
        assert instance.InstanceDefinition.Index == definition
        assert abs(instance.InstanceXform.M03 - 12) < 1e-9
        assert abs(source.bbox.Center.X - 3) < 1e-9
        print("PASS: preview isolation, group expansion/creation, block preservation/composition")
    finally:
        if source is not None:
            source.dispose()
        doc.Dispose()


if __name__ == "__main__":
    run()
