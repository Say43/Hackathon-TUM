# Burned Area Classifier

Minimal Prithvi demo for running a local test image through the original checkpoint.

`prithvi.py` is the main program and current CLI entry point.

## Jupyter Notebook

Open `jupyter_demo.ipynb` in your Jupyter environment.

The notebook clones the repo, installs dependencies, and runs the demo with a file path that you set on your server.

## PowerShell quick start

```bash
cd "C:\Festplatte (D)\Dateien\AI\Codex Projects\Hackathon"
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe prithvi.py
```

By default the script uses `config.yaml` and `example data\images.jpg`.
You can still override both paths:

```bash
.\.venv\Scripts\python.exe prithvi.py --config config.yaml --image "example data\images.jpg"
```

## Notes

The first run downloads the model from Hugging Face, so internet access is required once.
Prithvi expects 6-band remote-sensing input in shape `(B, C, T, H, W)`. For your local JPG test image, the script duplicates RGB channels to 6 bands and repeats the same frame across timesteps so the checkpoint can run. This is only a technical fallback and not scientifically correct remote-sensing inference.
