import asyncio
import spade
from spade import wait_until_finished
from spade.agent import Agent
from spade.message import Message
from spade.behaviour import CyclicBehaviour
from state_machine_drone import StateBehaviour, Begin, Negotiating, Delivering, ReturningCenter, NoBattery, DroneAgent
from center import Center

async def main():
    center = Center("center@localhost", "pass", "orders", "pos")
    await center.start()
    print("Center started")
    
    drone = DroneAgent("drone@localhost", "pass", "pos", 100, 100, 100, 100, center.jid)
    await drone.start()
    print("Drone started")


if __name__ == "__main__":
    spade.run(main())