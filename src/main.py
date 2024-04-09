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

    #for i in range(len(drones_data)):
     #   drones_data[i][0] = DroneAgent(drones_data[i][0] + '@localhost', drones_data[i][0], "pos", drones_data[i][2], drones_data[i][2], drones_data[i][3], drones_data[i][4])

    drones_data = position_drones(drones_data, center_data)
    
    first_drone  = DroneAgent(drones_data[0][0]+ '@localhost', drones_data[0][0], drones_data[0][4], drones_data[0][2], drones_data[0][2], drones_data[0][3], drones_data[0][1])
    second_drone = DroneAgent(drones_data[1][0]+ '@localhost', drones_data[1][0], drones_data[1][4], drones_data[1][2], drones_data[1][2], drones_data[1][3], drones_data[1][1])
    
    ambient      = Ambient("ambient@localhost", "ambient", set([first_drone.jid, second_drone.jid]))
    center1      = Center(center_data[0][0]+'@localhost', center_data[0][0], (center_data[0][1], center_data[0][2]), orders_data[0],set([first_drone.jid, second_drone.jid]))

    await first_drone.start(auto_register=True)
    await second_drone.start(auto_register=True)

    await asyncio.sleep(5)
    await center1.start(auto_register=True)
    await ambient.start(auto_register=True)

    print("Center started")
    print("Ambient started")
    print("Supplier started")
    print("Drones started")


if __name__ == "__main__":
    spade.run(main())
