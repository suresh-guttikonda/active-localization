#!/usr/bin/env python3

import sys
def set_path(path: str):
    try:
        sys.path.index(path)
    except ValueError:
        sys.path.insert(0, path)

# set programatically the path to 'openai_ros' directory (alternately can also set PYTHONPATH)
set_path('/media/suresh/research/awesome-robotics/active-slam/catkin_ws/src/openai-rosbot-env/openai_ros/src')
from openai_ros.task_envs.turtlebot3 import turtlebot3_localize
import gym
import rospy
import argparse
import datetime

import stable_baselines3
import custom_baselines
from stable_baselines3.common.callbacks import CallbackList, CheckpointCallback, EvalCallback
from stable_baselines3.common.env_checker import check_env
from stable_baselines3.common.monitor import Monitor

def train_network(env, file_path: str, agent: str):
    """
    Train the RL agent for localization task and store the policy/agent

    :params env: openai gym (TurtleBot3LocalizeEnv) instance
            str file_path: location to store the trained agent
            agent: stable_baselines3 agent to be used for training
    """
    dt_str = datetime.datetime.now().strftime('%d_%m_%Y_%H_%M')
    env = Monitor(env, filename=None)
    train_steps = 30000

    if agent == 'PPO':
        log_dir = './logs/PPO/'
        model = stable_baselines3.PPO('MlpPolicy', env, verbose=1,
                                    tensorboard_log=log_dir + 'tensorboard/')
    elif agent == 'RAND':
        log_dir = './logs/RAND/'
        model = custom_baselines.RAND(env, verbose=1,
                                    tensorboard_log=log_dir + 'tensorboard/')
    else:
        return

    checkpoint_callback = CheckpointCallback(save_freq=1000,
                                             save_path=log_dir + 'checkpoints/',
                                             name_prefix=dt_str + 'rl_model')
    eval_callback = EvalCallback(env,
                                 best_model_save_path=log_dir + 'best_model',
                                 log_path=log_dir + 'results',
                                 eval_freq=500,
                                 deterministic=True,
                                 render=False)

    # create the callback listeners list
    callback_list = CallbackList([checkpoint_callback, eval_callback])

    model.learn(total_timesteps=train_steps, callback=callback_list,
                tb_log_name=dt_str + '_run')

    model.save(file_path)
    print('training finished')

def eval_network(env, file_path: str, agent: str):
    """
    Evaluate the pretrained RL agent for localization task

    :params env: openai gym (TurtleBot3LocalizeEnv) instance
            str file_path: location to load the pretrained agent
            agent: stable_baselines3 agent to be used for evaluation
    """
    eval_steps = 500

    if agent == 'PPO':
        model = stable_baselines3.PPO.load(file_path)
    elif agent == 'RAND':
        model = custom_baselines.RAND.load(file_path)
    else:
        return

    obs = env.reset()
    for i in range(eval_steps):
        action, _states = model.predict(obs, deterministic=True)
        obs, reward, done, info = env.step(action)
        env.render()
        if done:
          obs = env.reset()

    env.close()
    print('evaluation finished')

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Train/Evaluate localization RL agent')
    parser.add_argument('--file_path', dest='file_path', \
                    required=False, help='full path for location to store/load agent', \
                    default='./rand_turtlebot3_localize')
    parser.add_argument('--train', dest='is_train', required=False, \
                    default=True, help='whether to train the agent')
    parser.add_argument('--agent', dest='agent', required=False, \
                    default='RAND', help='agent to use for train/eval')
    args = parser.parse_args()

    # create a new ros node
    rospy.init_node('turtlebot3_localization')

    # create a new gym turtlebot3 localization environment
    env = gym.make('TurtleBot3Localize-v0')

    # check out environment follows the gym interface
    check_env(env)

    if args.is_train:
        train_network(env, args.file_path, args.agent)
    eval_network(env, args.file_path, args.agent)

    # prevent te code from exiting until an shutdown signal (ctrl+c) is received
    rospy.spin()
