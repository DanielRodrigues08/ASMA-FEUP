import pygame
import math


def long_lat_to_xy(latitude, longitude):

    global center_lat, center_lon

    R = 6371

    # Convert latitude and longitude from degrees to radians
    lat_rad = math.radians(latitude)
    lon_rad = math.radians(longitude)
    center_lat_rad = math.radians(center_lat)
    center_lon_rad = math.radians(center_lon)

    # Calculate Cartesian coordinates
    x = R * math.cos(lat_rad) * math.sin(lon_rad - center_lon_rad)
    y = R * (math.cos(center_lat_rad) * math.sin(lat_rad) - math.sin(center_lat_rad) * math.cos(lat_rad) * math.cos(lon_rad - center_lon_rad))

    return x * 10, y * 10

class GameObject:
    def __init__(self, n, func):
        self.id = n
        self.func = func
        self.x  = 0
        self.y  = 0
        self.color = (255,255,255)

    def update(self):
        # Example: Move the object (change its position)

        drone_lat, drone_lon = self.func(self.id)
        self.x, self.y = long_lat_to_xy(drone_lat, drone_lon)


    def draw(self, surface):
        # Example: Draw the object on the surface
        pygame.draw.circle(surface, self.color, (self.x, self.y), 10)
    


def run_gui(n, func, lat, long):


    global center_lat, center_lon

    pygame.init()


    WIDTH, HEIGHT = 800, 600
    FPS = 60

    # Set up the display surface
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Real-Time Object Positions")

    # Clock to control the frame rate
    clock = pygame.time.Clock()


    center_lat = lat
    center_lon = long


    game_objects = []

    for i in range(n):

        game_object = GameObject(i, func)
        game_objects.append(game_object)
    
    running = True

    while running:

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        screen.fill((0, 0, 0))  

        for game_object in game_objects:

            game_object.update()
            game_object.draw(screen)

        pygame.display.flip()

        clock.tick(FPS)

    pygame.quit()