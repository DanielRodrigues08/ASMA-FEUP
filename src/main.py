import asyncio
import spade
import os
from drone import DroneAgent
from ambient import Ambient
from center import Center
from utils import csv_centers_to_system, csv_orders_to_system, csv_drones_to_system, position_drones

CENTERS_DIR = "../data/centers/"
DRONES_DIR = "../data/drones/"


async def main():
    center_data = []
    orders_data = []
    drones_data = []


    for filename in os.listdir(CENTERS_DIR):
        center_data = center_data + [csv_centers_to_system(CENTERS_DIR + filename)]
        orders_data = orders_data + [csv_orders_to_system(CENTERS_DIR + filename)]


    for filename in os.listdir(DRONES_DIR):
        drones_data = csv_drones_to_system(DRONES_DIR + filename)

    drones_data = position_drones(drones_data, center_data)
    drones      = []

    for drone_data in drones_data:

        drones.append(DroneAgent(drone_data['id'] + '@localhost', drone_data['password'], drone_data["position"], drone_data['autonomy'],  drone_data['autonomy'], drone_data['velocity'], drone_data['capacity']))
    
    drones_jids  = set([x.jid for x in drones])
    ambient      = Ambient("ambient@localhost", "ambient", drones_jids)
    center1      = Center(center_data[0][0]+'@localhost', center_data[0][0], (center_data[0][1], center_data[0][2]), orders_data[0], drones_jids)

    await center1.start(auto_register=True)
    await ambient.start(auto_register=True)


    await asyncio.sleep(2)

    for drone in drones:
        await drone.start(auto_register=True)

    
    print("Center started")
    print("Ambient started")
    print("Supplier started")
    print("Drones started")


if __name__ == "__main__":
    spade.run(main())
