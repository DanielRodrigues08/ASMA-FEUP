from spade.agent import Agent
from spade.behaviour import FSMBehaviour, State, CyclicBehaviour
from spade.message import Message
from utils import haversine_distance, rearrange_orders_base
import json

WAITING_1_MSG = "WAITING_1_MSG"
WAITING_2_MSG = "WAITING_2_MSG"
WAITING_MEETING = "WAITING_MEETING"
REARRANGEMENT = "REARRANGEMENT"

class SupportBase(Agent):
    
    def __init__(self, jid, password, position):
        super().__init__(jid, password)
        self.position = position
        self.drones_close = []
        
class StateBehaviour(FSMBehaviour):
    async def on_start(self):
        print(f"FSM starting at initial state {self.current_state}")

    async def on_end(self):
        print(f"FSM finished at state {self.current_state}")
        await self.agent.stop()
        
class Waiting_1_msg(State):
    async def run(self):
        self.drone_close = []
        msg = await self.receive(timeout=5)
        
        if msg is None:
            self.set_next_state(WAITING_1_MSG)
            return
        
        payload = json.loads(msg.body)
        
        match payload["type"]:
            case "PRESENCE":
                print(f"Base received 1 message")
                self.drones_close.append(msg.sender)
                self.set_next_state(WAITING_2_MSG)
                return 
        
        self.set_next_state(WAITING_1_MSG)
        return    
    
class Waiting_2_msg(State):
    async def run(self):
        msg = await self.receive(timeout=5) #timeout de espera por 2 msg
        
        if msg is None:
            self.set_next_state(WAITING_1_MSG)
            return
        
        payload = json.loads(msg.body)
        
        match payload["type"]:
            case "PRESENCE":
                print(f"Base received 2 message")
                if msg.sender not in self.drones_close:
                    self.drones_close.append(msg.sender)
                    self.set_next_state(WAITING_MEETING) #provisorio, objetivo e o drone so enviar msg 1 vez
                else:
                    self.set_next_state(WAITING_1_MSG)    
                return 
        
        self.set_next_state(WAITING_1_MSG)
        return
    
class Waiting_Meeting(State):
    async def run(self):   
        for drone in self.drones_close:
            
            msg = Message(to=str(drone))
            msg.body = json.dumps({"type": "UPDATE_ORDERS", "position": self.agent.position})
            await self.send(msg)        
        
        msg_1 = await self.receive(timeout=60)
        msg_2 = await self.receive(timeout=60)
        
        payload_1 = json.loads(msg_1.body)
        payload_2 = json.loads(msg_2.body)
        
        if msg_1 is None or msg_2 is None:
            self.set_next_state(WAITING_1_MSG)
            return
        
        if payload_1["type"] == "ARRIVED" and payload_2["type"] == "ARRIVED":
            self.set_next_state(REARRANGEMENT)
            return 
        
class Rearrangement(State):
    async def run(self):
        utility_drone_1, utility_drone_2 = rearrange_orders_base(self.drones_close[0], self.drones_close[0].orders[1:], self.drones_close[1], self.drones_close[1].orders[1:])      
        
        #sacar 1 order de ambos, e garantir q todas as orders tao la           