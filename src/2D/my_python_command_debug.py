import rhinoscriptsyntax as rs
import debugpy

# Set the host and port for the debugger to listen on.
debug_host = "127.0.0.1"
debug_port = 5678

# Enable debugging and wait for a client to attach.
debugpy.listen((debug_host, debug_port))
print(f"Waiting for debugger to attach on {debug_host}:{debug_port}...")
debugpy.wait_for_client()
print("Debugger attached!")

def MyPythonCommandDebug():
    """
    This is a sample Python command for Rhino that is ready for debugging.
    """
    print("Hello from MyPythonCommandDebug!")
    
    # Add a point to the document
    point = (20, 20, 0)
    rs.AddPoint(point)
    
    # Redraw the viewports to see the new point
    rs.Redraw()

if __name__ == "__main__":
    MyPythonCommandDebug()
