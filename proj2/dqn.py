import gym
import torch
from stable_baselines3 import DQN
import os

TIMESTEPS = 100000
EPISODES = 10
env_name   = "Taxi-v3"
models_dir = "models/" + env_name
logdir     = "logs/" + env_name

if not os.path.exists(models_dir):
    os.makedirs(models_dir)

if not os.path.exists(logdir):
    os.makedirs(logdir)

combs = [
    {"lr": 0.0007, "gamma": 0.99},
    {"lr": 0.0007, "gamma": 0.5},
    {"lr": 0.0007, "gamma": 0.1},
    {"lr": 0.00007, "gamma": 0.99},
    {"lr": 0.007, "gamma": 0.5},
]

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

env_name = "Taxi-v3"
env = gym.make(env_name)

for comb in combs:
    lr = comb["lr"]
    g = comb["gamma"]
    env.reset()
    model = DQN(
        "MlpPolicy",
        env,
        verbose=1,
        tensorboard_log=logdir,
        learning_rate=lr,
        gamma=g,
        device=device,
    )
    for i in range(EPISODES):
        model.learn(
            total_timesteps=TIMESTEPS,
            reset_num_timesteps=False,
            tb_log_name=f"DQN_{lr}_{g}",
        )
        model.save(f"{models_dir}/DQN_{lr}_{g}_{TIMESTEPS*i}")
