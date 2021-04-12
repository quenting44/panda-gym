from gym import spaces
import numpy as np

from panda_gym.envs.robots import PandaEnv
from panda_gym.envs.tasks import PickAndPlaceEnv
from panda_gym.pybullet import PyBullet


class PandaPickAndPlaceEnv(PandaEnv, PickAndPlaceEnv):
    """Pick and Place task wih Panda robot

    Args:
        render (bool, optional): Activate rendering. Defaults to False.
        reward_type (str, optional): "sparse" or "dense". Defaults to "sparse".
    """

    def __init__(self, render=False, reward_type="sparse"):
        sim = PyBullet(render=render, n_substeps=20)
        PickAndPlaceEnv.__init__(self, sim, reward_type=reward_type)
        PandaEnv.__init__(self, sim, block_gripper=False)
        self.observation_space = spaces.Dict(
            dict(
                observation=spaces.Box(-np.inf, np.inf, shape=(19,)),
                desired_goal=spaces.Box(-np.inf, np.inf, shape=(3,)),
                achieved_goal=spaces.Box(-np.inf, np.inf, shape=(3,)),
            )
        )

    def _get_obs(self):
        # end-effector position and velocity
        ee_position = np.array(self.get_ee_position())
        ee_velocity = np.array(self.get_ee_velocity())

        # fingers opening
        fingers_width = self.get_fingers_width()

        # position, rotation of the object
        object_position = np.array(self.sim.get_base_position("object"))
        object_rotation = np.array(self.sim.get_base_rotation("object"))
        object_velocity = np.array(self.sim.get_base_velocity("object"))
        object_angular_velocity = np.array(self.sim.get_base_angular_velocity("object"))

        observation = np.concatenate(
            [
                ee_position,
                ee_velocity,
                [fingers_width],  # this is a float
                object_position,
                object_rotation,
                object_velocity,
                object_angular_velocity,
            ]
        )

        achieved_goal = np.squeeze(object_position.copy())

        return {
            "observation": observation,
            "achieved_goal": achieved_goal,
            "desired_goal": self.goal.copy(),
        }

    def reset(self):
        with self.sim.no_rendering():
            self.set_joint_neutral()
            self.resample()
        return self._get_obs()

    def step(self, action):
        self._set_action(action)
        self.sim.step()
        obs = self._get_obs()
        done = False
        info = {
            "is_success": self._is_success(obs["achieved_goal"], self.goal),
        }
        reward = self.compute_reward(obs["achieved_goal"], self.goal, info)

        return obs, reward, done, info