import json
import heapq
import time

from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message


class Coordinator(Agent):
    def __init__(self, jid, password):
        super().__init__(jid, password)

        self.position = (0, 0)
        self.drones = set()
        self.orders = heapq.heapify([])

    def add_drone(self, drone_jid):
        self.drones.add(drone_jid)

    async def assign_order(self, drone_jid):
        return

    def receive_batch(self, body):
        body_json = json.loads(body)
        for order in body_json.get("orders"):
            heapq.heappush(self.orders, order)

    class AssignOrdersBehav(CyclicBehaviour):
        async def on_start(self):
            print(f"Center starts working")

        async def on_end(self):
            print(f"Center finished working")
            await self.agent.stop()

        async def run(self):

            for drone in self.agent.drones:
                await self.agent.assign_order(drone)

    async def setup(self):
        print(f"Center starting at {self.position}")
        self.add_behaviour(self.AssignOrdersBehav())
