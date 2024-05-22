import gym
import torch
import numpy as np
from stable_baselines3 import DQN
from stable_baselines3 import PPO


import os

MAPS = ["GFFF", "FHFH", "FFFF", "HFFS"]

env = gym.make('FrozenLake-v1', render_mode = "human")

model = PPO.load("models/PPO_0.0007_0.99_900000")


rewards_sum = 0
steps = 0



done = False



for i in range(10000):
    done = False    
    obs, _ = env.reset()
    while not done:
        action, states = model.predict(obs, deterministic=True)
        if isinstance(action, np.ndarray):
            action = action.item()
        obs, reward, terminated, truncated, info  = env.step(action)
        print(f"Action: {action}, Reward: {reward}")
        done = terminated or truncated
        env.render()
        steps += 1
        rewards_sum += reward

print(f"Average rewards: {rewards_sum / steps}")

    