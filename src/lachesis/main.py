import os
import secrets
from pathlib import Path
from typing import Dict

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import gradio as gr
from dotenv import load_dotenv

from lachesis.node.calculate_ranks import calculate_relative_placement, load_df_scores_from_csv
from lachesis.node.project_logging import fastapi_logging

# 1) Load credentials
load_dotenv()
fastapi_logging()
USERNAME = os.environ["FRONTEND_USERNAME"]
PASSWORD = os.environ["FRONTEND_PASSWORD"]

# 2) Define Gradio interface
def run_app(file_obj):
    df = load_df_scores_from_csv(Path(file_obj.name))
    return calculate_relative_placement(df)

with gr.Blocks(theme=gr.themes.Soft()) as demo:
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

def basic_auth(creds: HTTPBasicCredentials = Depends(security)):
    user_ok = secrets.compare_digest(creds.username, USERNAME)
    pass_ok = secrets.compare_digest(creds.password, PASSWORD)
    if not (user_ok and pass_ok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )

# 4) Create your main FastAPI app and mount that protected sub-app
app = FastAPI()

# Add a health check
@app.get("/health-check")
async def health_check() -> Dict[str, str]:
    return {"message": "The application is running"}

# path and root_path params must both be the same
# They also cannot be gradio-demo because it conflicts with internal paths
app = gr.mount_gradio_app(app, demo, "/jnj-explainer", auth=(USERNAME, PASSWORD), pwa=True, root_path="/jnj-explainer")
