import os
import secrets
from pathlib import Path
from typing import Dict

from fastapi import FastAPI, Depends, HTTPException, status, APIRouter
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import gradio as gr
from dotenv import load_dotenv

from lachesis.node.calculate_ranks import calculate_relative_placement, load_df_scores_from_csv
from lachesis.node.project_logging import default_logging

# 1) Load credentials
load_dotenv()
USERNAME = os.environ["FRONTEND_USERNAME"]
PASSWORD = os.environ["FRONTEND_PASSWORD"]

# 2) Define Gradio interface
def run_app(file_obj):
    df = load_df_scores_from_csv(Path(file_obj.name))
    return calculate_relative_placement(df)

iface = gr.Interface(
    fn=run_app,
    inputs=gr.File(label="Upload CSV with J1–J5 columns"),
    outputs=[gr.Dataframe(label="Final Placements"), gr.Textbox(label="Detailed Logs", lines=20)],
    title="Ballroom Dance Placement Calculator",
    description="Upload your CSV of judge placings; see final placements and detailed logs."
)

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

app = gr.mount_gradio_app(app, iface, "/gradio-demo", auth=(USERNAME, PASSWORD))

# 5) Run with Uvicorn in __main__
if __name__ == "__main__":
    default_logging()

    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)
