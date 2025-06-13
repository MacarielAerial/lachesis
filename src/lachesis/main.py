import base64
import os
import secrets
from pathlib import Path
from typing import Dict, Optional

from fastapi import FastAPI, Request, status, HTTPException
from fastapi.security import HTTPBasic
from starlette.middleware.base import BaseHTTPMiddleware
import gradio as gr
from dotenv import load_dotenv

from lachesis.node.calculate_ranks import calculate_relative_placement, load_df_scores_from_csv
from lachesis.node.project_logging import fastapi_logging

# 1) Load credentials
load_dotenv()
fastapi_logging()
USERNAME = os.environ["FRONTEND_USERNAME"]
PASSWORD = os.environ["FRONTEND_PASSWORD"]
ROOT_PATH = "/jnj-explainer"
os.environ["GRADIO_ROOT_PATH"] = ROOT_PATH

# 2) Define Gradio interface
def run_app(file_obj):
    df = load_df_scores_from_csv(Path(file_obj.name))
    return calculate_relative_placement(df)

with gr.Blocks(theme=gr.themes.Ocean()) as demo:
    # Title and description
    gr.Markdown("# Ballroom Dance Placement Calculator")
    gr.Markdown("Upload your CSV of judge placings; see final placements and detailed logs.")

    # File input and outputs
    with gr.Row():
        file_input = gr.File(label="Upload CSV with J1–J5 columns")
    with gr.Row():
        output_df = gr.Dataframe(label="Final Placements")
    detailed_logs = gr.Textbox(label="Detailed Logs", lines=20)

    # Run button
    run_button = gr.Button("Run")
    run_button.click(fn=run_app, inputs=file_input, outputs=[output_df, detailed_logs])

# 3) Set up FastAPI’s HTTPBasic dependency
security = HTTPBasic()

def gradio_auth_dependency(request: Request) -> Optional[str]:
    # 1) Let Gradio fetch its own bootstrap data without creds
    if request.url.path in {
        f"{ROOT_PATH}/config",
        f"{ROOT_PATH}/gradio_api/info",
    }:
        return "__gradio_internal__"

    # 2) Otherwise require an Authorization header
    auth = request.headers.get("authorization")
    if not auth or not auth.lower().startswith("basic "):
        # trigger a browser login prompt
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Basic"},
        )

    # 3) Decode and verify credentials
    try:
        b64 = auth.split(" ", 1)[1]
        user_pass = base64.b64decode(b64).decode("utf-8")
        user, pwd = user_pass.split(":", 1)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication",
            headers={"WWW-Authenticate": "Basic"},
        )

    if secrets.compare_digest(user, USERNAME) and secrets.compare_digest(pwd, PASSWORD):
        return user

    # 4) Wrong creds → challenge again
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials",
        headers={"WWW-Authenticate": "Basic"},
    )

# 4) Write a middleware to fix a gradio template bug with hard coded "/manifest.json" call
class RewriteRootRequestMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        new_path = request.url.path
        # if a request hits certain endpoints
        if new_path.startswith("/gradio-demo"):
            new_path = new_path.removeprefix("/gradio-demo")
        if new_path in {"/manifest.json", "/pwa_icon/192", "/config", "/theme.css"} or new_path.startswith(("/gradio_api", "/assets", "/static")):
            new_path = f"{ROOT_PATH}{new_path}"

        # rewrite it so downstream it’s as if they called /{ROOT_PATH}/endpoint
        request.scope["path"]     = new_path
        request.scope["raw_path"] = new_path.encode("utf-8")

        return await call_next(request)

# 5) Create your main FastAPI app and mount the middleware
app = FastAPI()
app.add_middleware(RewriteRootRequestMiddleware)

# 6) Add a health check endpoint
# Add a health check
@app.get("/health-check")
async def health_check() -> Dict[str, str]:
    return {"message": "The application is running"}

# 7) Mount the gradio app
# path and root_path params must both be the same
# They also cannot be gradio-demo because it conflicts with internal paths
app = gr.mount_gradio_app(app, demo, ROOT_PATH, auth_dependency=gradio_auth_dependency, pwa=True, root_path=ROOT_PATH, favicon_path="./asset/favicon.ico")
