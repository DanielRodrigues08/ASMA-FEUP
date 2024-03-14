import time
import getpass

import spade
from spade.agent import Agent
from spade.behaviour import CyclicBehaviour, PeriodicBehaviour
from spade.message import Message


class Supplier(Agent):

    def __init__(self, jid, password, centers = set()):
        super().__init__(jid, password)
        self.centers = centers        

    class InformBehav(PeriodicBehaviour):

        
        async def run(self):
            print(f"Supplier running at {time.time()}: {self.counter}")

            for center in self.agent.centers:
                msg = Message(to=str(center))
                msg.body = "NEW_ORDER"
                msg.metadata = {"order": "Details"}
                await self.send(msg)
                print(f"Order sent to {center}")

        async def on_end(self):

            await self.agent.stop()

        async def on_start(self):
            self.counter = 0

    async def setup(self):
        print(f"Supplier started at {time.time()}")
        start_at = time.time() + 5
        b = self.InformBehav(period=3, start_at=start_at)
        self.add_behaviour(b)