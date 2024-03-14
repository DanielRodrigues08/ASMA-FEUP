import asyncio
import spade
from drone import  DroneAgent
from center import Center
from ambient import Ambient
from supplier import Supplier
async def main():


    first_drone  = DroneAgent("drone1@localhost", "pass", "pos", 100, 100, 100, 100, center.jid)
    second_drone = DroneAgent("drone2@localhost", "pass", "pos", 100, 100, 100, 100, center.jid)

    center       = Center("center@localhost", "pass", "orders", "pos")
    ambient      = Ambient("ambient@localhost", "pass", set(first_drone.jid, second_drone.jid))
    supplier     = Supplier("supplier@localhost", "pass", set(center.jid))

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