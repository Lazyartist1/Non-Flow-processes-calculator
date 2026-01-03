# Thermo Processes API

This is a small FastAPI app that accepts a thermodynamic process request and returns computed final states and energetics, plus P-V and T-S diagrams.

Quick start (from project root):

1. Create a virtual environment and install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate   # on Windows (bash): .venv\\Scripts\\activate
python -m pip install -r requirements.txt
```

2. Run the API:

```bash
python api.py
```

3. Example request (JSON, POST to http://127.0.0.1:8000/calculate):

```json
{
  "process_type": "isothermal",
  "substance": "idealGas",
  "input_data": {"P1": 100.0, "V1": 0.01, "T1": 300.0, "V2": 0.02},
  "mass": 1.0
}
```

The response JSON includes the numerical results and two fields `pv_plot` and `ts_plot` that contain data URLs (PNG) you can open in a browser or embed in an HTML <img> tag.
