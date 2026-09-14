"""Cross-platform Eto interface; all Rhino work stays on the UI thread."""
import math
import Rhino
import Rhino.Geometry as rg
import rhinoscriptsyntax as rs
import scriptcontext as sc
import Eto.Forms as ef
import Eto.Drawing as ed
from System.Drawing import Color
from .engine import build_transforms, DEFAULTS
from .objects import capture_sources


def widget(kind, **properties):
    control = kind()
    for name, value in properties.items():
        setattr(control, name, value)
    return control


def label(text):
    return widget(ef.Label, Text=text)


def dropdown(items, selected=0):
    control = ef.DropDown()
    control.DataStore = items
    control.SelectedIndex = selected
    return control


class Number:
    def __init__(self, value, low, high, changed, integer=False):
        self.low, self.high, self.busy = low, high, False
        self.slider_low = max(low, -100) if low < 0 else low
        self.slider_high = min(high, max(100, value * 4)) if high > 1000 and not integer else high
        self.input = ef.NumericUpDown()
        self.input.DecimalPlaces = 0 if integer else 3
        self.input.MinValue = low
        self.input.MaxValue = high
        self.input.Value = value
        self.input.Width = 85
        self.slider = widget(ef.Slider, MinValue=0, MaxValue=1000)
        self.slider.Width = 115
        self.slider.Value = int(1000 * (value - self.slider_low) / (self.slider_high - self.slider_low))
        self.changed = changed
        self.integer = integer
        self.input.ValueChanged += self.from_input
        self.slider.ValueChanged += self.from_slider

    def from_input(self, sender, event):
        if self.busy:
            return
        self.busy = True
        value = float(self.input.Value)
        self.slider_low = min(self.slider_low, value)
        self.slider_high = max(self.slider_high, value)
        self.slider.Value = int(1000 * (value - self.slider_low) / (self.slider_high - self.slider_low))
        self.busy = False
        self.changed()

    def from_slider(self, sender, event):
        if self.busy:
            return
        self.busy = True
        value = self.slider_low + self.slider.Value / 1000.0 * (self.slider_high - self.slider_low)
        self.input.Value = round(value) if self.integer else value
        self.busy = False
        self.changed()

    @property
    def value(self):
        return int(self.input.Value) if self.integer else float(self.input.Value)


class ZonePreview(Rhino.Display.DisplayConduit):
    def __init__(self, doc):
        super().__init__()
        self.doc = doc
        self.circles = []

    def CalculateBoundingBox(self, e):
        if e.RhinoDoc != self.doc:
            return
        for circle in self.circles:
            e.IncludeBoundingBox(circle.BoundingBox)

    def DrawForeground(self, e):
        if e.RhinoDoc == self.doc:
            for circle in self.circles:
                e.Display.DrawCircle(circle, Color.Orange, 2)


class ArrayToolsWindow(ef.Form):
    def __init__(self, doc, case='Profiles'):
        super().__init__()
        self.doc = doc
        self.case = case
        self.Title = {'Profiles': 'Profile Array', 'AlongCurve': 'Along Curve', 'Surface': 'Surface Array', 'Volume': 'Volume Array'}[case]
        self.ClientSize = ed.Size(640, 640)
        self.MinimumSize = ed.Size(600, 500)
        self.Padding = ed.Padding(12)
        self.source = None
        self.target = None
        self.target_ref = None
        self.base = rg.Plane(doc.Views.ActiveView.ActiveViewport.ConstructionPlane())
        self.center = rg.Point3d(self.base.Origin)
        self.dirty = False
        self.closed = False
        self.zone = ZonePreview(doc)
        self.numbers = {}
        self.rows = {}
        self.titles = {}
        self.status = label('Select source curves, polysurfaces, a group, or a block.')
        self.status.Wrap = ef.WrapMode.Word
        self.status.Height = 52
        self.source_label = label('No source selected')
        self.target_label = label('No target selected')
        self.mode = dropdown(['Linear', 'Grid', 'Curve', 'Surface', 'Volume'], {'Profiles': 1, 'AlongCurve': 2, 'Surface': 3, 'Volume': 4}[case])
        self.pattern = dropdown(['Linear', 'Grid'], 1)
        self.pattern.SelectedIndexChanged += self.on_pattern
        self.volume_mode = dropdown(['Exterior', 'Interior'])
        self.orient = widget(ef.CheckBox, Text='Follow curve / surface orientation', Checked=True)
        self.variation = dropdown(['None', 'Random', 'Gradual'])
        self.uniform = widget(ef.CheckBox, Text='Uniform scale — same in all directions', Checked=True)
        self.progression = dropdown(['X / U', 'Y / V', 'Z'])
        self.falloff = widget(ef.CheckBox, Text='Enable falloff zone', Checked=False)
        self.live = widget(ef.CheckBox, Text='Live preview', Checked=True)
        preview_prefs = sc.sticky.get('nk_array_tools_preview', ('Wireframe', (55, 185, 230)))
        self.preview_style = dropdown(['Wireframe', 'Shaded'], 1 if preview_prefs[0] == 'Shaded' else 0)
        self.preview_color = ef.ColorPicker()
        self.preview_color.Value = ed.Color.FromArgb(*preview_prefs[1])
        self.preview_color.Width = 70
        self.preview_style.SelectedIndexChanged += self.on_preview_change
        self.preview_color.ValueChanged += self.on_preview_change
        self.center_label = label('Center: source base point')
        for control in (self.mode, self.volume_mode, self.variation, self.progression):
            control.SelectedIndexChanged += self.on_change
        for control in (self.orient, self.falloff, self.live, self.uniform):
            control.CheckedChanged += self.on_change

        tabs = ef.TabControl()
        tabs.Pages.Add(self.placement_page())
        tabs.Pages.Add(self.variation_page())
        tabs.Pages.Add(self.falloff_page())
        # Only the settings row stretches. Header and actions keep their height.
        tabs.MinimumSize = ed.Size(0, 0)
        self.settings_tabs = tabs
        root = widget(ef.TableLayout, Spacing=ed.Size(8, 8))
        self.back_button = self.button('‹ All array tools', self.go_back)
        self.create_button = self.button('Create array', self.create)
        self.cancel_button = self.button('Cancel / Close', lambda: self.Close())
        controls = [self.back_button,
                    self.row(self.button('Select source', self.pick_source), self.source_label),
                    self.row(self.button('Pick base point', self.pick_base), label('Axes follow the construction plane.')),
                    tabs,
                    self.row(label('Preview'), self.preview_style, label('Color'), self.preview_color),
                    self.row(self.live, self.button('Refresh preview', self.refresh)),
                    self.status,
                    self.row(self.create_button, self.cancel_button)]
        for control in controls:
            cell = ef.TableCell(control)
            cell.ScaleWidth = True
            row = ef.TableRow(cell)
            row.ScaleHeight = control is tabs
            root.Rows.Add(row)
        self.Content = root
        self.timer = widget(ef.UITimer, Interval=0.25)
        self.timer.Elapsed += self.tick
        self.timer.Start()
        self.Closed += self.on_closed
        self.update_controls()

    def go_back(self):
        from .app import main
        main()

    def button(self, text, action):
        button = widget(ef.Button, Text=text)
        def clicked(sender, event):
            try:
                action()
            except Exception as error:
                self.report(error)
        button.Click += clicked
        return button

    def page(self, name):
        layout = widget(ef.DynamicLayout, Padding=ed.Padding(10), Spacing=ed.Size(8, 8))
        scroll = widget(ef.Scrollable, Content=layout)
        scroll.MinimumSize = ed.Size(0, 0)
        return widget(ef.TabPage, Text=name, Content=scroll), layout

    def add_number(self, layout, key, title, value, low, high, integer=False):
        number = Number(value, low, high, self.mark_dirty, integer)
        self.numbers[key] = number
        self.titles[key] = label(title)
        self.titles[key].Width = 160
        row = widget(ef.DynamicLayout, Spacing=ed.Size(8, 4))
        row.AddRow(self.titles[key], number.slider, number.input)
        self.rows[key] = row
        layout.AddRow(row)
        return number

    def placement_page(self):
        page, layout = self.page('Placement')
        if self.case == 'Profiles':
            layout.AddRow(label('Pattern'), self.pattern)
        self.volume_row = self.row(label('Place copies'), self.volume_mode)
        layout.AddRow(self.volume_row)
        self.target_row = self.row(self.button('Select target', self.pick_target), self.target_label)
        layout.AddRow(self.target_row)
        layout.AddRow(self.orient)
        for axis in 'xyz':
            self.add_number(layout, 'count_' + axis, 'Count ' + axis.upper(), DEFAULTS['count_' + axis], 1, 100, True)
        for axis in 'xy':
            self.add_number(layout, 'spacing_' + axis, 'Plan spacing ' + axis.upper(), 10, .001, 10000)
        note = label('')
        self.placement_note = note
        note.Wrap = ef.WrapMode.Word
        note.Width = 470
        layout.AddRow(note)
        layout.AddRow(None)
        return page

    def variation_page(self):
        page, layout = self.page('Variation')
        layout.AddRow(label('Variation style'), self.variation)
        self.progression_row = self.row(label('Change along'), self.progression)
        layout.AddRow(self.progression_row)
        self.add_number(layout, 'seed', 'Random seed', 1, 0, 100000, True)
        self.reroll_button = self.button('New random arrangement', self.reroll)
        layout.AddRow(self.reroll_button)
        note = label('')
        self.variation_note = note
        note.Wrap = ef.WrapMode.Word
        note.Width = 470
        layout.AddRow(note)
        sub = ef.TabControl()
        self.variation_tabs = sub
        for name, title, identity, low, high in [('shift', 'Shift', 0, -10000, 10000), ('rotate', 'Rotate', 0, -360, 360), ('scale', 'Scale', 1, .01, 10)]:
            child, fields = self.page(title)
            if name == 'scale':
                fields.AddRow(self.uniform)
            for index, axis in enumerate('XYZ'):
                for end, caption in [('start', 'A'), ('end', 'B')]:
                    self.add_number(fields, '{}_{}_{}'.format(name, end, index), '{} {}'.format(axis, caption), identity, low, high)
            sub.Pages.Add(child)
        layout.AddRow(sub)
        layout.AddRow(None)
        return page

    def falloff_page(self):
        page, layout = self.page('Falloff')
        layout.AddRow(self.falloff)
        layout.AddRow(self.button('Pick zone center', self.pick_center), self.center_label)
        self.add_number(layout, 'falloff_radius', 'Radius', 50, .001, 10000)
        self.add_number(layout, 'falloff_strength', 'Strength', 1, 0, 1)
        self.add_number(layout, 'falloff_softness', 'Softness', 1, 0, 1)
        note = label('Variation is strongest near the center and fades to the ordinary array outside the zone. This changes shift, rotation and scale, not copy count. Plan uses a circle; 3D modes use a sphere.')
        note.Wrap = ef.WrapMode.Word
        note.Width = 470
        layout.AddRow(note)
        layout.AddRow(None)
        return page

    def settings(self):
        settings = dict(DEFAULTS)
        for key in ('count_x', 'count_y', 'count_z', 'spacing_x', 'spacing_y', 'seed', 'falloff_radius', 'falloff_strength', 'falloff_softness'):
            settings[key] = self.numbers[key].value
        for name in ('shift', 'rotate', 'scale'):
            for end in ('start', 'end'):
                settings[name + '_' + end] = tuple(self.numbers['{}_{}_{}'.format(name, end, i)].value for i in range(3))
        settings.update(mode=['Linear', 'Grid', 'Curve', 'Surface', 'Volume'][self.mode.SelectedIndex],
                        volume_mode=['Exterior', 'Interior'][self.volume_mode.SelectedIndex],
                        uniform_scale=bool(self.uniform.Checked), orient=bool(self.orient.Checked), variation=['None', 'Random', 'Gradual'][self.variation.SelectedIndex],
                        progression='XYZ'[self.progression.SelectedIndex], falloff_enabled=bool(self.falloff.Checked),
                        falloff_center=(self.center.X, self.center.Y, self.center.Z))
        return settings

    def on_preview_change(self, sender, event):
        try:
            value = self.preview_color.Value
            rgb = tuple(int(round(max(0., min(1., float(channel))) * 255)) for channel in (value.R, value.G, value.B))
            style = ['Wireframe', 'Shaded'][self.preview_style.SelectedIndex]
            sc.sticky['nk_array_tools_preview'] = (style, rgb)
            if self.source:
                self.source.set_preview_style(style, Color.FromArgb(*rgb))
        except Exception as error:
            self.report(error)

    def ensure_doc(self):
        if Rhino.RhinoDoc.ActiveDoc is None or Rhino.RhinoDoc.ActiveDoc.RuntimeSerialNumber != self.doc.RuntimeSerialNumber:
            raise ValueError('Activate the document where you opened Array Studio.')

    def pick(self, callback):
        self.ensure_doc()
        self.Visible = False
        previous = sc.doc
        try:
            sc.doc = self.doc
            callback()
        finally:
            sc.doc = previous
            self.Visible = True
            self.BringToFront()
            self.mark_dirty()

    def pick_source(self):
        def run():
            ids = rs.GetObjects('Select source objects as one repeatable unit', 4 | 8 | 16 | 4096, group=True, preselect=True)
            if not ids:
                return
            candidate = capture_sources(self.doc, ids)
            if self.source:
                self.source.dispose()
            self.source = candidate
            self.base = rg.Plane(self.doc.Views.ActiveView.ActiveViewport.ConstructionPlane())
            self.base.Origin = candidate.base_point
            self.center = rg.Point3d(candidate.base_point)
            self.source_label.Text = '{} source objects'.format(candidate.count)
            self.center_label.Text = 'Center: {:.2f}, {:.2f}, {:.2f}'.format(self.center.X, self.center.Y, self.center.Z)
        self.pick(run)

    def pick_base(self):
        def run():
            point = rs.GetPoint('Pick the source unit base point')
            if point is not None:
                self.base.Origin = point
        self.pick(run)

    def pick_center(self):
        def run():
            point = rs.GetPoint('Pick falloff zone center')
            if point is not None:
                self.center = point
                self.center_label.Text = 'Center: {:.2f}, {:.2f}, {:.2f}'.format(point.X, point.Y, point.Z)
        self.pick(run)

    def pick_target(self):
        def run():
            mode = self.settings()['mode']
            if mode in ('Linear', 'Grid'):
                self.status.Text = 'Plan arrays do not need a target.'
                return
            getter = Rhino.Input.Custom.GetObject()
            getter.SetCommandPrompt('Select target ' + ('curve' if mode == 'Curve' else 'surface or polysurface'))
            getter.GeometryFilter = Rhino.DocObjects.ObjectType.Curve if mode == 'Curve' else Rhino.DocObjects.ObjectType.Surface | Rhino.DocObjects.ObjectType.PolysrfFilter
            getter.SubObjectSelect = mode == 'Surface'
            getter.EnablePreSelect(False, True)
            getter.Get()
            if getter.CommandResult() != Rhino.Commands.Result.Success:
                getter.Dispose()
                return
            reference = getter.Object(0)
            if mode == 'Curve':
                geometry = reference.Curve().DuplicateCurve()
            elif mode == 'Surface' and reference.Face() is not None:
                geometry = reference.Face().DuplicateFace(False)
            else:
                geometry = reference.Brep().DuplicateBrep()
            if self.target:
                self.target.Dispose()
            self.target = geometry
            self.target_label.Text = mode + ' target selected'
            getter.Dispose()
        self.pick(run)

    def reroll(self):
        control = self.numbers['seed'].input
        control.Value = (int(control.Value) + 1) % 100001

    def row(self, *controls):
        row = widget(ef.DynamicLayout, Spacing=ed.Size(8, 4))
        row.AddRow(*controls)
        return row

    def update_controls(self):
        mode = ['Linear', 'Grid', 'Curve', 'Surface', 'Volume'][self.mode.SelectedIndex]
        volume = mode == 'Volume'
        interior = volume and self.volume_mode.SelectedIndex == 1
        uv = mode == 'Surface' or (volume and not interior)
        self.volume_row.Visible = volume
        self.target_row.Visible = mode not in ('Linear', 'Grid')
        self.orient.Visible = mode in ('Curve', 'Surface') or (volume and not interior)
        self.rows['count_y'].Visible = mode not in ('Linear', 'Curve')
        self.rows['count_z'].Visible = interior
        self.rows['spacing_x'].Visible = mode in ('Linear', 'Grid')
        self.rows['spacing_y'].Visible = mode == 'Grid'
        names = ['U count', 'V count', 'Depth count'] if uv else (['Columns', 'Rows', 'Layers'] if mode == 'Grid' or interior else ['Copies', 'Rows', 'Layers'])
        for axis, title in zip('xyz', names):
            self.titles['count_' + axis].Text = title
        self.placement_note.Text = ('Copies fill a 3D grid inside the volume. Their base points stay inside before variation; geometry may cross the boundary.' if interior else
                                    'Counts sample the surface in U and V without rebuilding it. Trimmed-out positions are skipped.' if uv else
                                    'Copies are evenly spaced along the curve. Local X follows its tangent when orientation is enabled.' if mode == 'Curve' else
                                    'Copies follow the construction plane. Spacing is measured between copy base points in model units.')
        variation = ['None', 'Random', 'Gradual'][self.variation.SelectedIndex]
        self.rows['seed'].Visible = variation == 'Random'
        self.reroll_button.Visible = variation == 'Random'
        self.progression_row.Visible = variation == 'Gradual' and mode not in ('Linear', 'Curve')
        self.variation_tabs.Visible = variation != 'None'
        self.variation_note.Text = ('Choose Random or Gradual to vary the copies.' if variation == 'None' else
                                    'Each copy gets values between your minimum and maximum. The seed keeps the arrangement repeatable.' if variation == 'Random' else
                                    'Values transition from start to end across the array.')
        for kind in ('shift', 'rotate', 'scale'):
            for axis, axis_name in enumerate('XYZ'):
                for end, caption in [('start', 'Minimum' if variation == 'Random' else 'Start'), ('end', 'Maximum' if variation == 'Random' else 'End')]:
                    key = '{}_{}_{}'.format(kind, end, axis)
                    self.rows[key].Visible = not (kind == 'scale' and self.uniform.Checked and axis > 0)
                    axis_label = '' if kind == 'scale' and self.uniform.Checked else axis_name + ' '
                    self.titles[key].Text = axis_label + caption + (' (degrees)' if kind == 'rotate' else '')

    def restore(self, snapshot):
        settings, source, base, center, target = snapshot
        self.source, self.base, self.center, self.target = source, base, center, target
        if source:
            self.source_label.Text = '{} source objects'.format(source.count)
        if target:
            self.target_label.Text = 'Target retained'
        self.center_label.Text = 'Center: {:.2f}, {:.2f}, {:.2f}'.format(center.X, center.Y, center.Z)
        for key, number in self.numbers.items():
            if key in settings:
                number.input.Value = settings[key]
            elif key.startswith(('shift_', 'rotate_', 'scale_')):
                name, end, axis = key.split('_')
                number.input.Value = settings[name + '_' + end][int(axis)]
        if self.case == 'Profiles':
            self.pattern.SelectedIndex = 0 if settings['mode'] == 'Linear' else 1
            self.mode.SelectedIndex = self.pattern.SelectedIndex
        self.volume_mode.SelectedIndex = ['Exterior', 'Interior'].index(settings['volume_mode'])
        self.variation.SelectedIndex = ['None', 'Random', 'Gradual'].index(settings['variation'])
        self.progression.SelectedIndex = 'XYZ'.index(settings['progression'])
        self.falloff.Checked = settings['falloff_enabled']
        self.orient.Checked = settings['orient']
        self.uniform.Checked = settings.get('uniform_scale', True)
        self.update_controls()
        self.mark_dirty()

    def on_pattern(self, sender, event):
        self.mode.SelectedIndex = self.pattern.SelectedIndex
        self.mark_dirty()

    def on_change(self, sender, event):
        if hasattr(self, 'variation_tabs') and 'falloff_radius' in self.numbers:
            self.update_controls()
        self.mark_dirty()

    def mark_dirty(self):
        self.dirty = True

    def tick(self, sender, event):
        if self.dirty and self.live.Checked and not self.closed and self.Visible:
            self.dirty = False
            self.refresh()

    def refresh(self):
        try:
            if not self.source:
                return
            self.ensure_doc()
            settings = self.settings()
            transforms, points = build_transforms(settings, self.base, self.target, self.doc.ModelAbsoluteTolerance)
            limit = max(1, min(1000, 5000 // self.source.count))
            preview = transforms if len(transforms) <= limit else [transforms[int(i * len(transforms) / limit)] for i in range(limit)]
            self.on_preview_change(None, None)
            self.source.preview(preview)
            self.zone.circles = []
            if settings['falloff_enabled']:
                normals = [self.base.ZAxis] if settings['mode'] in ('Linear', 'Grid') else [rg.Vector3d.XAxis, rg.Vector3d.YAxis, rg.Vector3d.ZAxis]
                self.zone.circles = [rg.Circle(rg.Plane(self.center, normal), settings['falloff_radius']) for normal in normals]
            self.zone.Enabled = bool(self.zone.circles)
            self.doc.Views.Redraw()
            self.status.Text = '{} copies ready. Preview shows {}. Originals are preserved.'.format(len(transforms), len(preview))
        except Exception as error:
            if self.source:
                self.source.clear_preview()
            self.zone.Enabled = False
            self.doc.Views.Redraw()
            self.report(error)

    def create(self):
        self.ensure_doc()
        if not self.source:
            raise ValueError('Select source objects first.')
        transforms, points = build_transforms(self.settings(), self.base, self.target, self.doc.ModelAbsoluteTolerance)
        if len(transforms) * self.source.count > 50000:
            raise ValueError('More than 50,000 output objects requested. Reduce counts.')
        ids = self.source.create(transforms)
        self.status.Text = 'Created {} objects.'.format(len(ids))
        self.Close()

    def report(self, error):
        self.status.Text = str(error)
        Rhino.RhinoApp.WriteLine('Array Studio: ' + str(error))

    def on_closed(self, sender, event):
        self.closed = True
        self.timer.Stop()
        self.timer.Elapsed -= self.tick
        self.timer.Dispose()
        self.zone.Enabled = False
        if self.source:
            self.source.dispose()
        if self.target:
            self.target.Dispose()
        self.doc.Views.Redraw()
        if sc.sticky.get('array_studio_window') is self:
            sc.sticky.pop('array_studio_window', None)
