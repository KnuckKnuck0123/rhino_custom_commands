import rhinoscriptsyntax as rs
import random
import math

def create_random_pile():
    """
    Creates a random pile of bricks.
    """
    # 1. Get user inputs
    num_bricks = rs.GetInteger("Number of bricks", 100, 1, 5000)
    if num_bricks is None: return

    # Default brick size (approx standard proportions 8:4:2.5)
    l = 20.0
    w = 10.0
    h = 5.0

    # Get center point for the pile
    center = rs.GetPoint("Select center point for the pile")
    if not center: return

    rs.EnableRedraw(False)
    rs.StatusBarProgressMeterShow("Building Pile", 0, num_bricks, True, True)

    try:
        # 2. Generate bricks
        for i in range(num_bricks):
            rs.StatusBarProgressMeterUpdate(i, True)
            
            # Allow cancellation checking (Rhino logic usually handles escape in loops efficiently but check periodically)
            if i % 10 == 0:
                rs.Prompt("Building brick {} of {}...".format(i+1, num_bricks))
            
            # Algorithm:
            # We want a somewhat conical pile.
            # Bricks higher up should be more centered.
            # Bricks lower down can be more spread out.
            
            # Progress 0.0 to 1.0
            t = float(i) / float(num_bricks)
            
            # Radius decreases as we go up, but with randomness
            # A simple approximation: 
            # Height increases with i
            # Spread depends on how many bricks are below.
            
            # Let's try a specific volume approach:
            # Random gaussian distribution tends to look like a clump.
            
            # Random position in X, Y
            # Use gaussian for natural "pile" falloff
            spread = l * 3.0 # Base spread factor
            
            # Variation 1: Gaussian clump
            x_off = random.gauss(0, spread)
            y_off = random.gauss(0, spread)
            
            # Z position: 
            # In a real pile, height depends on x/y (higher in middle).
            # Bell curve for Z based on distance from center.
            dist = math.sqrt(x_off**2 + y_off**2)
            
            # Approximate height of pile at this distance
            # Max height in center proportional to total bricks?
            # Let's just stack them randomly in Z but constrained by a cone.
            # Cone defined by: H = MaxH - Slope * Dist
            
            # Alternatively, simpler approach for visual effect:
            # Just scatter them in a bounding cylinder, but bias Z to be higher if X,Y is central.
            
            # Simplest workable "Pile":
            # 1. Pick random pt in circle.
            # 2. Z is random but generally higher for later bricks? No, physics doesn't verify order.
            
            # Let's just place them explicitly.
            # X, Y = uniform random in disk.
            # Z = a function of distance from center + randomness.
            # H(r) = H_max * exp(-r^2 / sigma^2)  (Gaussian heap)
            
            # Peak height approx
            h_peak = num_bricks * h * 0.05 # rough guess
            sigma = spread * 1.5
            
            pile_z = h_peak * math.exp(-(dist**2)/(2*sigma**2))
            
            # Randomize z slightly around that theoretical surface
            z_off = random.uniform(0, pile_z)
            
            # Absolute pos
            pos = [center.X + x_off, center.Y + y_off, center.Z + z_off]
            
            # Create the brick at origin first for easy rotation
            # Box corners
            # 0,0,0 is corner. 
            # Let's center the box on 0,0,0
            corners = [
                [-l/2, -w/2, -h/2], [l/2, -w/2, -h/2], [l/2, w/2, -h/2], [-l/2, w/2, -h/2],
                [-l/2, -w/2, h/2],  [l/2, -w/2, h/2],  [l/2, w/2, h/2],  [-l/2, w/2, h/2]
            ]
            
            box_id = rs.AddBox(corners)
            
            # Random Rotation
            # Rotate around X, Y, Z axes
            rot_x = random.uniform(0, 360)
            rot_y = random.uniform(0, 360) 
            rot_z = random.uniform(0, 360)
            
            rs.RotateObject(box_id, [0,0,0], rot_z, [0,0,1])
            rs.RotateObject(box_id, [0,0,0], rot_x, [1,0,0])
            rs.RotateObject(box_id, [0,0,0], rot_y, [0,1,0])
            
            # Move to position
            rs.MoveObject(box_id, pos)
            
    finally:
        rs.StatusBarProgressMeterHide()
        rs.EnableRedraw(True)
        print("Done creating pile.")

if __name__ == "__main__":
    create_random_pile()
