import numpy as np
import os
import gymnasium as gym
from gymnasium import spaces
from stable_baselines3 import PPO
import onnxruntime as ort

ONNX_MODEL_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "rl_placement_model.onnx"
)

class PCBPlacementEnv(gym.Env):
    def __init__(self, num_components=10):
        super().__init__()
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
        self.positions = np.zeros((self.num_components, 2))
        self.current = 0
        return self.positions.flatten().astype(np.float32), {}

    def step(self, action):
        self.positions[self.current] = action
        self.current += 1
        done = self.current >= self.num_components
        reward = 1.0
        return self.positions.flatten().astype(np.float32), reward, done, False, {}


def train_and_export_onnx(num_components=10, timesteps=500):
    """
    Train RL model and export to ONNX format
    """
    try:
        print("Training RL model...")
        env = PCBPlacementEnv(num_components=num_components)
        model = PPO("MlpPolicy", env, verbose=0)
        model.learn(total_timesteps=timesteps)
        print("Training complete!")

        # Save as regular model first
        model_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "rl_placement_model"
        )
        model.save(model_path)
        print(f"Model saved to {model_path}")

        # Export to ONNX
        try:
            from stable_baselines3.common.policies import ActorCriticPolicy
            import torch

            # Get the policy
            policy = model.policy
            policy.eval()

            # Create dummy input
            dummy_obs = torch.zeros(1, num_components * 2)

            # Export to ONNX
            torch.onnx.export(
                policy,
                dummy_obs,
                ONNX_MODEL_PATH,
                opset_version=11,
                input_names=["obs"],
                output_names=["action"],
                dynamic_axes={
                    "obs": {0: "batch_size"},
                    "action": {0: "batch_size"}
                }
            )
            print(f"ONNX model exported to {ONNX_MODEL_PATH}")
            return True

        except Exception as e:
            print(f"ONNX export failed: {str(e)}")
            return False

    except Exception as e:
        print(f"Training failed: {str(e)}")
        return False


def load_onnx_and_place(num_components=10):
    """
    Load ONNX model and get placements instantly!
    """
    try:
        # Check if ONNX model exists
        if not os.path.exists(ONNX_MODEL_PATH):
            print("ONNX model not found! Training first...")
            success = train_and_export_onnx(num_components=num_components)
            if not success:
                return use_fallback_placement(num_components)

        # Load ONNX model
        print("Loading ONNX model...")
        session = ort.InferenceSession(ONNX_MODEL_PATH)
        print("ONNX model loaded!")

        # Get placements
        placements = []
        obs = np.zeros((1, num_components * 2), dtype=np.float32)

        for i in range(num_components):
            outputs = session.run(None, {"obs": obs})
            action = outputs[0][0][:2]
            action = np.clip(action, 0, 1)
            placements.append(action.tolist())

            # Update observation
            if i < num_components:
                obs[0, i*2] = action[0]
                obs[0, i*2+1] = action[1]

        return placements

    except Exception as e:
        print(f"ONNX inference failed: {str(e)}")
        return use_fallback_placement(num_components)


def use_fallback_placement(num_components=10):
    """
    Fallback — use regular RL if ONNX fails
    """
    print("Using fallback RL placement...")
    model_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "rl_placement_model.zip"
    )

    env = PCBPlacementEnv(num_components=num_components)

    if os.path.exists(model_path):
        model = PPO.load(model_path)
    else:
        model = PPO("MlpPolicy", env, verbose=0)
        model.learn(total_timesteps=500)

    obs, _ = env.reset()
    placements = []
    for _ in range(num_components):
        action, _ = model.predict(obs)
        obs, _, done, _, _ = env.step(action)
        placements.append(action.tolist())
        if done:
            break

    return placements


def place_components_with_onnx():
    """
    Main function — place components using ONNX model
    """
    try:
        import pcbnew

        board = pcbnew.GetBoard()
        footprints = list(board.GetFootprints())

        if not footprints:
            return "No components found on board!"

        num_components = len(footprints)
        print(f"Found {num_components} components!")

        # Board dimensions
        board_x = 10.0
        board_y = 10.0
        board_width = 100.0
        board_height = 100.0

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

        # Get placements using ONNX
        placements = load_onnx_and_place(num_components=num_components)

        # Place components
        for i, footprint in enumerate(footprints):
            if i < len(placements):
                x_ratio, y_ratio = placements[i]
                new_x = board_x + (x_ratio * board_width)
                new_y = board_y + (y_ratio * board_height)
                footprint.SetX(pcbnew.FromMM(new_x))
                footprint.SetY(pcbnew.FromMM(new_y))

        pcbnew.Refresh()
        return f"✅ ONNX Placement complete! Placed {num_components} components instantly!"

    except Exception as e:
        return f"Error: {str(e)}"
    