from typing import Any, Dict
import base64
import io

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from Processes import calculate_process, GAS_PROPERTIES


class ProcessRequest(BaseModel):
    process_type: str
    substance: str
    input_data: Dict[str, float]
    mass: float = 1.0


app = FastAPI(title="Thermo Processes API")

# Enable CORS for development. Restrict allow_origins in production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static frontend files from ./static at /static
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def root() -> FileResponse:
    """Serve the SPA index page."""
    return FileResponse("static/index.html")


def _plot_to_base64(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    data = base64.b64encode(buf.read()).decode("ascii")
    return f"data:image/png;base64,{data}"


@app.post("/calculate")
def calculate(req: ProcessRequest) -> Any:
    try:
        result = calculate_process(req.process_type, req.substance, req.input_data, mass=req.mass)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    # Create PV plot
    pv = result.get("pvData", [])
    fig1 = plt.figure()
    if pv:
        V = [p["V"] for p in pv]
        P = [p["P"] for p in pv]
        plt.plot(V, P, marker=".")
        plt.xlabel("V (m^3)")
        plt.ylabel("P (kPa)")
        plt.title("P-V diagram")
    pv_img = _plot_to_base64(fig1)

    # Create T-S plot
    ts = result.get("tsData", [])
    fig2 = plt.figure()
    if ts:
        T = [p["T"] for p in ts]
        S = [p["S"] for p in ts]
        plt.plot(S, T, marker=".")
        plt.xlabel("S (kJ/K)")
        plt.ylabel("T (K)")
        plt.title("T-S diagram")
    ts_img = _plot_to_base64(fig2)

    return {"result": result, "pv_plot": pv_img, "ts_plot": ts_img}


@app.get("/substances")
def list_substances() -> Any:
    """Return available substances (key and name) for frontend selects."""
    return [{"key": k, "name": v.get("name", k)} for k, v in GAS_PROPERTIES.items()]


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api:app", host="127.0.0.1", port=8000, log_level="info")
