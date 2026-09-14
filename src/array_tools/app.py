"""Array Studio application lifecycle shared by source scripts and the plugin."""
import importlib

import Eto.Drawing as ed
import Eto.Forms as ef
import scriptcontext as sc
from Rhino.UI import EtoExtensions


CASES = (
    ('Profiles', 'Profile Array — linear / grid'),
    ('AlongCurve', 'Along Curve — 2D / 3D path'),
    ('Surface', 'Surface Array — U / V'),
    ('Volume', 'Volume Array — exterior / interior'),
)


def show_chooser(previous):
    old = sc.sticky.get('array_studio_chooser')
    if old is not None:
        old.BringToFront()
        return
    if previous is not None:
        previous.Visible = False

    chooser = ef.Form()
    chooser.Title = 'Array Studio'
    chooser.ClientSize = ed.Size(400, 320)
    chooser.MinimumSize = ed.Size(380, 300)
    chooser.Padding = ed.Padding(20)
    layout = ef.DynamicLayout()
    layout.Spacing = ed.Size(8, 12)
    heading = ef.Label()
    heading.Text = 'Choose an array tool'
    layout.AddRow(heading)
    switching = [False]

    for key, title in CASES:
        button = ef.Button()
        button.Text = title
        button.Height = 42

        def clicked(sender, event, chosen=key):
            switching[0] = True
            chooser.Close()
            main(chosen)

        button.Click += clicked
        layout.AddRow(button)

    def closed(sender, event):
        if sc.sticky.get('array_studio_chooser') is chooser:
            sc.sticky.pop('array_studio_chooser', None)
        if previous is not None and not previous.closed and not switching[0]:
            previous.Visible = True
            previous.BringToFront()

    chooser.Closed += closed
    chooser.Content = layout
    sc.sticky['array_studio_chooser'] = chooser
    EtoExtensions.Show(chooser, previous.doc if previous else sc.doc)


def main(case=None, reload_modules=False):
    previous = sc.sticky.get('array_studio_window')
    if case is None:
        show_chooser(previous)
        return

    snapshot = None
    doc = previous.doc if previous else sc.doc
    if previous is not None:
        settings = previous.settings()
        old_case = getattr(previous, 'case', 'Profiles')
        saved = sc.sticky.setdefault('array_studio_settings', {})
        saved[old_case] = settings
        settings = saved.get(case, settings)
        target = previous.target.Duplicate() if previous.target is not None and old_case == case else None
        snapshot = (settings, previous.source, previous.base, previous.center, target)
        previous.source = None
        previous.Close()

    if reload_modules:
        for name in ('variation', 'engine', 'objects', 'ui'):
            qualified = 'array_tools.' + name
            if qualified in __import__('sys').modules:
                importlib.reload(__import__(qualified, fromlist=[name]))

    from .ui import ArrayToolsWindow

    window = ArrayToolsWindow(doc, case)
    sc.sticky['array_studio_window'] = window
    if snapshot:
        from .objects import adopt_source
        settings, source, base, center, target = snapshot
        window.restore((settings, adopt_source(source), base, center, target))
    EtoExtensions.Show(window, doc)
