import json
from collections import deque
import datetime

from spade.agent import Agent
from spade.behaviour import PeriodicBehaviour
from spade.message import Message


class Coordinator(Agent):
    def __init__(self, jid, password):
        super().__init__(jid, password)

        self.position = (0, 0)
        self.drones = set()
        self.orders = deque()

    def add_drone(self, drone_jid):
        self.drones.add(drone_jid)

    def receive_batch(self, body):
        body_json = json.loads(body)
        for order in body_json.get("orders"):
            self.orders.append(order)

    class AssignOrdersBehav(PeriodicBehaviour):
        async def on_start(self):
            print(f"Center starts working")

        async def on_end(self):
            print(f"Center finished working")
            await self.agent.stop()

        async def run(self):

            for drone in self.agent.drones:
                msg = Message(to=str(drone))
                msg.body = json.dumps({"orders": [x for x in self.agent.orders]})
                msg.set_metadata("performative", "cfp")
                await self.send(msg)

    async def setup(self):
        print(f"Center starting at {self.position}")
        self.add_behaviour(self.AssignOrdersBehav(period=10, start_at=datetime.datetime.now()))
        