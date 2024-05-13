import gym
from stable_baselines3 import DQN

def main():
    env = gym.make('FrozenLake-v1', render_mode='human')
    obs, info = env.reset()
    
    model = DQN('MlpPolicy', env, verbose=1)
    model.learn(total_timesteps=2000)
    
    episodes = 5

    for ep in range(episodes):
       obs, info = env.reset()
       done = False
       while not done:
              action, _states = model.predict(obs, deterministic=True)
              obs, rewards, done, info = env.step(action)
              env.render()
              print(rewards)
    #for step in range(200):
     #   action = env.action_space.sample()  # Select an action randomly
       # result = env.step(action)
       # observation, reward, done, extra_bool, info = env.step(action)  # Correctly unpack all returned values
        #print(reward, done)
        #env.render()
          
    env.close()
    
if __name__ == "__main__":
    main()    