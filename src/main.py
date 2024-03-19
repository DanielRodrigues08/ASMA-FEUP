import asyncio
import spade
import os
from drone import DroneAgent
from coordinator import Coordinator
from ambient import Ambient
from center import Center
from utils import csv_centers_to_system, csv_orders_to_system, csv_drones_to_system

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

    print(center_data)
    print(orders_data)
    print(drones_data)

    # NOT DEALED YET
    coordinator = Coordinator("coordinator@localhost", "pass", center_data[0][-2:]
    )
    center1 = Center("center1@localhost", "pass",  orders_data, set(coordinator.jid))
    first_drone = DroneAgent(
        "drone1@localhost", "drone1", "pos", 100, 100, 100, 100, coordinator.jid
    )
    second_drone = DroneAgent(
        "drone2@localhost", "drone2", "pos", 100, 100, 100, 100, coordinator.jid
    )
    ambient = Ambient(
        "ambient@localhost", "pass", set((first_drone.jid, second_drone.jid))
    )
    print(center.orders)
    await center.start()
    await ambient.start()
    await supplier.start()

    print("Center started")
    print("Ambient started")
    print("Supplier started")

    center.add_drone(first_drone.jid)
    center.add_drone(second_drone.jid)

    await first_drone.start()
    await second_drone.start()

    print("Drones started")


if __name__ == "__main__":
    spade.run(main())
