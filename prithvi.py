import argparse
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import torch
import yaml
from huggingface_hub import hf_hub_download
from PIL import Image

DEFAULT_CONFIG_PATH = Path("config.yaml")
DEFAULT_IMAGE_PATH = Path("example data") / "images.jpg"
DEFAULT_MODEL_REPO = "ibm-nasa-geospatial/Prithvi-EO-1.0-100M"
DEFAULT_MODEL_FILE = "Prithvi_EO_V1_100M.pt"
DEFAULT_MODEL_CODE = "prithvi_mae.py"
DEFAULT_MODEL_CONFIG = "config.yaml"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a local Prithvi demo on one JPG/PNG image."
    )
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG_PATH),
        help=f"Local app config path. Default: {DEFAULT_CONFIG_PATH}",
    )
    parser.add_argument(
        "--image",
        default=str(DEFAULT_IMAGE_PATH),
        help=f"Path to the input image. Default: {DEFAULT_IMAGE_PATH}",
    )
    parser.add_argument(
        "--repo",
        default=DEFAULT_MODEL_REPO,
        help=f"Hugging Face repo id. Default: {DEFAULT_MODEL_REPO}",
    )
    parser.add_argument(
        "--device",
        choices=("auto", "cpu", "cuda"),
        default="auto",
        help="Torch device selection. Default: auto",
    )
    return parser


def load_local_config(config_path: Path) -> dict:
    if not config_path.exists():
        return {}
    with config_path.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


def resolve_device(device_arg: str) -> torch.device:
    if device_arg == "cuda":
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA was requested, but no CUDA device is available.")
        return torch.device("cuda")
    if device_arg == "cpu":
        return torch.device("cpu")
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def download_model_files(repo_id: str) -> tuple[Path, Path, Path]:
    try:
        code_path = Path(hf_hub_download(repo_id=repo_id, filename=DEFAULT_MODEL_CODE))
        weights_path = Path(hf_hub_download(repo_id=repo_id, filename=DEFAULT_MODEL_FILE))
        model_config_path = Path(
            hf_hub_download(repo_id=repo_id, filename=DEFAULT_MODEL_CONFIG)
        )
    except Exception as exc:
        raise RuntimeError(
            "Failed to download Prithvi model files from Hugging Face. "
            "Check your internet connection and repo access."
        ) from exc
    return code_path, weights_path, model_config_path


def load_remote_module(module_path: Path):
    module_name = "prithvi_mae_runtime"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def load_prithvi_config(model_config_path: Path) -> dict:
    with model_config_path.open("r", encoding="utf-8") as file:
        raw_config = yaml.safe_load(file) or {}
    model_args = raw_config.get("model_args")
    if not model_args:
        raise RuntimeError("Downloaded model config did not contain model_args.")
    return model_args


def resolve_image_size(local_config: dict, model_config: dict) -> int:
    image_size = local_config.get("image_size", {})
    width = int(image_size.get("width", model_config.get("img_size", 224)))
    height = int(image_size.get("height", model_config.get("img_size", 224)))
    if width != height:
        raise ValueError("Current preprocessing expects a square image size.")
    return width


def build_input_tensor(image_path: Path, image_size: int, num_frames: int) -> torch.Tensor:
    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    image = Image.open(image_path).convert("RGB")
    image = image.resize((image_size, image_size))

    image_array = np.asarray(image, dtype=np.float32)
    image_array = np.transpose(image_array, (2, 0, 1))

    # The pretrained model expects 6 bands. For a plain RGB test image we mirror
    # RGB into six channels so the code path stays runnable.
    six_channels = np.concatenate([image_array, image_array], axis=0)

    # The pretrained checkpoint expects temporal input. We repeat the same frame
    # across the configured number of timesteps.
    temporal_stack = np.repeat(six_channels[:, None, :, :], repeats=num_frames, axis=1)

    tensor = torch.from_numpy(temporal_stack).unsqueeze(0).float()
    return tensor


def load_model(repo_id: str, device: torch.device):
    code_path, weights_path, model_config_path = download_model_files(repo_id)
    module = load_remote_module(code_path)
    model_config = load_prithvi_config(model_config_path)

    model = module.PrithviMAE(**model_config)
    state_dict = torch.load(weights_path, map_location=device)

    for key in list(state_dict.keys()):
        if "pos_embed" in key:
            del state_dict[key]

    model.load_state_dict(state_dict, strict=False)
    model.to(device)
    model.eval()
    return model, model_config, weights_path


def run_inference(model, image_tensor: torch.Tensor) -> dict:
    with torch.no_grad():
        _, pred, mask = model(image_tensor, mask_ratio=0.0)

    return {
        "prediction_shape": list(pred.shape),
        "mask_shape": list(mask.shape),
        "prediction_mean": round(float(pred.mean().item()), 6),
        "prediction_std": round(float(pred.std().item()), 6),
    }


def main() -> None:
    args = build_parser().parse_args()

    local_config = load_local_config(Path(args.config))
    device = resolve_device(args.device)

    model, model_config, weights_path = load_model(args.repo, device)
    image_size = resolve_image_size(local_config, model_config)
    num_frames = int(model_config.get("num_frames", 3))

    image_tensor = build_input_tensor(Path(args.image), image_size, num_frames).to(device)
    inference_result = run_inference(model, image_tensor)

    result = {
        "repo": args.repo,
        "weights": str(weights_path),
        "image": args.image,
        "device": str(device),
        "input_shape": list(image_tensor.shape),
        "note": (
            "Your RGB image was duplicated to 6 spectral bands and repeated across "
            f"{num_frames} timesteps so the pretrained Prithvi checkpoint can run."
        ),
        **inference_result,
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
