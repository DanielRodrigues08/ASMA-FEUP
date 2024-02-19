import asyncio
import spade
from spade import wait_until_finished
from spade.agent import Agent
from spade.message import Message
from spade.behaviour import CyclicBehaviour

class DummyAgent(Agent):
    class MyBehav(CyclicBehaviour):
        async def on_start(self):
            print("Starting behaviour . . .")
            self.counter = 0

        async def on_message(self, msg):
        # Handle incoming message
            print("Message received: {}".format(msg.body))
            await self.send(msg.sender, "Hi! I received your message.")
            
        async def run(self):
            print("Counter: {}".format(self.counter))
            self.counter += 1
            print("InformBehav running")
            msg = Message(to=str(self.agent.jid))  # Instantiate the message
            msg.set_metadata(
                "performative", "inform"
            )  # Set the "inform" FIPA performative
            msg.body = "Hello World {}".format(
                self.agent.jid
            )  # Set the message content

            await self.send(msg)
            print("Message sent!")
            await asyncio.sleep(1)

    async def setup(self):
        print("Agent starting . . .")
        b = self.MyBehav()
        self.add_behaviour(b)

async def main():
    dummy = DummyAgent("dummyagent@localhost", "password")
    await dummy.start()
    print("DummyAgent started. Check its console to see the output.")

    print("Wait until user interrupts with ctrl+C")
    await wait_until_finished(dummy)

if __name__ == "__main__":
    spade.run(main())