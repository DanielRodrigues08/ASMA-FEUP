import matplotlib.pyplot as plt
import matplotlib.animation as animation
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from random import uniform



def create_gui(n, func, values, centers, bases,):
    

    # Initialize drone coordinates
    drone_coordinates = [(0, 0) for _ in range(n)]

    min_lon = values['min_lon']
    max_lon = values['max_lon']
    min_lat = values['min_lat']
    max_lat = values['max_lat']

    # Function to update drone positions (simulated movement)
    def update_positions(frame):
        
        # Simulate movement by updating coordinates randomly
        for i in range(n):
            drone_coordinates[i] = (func[i]['x'], func[i]['y'])

        # Clear previous plot
        ax.clear()
        
        # Set the map extent based on drone positions
        ax.set_extent([min_lon-0.05, max_lon+0.05, min_lat-0.05, max_lat+0.05], crs=ccrs.PlateCarree())
        
        # Plot world map background
        ax.add_feature(cfeature.COASTLINE)
        ax.add_feature(cfeature.BORDERS, linestyle=':')

        ax.stock_img()
        
        # Plot updated drone positions
        ax.scatter([lon for lat, lon in drone_coordinates], 
                [lat for lat, lon in drone_coordinates], 
                color='red', marker='o', transform=ccrs.PlateCarree())
        
        # Plot centers

        ax.scatter([lon for lat, lon in centers],
                   [lat for lat, lon in centers],
                color='blue', marker='^', transform=ccrs.PlateCarree())
        
        # Plot bases

        ax.scatter([lon for lat, lon in bases],
                     [lat for lat, lon in bases],
                 color='green', marker='s', transform=ccrs.PlateCarree())
        
        ax.set_title(f'Drone Positions - Frame {frame}')

    # Create a plot with Cartopy
    fig = plt.figure(figsize=(10, 8))
    ax = plt.axes(projection=ccrs.PlateCarree())

    # Plot world map background
    ax.add_feature(cfeature.COASTLINE)
    ax.add_feature(cfeature.BORDERS, linestyle=':')

    # Animate drone positions with FuncAnimation
    ani = animation.FuncAnimation(fig, update_positions, interval=16, blit=False)

    # Show the animation
    plt.title('Real-time Drone Movement')
    plt.show()
