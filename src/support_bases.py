from spade.agent import Agent
from spade.behaviour import FSMBehaviour, State, CyclicBehaviour
from spade.message import Message
from utils import haversine_distance
import json

CHECKING = "CHECKING"

class StateBehaviour(FSMBehaviour):
    async def on_start(self):
        print(f"FSM starting at initial state {self.current_state}")

    async def on_end(self):
        print(f"FSM finished at state {self.current_state}")
        await self.agent.stop()
        
class Checking(State):
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
                self.set_next_state(WAITING_MEETING)
        else:
                self.drones_close = []
                self.set_next_state(CHECKING) 
                
class WaitingMeeting(State):                          
    async def run(self):
        
        for drone in self.drones_close:
            if (drone.position[0] == self.position[0] and drone.position[1] == self.position[1] and drone.meeting):
                self.drones_close.append(drone)         

class SupportBase(Agent):
    
    def __init__(self, jid, password, position, drones = set()):
        super().__init__(jid, password)
        self.position = position
        self.drones = drones
        self.drones_close = []
        
        
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
                    self.set_next_state(WAITING_MEETING)
            else:
                self.drones_close = []
                self.set_next_state(CHECKING)        
                
                
    