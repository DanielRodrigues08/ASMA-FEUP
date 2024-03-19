import json
import heapq
import time

from spade.agent import Agent
from spade.behaviour import CyclicBehaviour
from spade.message import Message


class Coordinator(Agent):
    def __init__(self, jid, password):
        super().__init__(jid, password)

        self.drones = set()
        self.orders = heapq.heapify()

    def add_drone(self, drone_jid):
        self.drones.add(drone_jid)

    async def assign_order(self, drone_jid):
        order = heapq.heappop(self.orders)
        msg = Message(to=str(drone_jid))
        msg.body = "ORDER"
        msg.metadata = order
        self.to_fulfill.add(order[0])
        # self.send(msg) it is not possible to send msg like this, we need an alternative
        await self.send(msg)

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

            acks = 0

            for drone in self.agent.drones:

                if drone not in self.agent.timeout_drones:

                    msg = Message(to=str(drone))
                    msg.body = "ORDER_READY"
                    acks += 1
                    await self.send(msg)

            available_drones = set()
            while acks:

                msg = await self.receive(timeout=3)
                if msg is None:
                    acks -= 1
                    continue

                match msg.body:

                    case "OK":
                        available_drones.add(msg.sender)
                        acks -= 1

                    case "NO":
                        self.timeout_drone(msg.sender)
                        acks -= 1

                    case "BATCH":
                        self.receive_batch(msg.metadata)
                    case "DELIVERED":
                        self.to_fulfill.remove(msg.metadata)

            self.agent.assign_order(available_drones)

            if self.agent.timer - time.time() > 10:

                self.agent.timer = time.time()
                self.reset_orders()
                self.agent.timeout_drones.clear()

    async def setup(self):
        print(f"Center starting at {self.position}")
        self.add_behaviour(self.AssignOrdersBehav())
