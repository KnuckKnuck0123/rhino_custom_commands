#! python 3
"""Open the dedicated SurfaceArray tool in Rhino 8."""
import os
import sys
source = os.path.dirname(os.path.abspath(__file__))
if source not in sys.path:
    sys.path.insert(0, source)
from ArrayTools import main
if __name__ == '__main__':
    main('Surface')
