#! python 3
"""Development launcher; the published Rhino command is ArrayStudio."""
import os
import sys
def main(case=None):
    source_path = os.path.dirname(os.path.abspath(__file__))
    if source_path not in sys.path:
        sys.path.insert(0, source_path)
    from array_tools.app import main as run
    run(case, reload_modules=True)


if __name__ == '__main__':
    main()
