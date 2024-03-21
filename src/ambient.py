import datetime
import getpass

import spade
from spade.agent import Agent
from spade.behaviour import PeriodicBehaviour
from spade.message import Message
import random

class Ambient(Agent):

    def __init__(self, jid, password, drones = set()):
        super().__init__(jid, password)
        self.drones    = drones        
        self.incidents = ["Incident1", "Incident2", "Incident3"]

    class InformBehav(PeriodicBehaviour):

        
        async def run(self):

            print(f"Ambient Warning Incoming at {datetime.datetime.now()}: {self.counter}")

            for drone in self.agent.drones:
                msg          = Message(to=str(drone))
                msg.body     = "INCIDENT"
                indx         = random.randint(0, len(self.agent.incidents)-1)
                msg.metadata = {"type": self.agent.incidents[indx]}
                await self.send(msg)
                print(f"Incident sent to {drone}")

        async def on_end(self):

            await self.agent.stop()

        async def on_start(self):
            self.counter = 0

    async def setup(self):
        print(f"Ambient started at {datetime.datetime.now()}")
        start_date = datetime.datetime.now()
        b = self.InformBehav(period=6, start_at=start_date)
        self.add_behaviour(b)