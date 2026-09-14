#! python 3
"""Check the editor-to-Rhino connection without changing the document."""
import Rhino


def main():
    Rhino.RhinoApp.WriteLine("Array tools: connected to Rhino {}.".format(Rhino.RhinoApp.Version))


if __name__ == "__main__":
    main()
