"""Rhino document boundary for Array Studio. Call on Rhino's UI thread only.

Preview owns geometry but never adds objects to the document. Output preserves
block instances and treats the entire source selection as one repeatable unit.
"""

import Rhino
import System
from System.Drawing import Color
from System.Collections.Generic import List

RG = Rhino.Geometry


def _dispose(items):
    for item in items:
        item.Dispose()


def _wire_geometry(obj, accumulated, ancestors=()):
    """Yield independent world-space geometry, recursively expanding blocks."""
    if isinstance(obj, Rhino.DocObjects.InstanceObject):
        definition = obj.InstanceDefinition
        if definition is None or definition.IsDeleted:
            raise ValueError("A source block definition is unavailable.")
        if definition.Id in ancestors:
            raise ValueError("A source block contains a circular reference.")
        combined = accumulated * obj.InstanceXform
        for child in definition.GetObjects():
            for geometry in _wire_geometry(child, combined, ancestors + (definition.Id,)):
                yield geometry
        return
    geometry = obj.Geometry.Duplicate()
    if geometry is None:
        raise ValueError("A source object could not be copied.")
    if isinstance(geometry, (RG.Surface, RG.Extrusion)):
        surface = geometry
        geometry = surface.ToBrep()
        surface.Dispose()
        if geometry is None:
            raise ValueError("A source surface could not be prepared for preview.")
    if not isinstance(geometry, (RG.Curve, RG.Brep, RG.Mesh, RG.Extrusion, RG.Point, RG.PointCloud)):
        geometry.Dispose()
        raise ValueError("Use curves, surfaces, polysurfaces, meshes, points, or blocks containing these objects.")
    if not geometry.Transform(accumulated):
        geometry.Dispose()
        raise ValueError("A source object could not be transformed for preview.")
    yield geometry


class _Preview(Rhino.Display.DisplayConduit):
    def __init__(self, owner):
        super().__init__()
        self.owner = owner
        self.transforms = []
        self.bounds = RG.BoundingBox.Empty
        self.color = Color.FromArgb(55, 185, 230)
        self.style = "Wireframe"
        self.material = Rhino.Display.DisplayMaterial(self.color)

    def CalculateBoundingBox(self, event):
        if (event.RhinoDoc is not None
                and event.RhinoDoc.RuntimeSerialNumber == self.owner.doc.RuntimeSerialNumber
                and self.bounds.IsValid):
            event.IncludeBoundingBox(self.bounds)

    def CalculateBoundingBoxZoomExtents(self, event):
        self.CalculateBoundingBox(event)

    def PostDrawObjects(self, event):
        # A conduit is global; never draw this document's preview in another.
        if (event.RhinoDoc is None
                or event.RhinoDoc.RuntimeSerialNumber != self.owner.doc.RuntimeSerialNumber):
            return
        display = event.Display
        for transform in self.transforms:
            display.PushModelTransform(transform)
            try:
                for geometry in self.owner._wires:
                    if isinstance(geometry, RG.Curve):
                        display.DrawCurve(geometry, self.color, 1)
                    elif isinstance(geometry, RG.Brep):
                        if self.style == "Shaded":
                            display.DrawBrepShaded(geometry, self.material)
                        else:
                            display.DrawBrepWires(geometry, self.color, -1)
                    elif isinstance(geometry, RG.Mesh):
                        if self.style == "Shaded":
                            display.DrawMeshShaded(geometry, self.material)
                        else:
                            display.DrawMeshWires(geometry, self.color)
                    elif isinstance(geometry, RG.Point):
                        display.DrawPoint(geometry.Location, self.color)
                    elif isinstance(geometry, RG.PointCloud):
                        display.DrawPointCloud(geometry, 2, self.color)
            finally:
                display.PopModelTransform()


class SourceSet:
    """Captured source geometry and attributes; dispose when closing the UI."""

    def __init__(self, doc, object_ids):
        self.doc = doc
        self._sources = []
        self._wires = []
        self._disposed = False
        self.bbox = RG.BoundingBox.Empty
        self._conduit = _Preview(self)
        # Expand selected groups, including nested group memberships, once.
        pending = list(object_ids)
        seen = set()
        try:
            while pending:
                object_id = pending.pop(0)
                if object_id in seen:
                    continue
                seen.add(object_id)
                obj = doc.Objects.FindId(object_id)
                if obj is None or obj.IsDeleted:
                    raise ValueError("A selected source object no longer exists.")
                for group_index in obj.Attributes.GetGroupList() or []:
                    pending.extend(member.Id for member in doc.Objects.FindByGroup(group_index))
                attributes = obj.Attributes.Duplicate()
                attributes.RemoveFromAllGroups()
                attributes.ObjectId = System.Guid.Empty
                attributes.Mode = Rhino.DocObjects.ObjectMode.Normal
                if isinstance(obj, Rhino.DocObjects.InstanceObject):
                    if obj.InstanceDefinition is None:
                        raise ValueError("A source block definition is unavailable.")
                    source = (None, attributes, obj.InstanceDefinition.Index, obj.InstanceXform)
                else:
                    geometry = obj.Geometry.Duplicate()
                    if geometry is None:
                        raise ValueError("A source object could not be copied.")
                    source = (geometry, attributes, None, None)
                self._sources.append(source)
                for wire in _wire_geometry(obj, RG.Transform.Identity):
                    self._wires.append(wire)
                    self.bbox.Union(wire.GetBoundingBox(True))
            if not self._sources or not self.bbox.IsValid:
                raise ValueError("Select at least one valid source object.")
            self.base_point = self.bbox.Center
        except Exception:
            self.dispose()
            raise

    @property
    def count(self):
        return len(self._sources)

    def _check(self):
        if self._disposed:
            raise RuntimeError("The source selection has been disposed.")

    def preview(self, transforms):
        self._check()
        transforms = list(transforms)
        bounds = RG.BoundingBox.Empty
        for transform in transforms:
            if not transform.IsValid:
                raise ValueError("Array contains an invalid transformation.")
            copy_bounds = RG.BoundingBox(self.bbox.Min, self.bbox.Max)
            copy_bounds.Transform(transform)
            bounds.Union(copy_bounds)
        self._conduit.transforms = transforms
        self._conduit.bounds = bounds
        self._conduit.Enabled = bool(transforms)
        self.doc.Views.Redraw()

    def set_preview_style(self, style="Wireframe", color=None):
        """Set viewport-only appearance. Color is a System.Drawing.Color."""
        self._check()
        if style not in ("Wireframe", "Shaded"):
            raise ValueError("Preview style must be Wireframe or Shaded.")
        if color is None:
            color = self._conduit.color
        if not isinstance(color, Color):
            raise ValueError("Preview color must be a System.Drawing.Color.")
        self._conduit.material.Diffuse = color
        self._conduit.color = color
        self._conduit.style = style
        self.doc.Views.Redraw()

    def clear_preview(self):
        self._conduit.Enabled = False
        self._conduit.transforms = []
        self._conduit.bounds = RG.BoundingBox.Empty
        self.doc.Views.Redraw()

    def create(self, transforms):
        """Create atomically, preserving sources; one undo record per batch."""
        self._check()
        transforms = list(transforms)
        if not transforms:
            raise ValueError("There are no placements to create.")
        if any(not transform.IsValid for transform in transforms):
            raise ValueError("Array contains an invalid transformation.")
        for _, _, definition_index, _ in self._sources:
            if definition_index is not None:
                definition = self.doc.InstanceDefinitions[definition_index]
                if definition is None or definition.IsDeleted:
                    raise ValueError("A source block definition was deleted; select sources again.")
        added = []
        groups = []
        undo = self.doc.BeginUndoRecord("Array Studio")
        try:
            for transform in transforms:
                unit = List[System.Guid]()
                for geometry, attributes, definition_index, instance_transform in self._sources:
                    if definition_index is not None:
                        new_id = self.doc.Objects.AddInstanceObject(
                            definition_index, transform * instance_transform, attributes)
                    else:
                        duplicate = geometry.Duplicate()
                        try:
                            if not duplicate.Transform(transform):
                                raise ValueError("A copy could not be transformed.")
                            new_id = self.doc.Objects.Add(duplicate, attributes)
                        finally:
                            duplicate.Dispose()
                    if new_id == System.Guid.Empty:
                        raise RuntimeError("Rhino could not add an array object.")
                    added.append(new_id)
                    unit.Add(new_id)
                if unit.Count > 1:
                    group = self.doc.Groups.Add(unit)
                    if group < 0:
                        raise RuntimeError("Rhino could not group an array copy.")
                    groups.append(group)
        except Exception:
            for new_id in reversed(added):
                self.doc.Objects.Delete(new_id, True)
            for group in reversed(groups):
                self.doc.Groups.Delete(group)
            raise
        finally:
            if undo:
                self.doc.EndUndoRecord(undo)
            self.doc.Views.Redraw()
        self.clear_preview()
        self.doc.Objects.UnselectAll()
        for new_id in added:
            self.doc.Objects.Select(new_id)
        self.doc.Views.Redraw()
        return added

    def dispose(self):
        if self._disposed:
            return
        self.clear_preview()
        self._conduit.material.Dispose()
        _dispose(self._wires)
        for geometry, attributes, _, _ in self._sources:
            if geometry is not None:
                geometry.Dispose()
            attributes.Dispose()
        self._wires = []
        self._sources = []
        self._disposed = True


def capture_sources(doc, object_ids):
    return SourceSet(doc, object_ids)


def adopt_source(source):
    """Transfer a captured selection to freshly reloaded development classes."""
    if source is None or isinstance(source, SourceSet):
        return source
    source.clear_preview()
    material = getattr(source._conduit, 'material', None)
    if material is not None:
        material.Dispose()
    fresh = SourceSet.__new__(SourceSet)
    fresh.__dict__.update(source.__dict__)
    fresh._conduit = _Preview(fresh)
    # Older live versions stored extrusions directly; normalize for shaded draw.
    wires = []
    for geometry in fresh._wires:
        if isinstance(geometry, RG.Extrusion):
            brep = geometry.ToBrep()
            geometry.Dispose()
            wires.append(brep)
        else:
            wires.append(geometry)
    fresh._wires = wires
    source._sources = []
    source._wires = []
    source._disposed = True
    return fresh
