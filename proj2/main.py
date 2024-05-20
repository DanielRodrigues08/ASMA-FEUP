import gym
import torch
from stable_baselines3 import A2C, PPO, DQN
import os

TIMESTEPS = 10000
EPISODES = 30

models_dir = "models"
logdir = "logs"

if not os.path.exists(models_dir):
    os.makedirs(models_dir)

if not os.path.exists(logdir):
    os.makedirs(logdir)

learning_rate = [0.007, 0.0007, 0.00007]
gamma = [0.99, 0.5, 0.1]
models = ['A2C', 'PPO', 'DQN']
device = device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

env = gym.make('FrozenLake-v1')
env.reset()

for model in models:
    for lr in learning_rate:
        for g in gamma:
            if model == 'A2C':
                model = A2C('MlpPolicy', env, verbose=1, tensorboard_log=logdir, learning_rate=lr, gamma=g, device=device)
            elif model == 'PPO':
                model = PPO('MlpPolicy', env, verbose=1, tensorboard_log=logdir, learning_rate=lr, gamma=g, device=device)
            elif model == 'DQN':
                model = DQN('MlpPolicy', env, verbose=1, tensorboard_log=logdir, learning_rate=lr, gamma=g, device=device)
            for i in range(30):
                model.learn(total_timesteps=TIMESTEPS, reset_num_timesteps=False, tb_log_name=f"{model}_{lr}_{g}")
                model.save(f"{models_dir}/{model}_{lr}_{g}_{TIMESTEPS*i}")
