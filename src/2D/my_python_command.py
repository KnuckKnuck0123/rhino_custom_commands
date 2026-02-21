import rhinoscriptsyntax as rs

def MyPythonCommand():
    """
    This is a sample Python command for Rhino.
    """
    print("Hello from MyPythonCommand!")
    
    # Add a point to the document
    point = (10, 10, 0)
    rs.AddPoint(point)
    
    # Redraw the viewports to see the new point
    rs.Redraw()

if __name__ == "__main__":
    MyPythonCommand()
