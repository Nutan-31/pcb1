import numpy as np
import gymnasium as gym
from gymnasium import spaces
from stable_baselines3 import PPO

class PCBPlacementEnv(gym.Env):
    def __init__(self, board_width=100, board_height=100, num_components=10):
        super().__init__()
        self.board_width = board_width
        self.board_height = board_height
        self.num_components = num_components

        self.action_space = spaces.Box(
            low=0, high=1, shape=(2,), dtype=np.float32
        )
        self.observation_space = spaces.Box(
            low=0, high=1, shape=(num_components * 2,), dtype=np.float32
        )
        self.reset()

    def reset(self, seed=None):
        super().reset(seed=seed)
        self.component_positions = np.zeros((self.num_components, 2))
        self.current_component = 0
        return self._get_observation(), {}

    def step(self, action):
        self.component_positions[self.current_component] = action
        self.current_component += 1
        reward = self._calculate_reward()
        done = self.current_component >= self.num_components
        return self._get_observation(), reward, done, False, {}

    def _get_observation(self):
        return self.component_positions.flatten().astype(np.float32)

    def _calculate_reward(self):
        reward = 0
        for pos in self.component_positions:
            if 0 <= pos[0] <= 1 and 0 <= pos[1] <= 1:
                reward += 1
            else:
                reward -= 5
        for i in range(self.current_component):
            for j in range(i + 1, self.current_component):
                dist = np.linalg.norm(
                    self.component_positions[i] - self.component_positions[j]
                )
                if dist < 0.05:
                    reward -= 10
        return reward


class RLPlacer:
    def __init__(self):
        self.model = None

    def train(self, num_components=10, timesteps=500):
        env = PCBPlacementEnv(num_components=num_components)
        self.model = PPO("MlpPolicy", env, verbose=0)
        self.model.learn(total_timesteps=timesteps)

    def get_placements(self, num_components):
        if self.model is None:
            self.train(num_components=num_components)

        env = PCBPlacementEnv(num_components=num_components)
        obs, _ = env.reset()
        placements = []

        for _ in range(num_components):
            action, _ = self.model.predict(obs)
            obs, _, done, _, _ = env.step(action)
            placements.append(action.tolist())
            if done:
                break
        return placements


def place_components_on_board():
    try:
        import pcbnew

        board = pcbnew.GetBoard()
        footprints = list(board.GetFootprints())

        if not footprints:
            return "No components found on board!"

        num_components = len(footprints)

        # Use fixed board dimensions
        board_width = 100.0
        board_height = 100.0
        board_x = 10.0
        board_y = 10.0

        # Try to get actual board dimensions
        try:
            bbox = board.GetBoardEdgesBoundingBox()
            w = pcbnew.ToMM(bbox.GetWidth())
            h = pcbnew.ToMM(bbox.GetHeight())
            if w > 0 and h > 0:
                board_width = w
                board_height = h
                board_x = pcbnew.ToMM(bbox.GetX())
                board_y = pcbnew.ToMM(bbox.GetY())
        except:
            pass

        # Train RL and get placements
        placer = RLPlacer()
        placer.train(num_components=num_components, timesteps=100)
        placements = placer.get_placements(num_components)

        # Place each component
        for i, footprint in enumerate(footprints):
            if i < len(placements):
                x_ratio, y_ratio = placements[i]
                new_x = board_x + (x_ratio * board_width)
                new_y = board_y + (y_ratio * board_height)
                footprint.SetX(pcbnew.FromMM(new_x))
                footprint.SetY(pcbnew.FromMM(new_y))

        pcbnew.Refresh()
        return f"Successfully placed {num_components} components on PCB!"

    except Exception as e:
        return f"Error placing components: {str(e)}"