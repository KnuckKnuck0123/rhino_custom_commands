#! python 3
"""Open the tool chooser. Save and use Cmd/Ctrl+Shift+B to test in Rhino."""
import os
import sys
import importlib
import scriptcontext as sc


def show_chooser(previous):
    import Eto.Forms as ef
    import Eto.Drawing as ed
    from Rhino.UI import EtoExtensions
    old = sc.sticky.get('nk_array_tools_chooser')
    if old is not None:
        old.BringToFront()
        return
    if previous is not None:
        previous.Visible = False
    chooser = ef.Form()
    chooser.Title = 'Array Tools'
    chooser.ClientSize = ed.Size(400, 320)
    chooser.MinimumSize = ed.Size(380, 300)
    chooser.Padding = ed.Padding(20)
    layout = ef.DynamicLayout()
    layout.Spacing = ed.Size(8, 12)
    heading = ef.Label()
    heading.Text = 'Choose an array tool'
    layout.AddRow(heading)
    switching = [False]
    for key, title in [('Profiles', 'Profile Array — linear / grid'), ('AlongCurve', 'Along Curve — 2D / 3D path'), ('Surface', 'Surface Array — U / V'), ('Volume', 'Volume Array — exterior / interior')]:
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
        if sc.sticky.get('nk_array_tools_chooser') is chooser:
            sc.sticky.pop('nk_array_tools_chooser', None)
        if previous is not None and not previous.closed and not switching[0]:
            previous.Visible = True
            previous.BringToFront()
    chooser.Closed += closed
    chooser.Content = layout
    sc.sticky['nk_array_tools_chooser'] = chooser
    EtoExtensions.Show(chooser, previous.doc if previous else sc.doc)


def main(case=None):
    source_path = os.path.dirname(os.path.abspath(__file__))
    if source_path not in sys.path:
        sys.path.insert(0, source_path)
    previous = sc.sticky.get('nk_array_tools_window')
    if case is None:
        show_chooser(previous)
        return
    snapshot = None
    doc = previous.doc if previous else sc.doc
    if previous is not None:
        settings = previous.settings()
        old_case = getattr(previous, 'case', 'Profiles')
        saved = sc.sticky.setdefault('nk_array_tools_settings', {})
        saved[old_case] = settings
        settings = saved.get(case, settings)
        target = previous.target.Duplicate() if previous.target is not None and old_case == case else None
        snapshot = (settings, previous.source, previous.base, previous.center, target)
        previous.source = None
        previous.Close()
    # Reload the implementation so edits are picked up by the development hotkey.
    for name in ('variation', 'engine', 'objects', 'ui'):
        qualified = 'array_tools.' + name
        if qualified in sys.modules:
            importlib.reload(sys.modules[qualified])
    from array_tools.ui import ArrayToolsWindow
    from Rhino.UI import EtoExtensions
    window = ArrayToolsWindow(doc, case)
    sc.sticky['nk_array_tools_window'] = window
    if snapshot:
        from array_tools.objects import adopt_source
        settings, source, base, center, target = snapshot
        window.restore((settings, adopt_source(source), base, center, target))
    EtoExtensions.Show(window, doc)


if __name__ == '__main__':
    main()
