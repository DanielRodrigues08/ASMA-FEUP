from spade.agent import Agent
from spade.behaviour import FSMBehaviour, State, CyclicBehaviour
from spade.message import Message
from utils import haversine_distance
import json

class SupportBase(Agent):
    
    def __init__(self, jid, password, position, drones = set()):
        super().__init__(jid, password)
        self.position = position
        self.drones = drones
        
    class checkBehav(CyclicBehaviour):
        async def on_start(self):
            print("Support Base started")
            self.drones_close = []
            
        async def on_end(self):
            print("Support Base stopped")
            await self.agent.stop()
        
        async def run(self):
            for drone in self.agent.drones:
                if (haversine_distance(self.position[0],self.position[1], drone.position[0], drone.position[1]) < 5):
                    self.drones_close.append(drone)
            
            if len(self.drone_close) > 1 :
                for drone in self.drones_close:
                    msg = Message(to=str(drone))
                    msg.body = json.dumps({'type':'MEETING', 'meeting_point': self.position})
                    msg.set_metadata("performative", "inform")
                    
                    await self.send(msg)
                
                
    