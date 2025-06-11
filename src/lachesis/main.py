import os
from pathlib import Path
import gradio as gr
from lachesis.node.calculate_ranks import calculate_relative_placement, load_df_scores_from_csv


USERNAME = os.environ["USERNAME"]
PASSWORD = os.environ["PASSWORD"]

def run_app(file_obj):
    # file_obj is a dict-like with 'name' and 'data'
    df_scores = load_df_scores_from_csv(Path(file_obj.name))
    placements, logs = calculate_relative_placement(df_scores)
    return placements, logs

iface = gr.Interface(
    fn=run_app,
    inputs=gr.File(label="Upload CSV with J1–J5 columns"),
    outputs=[
        gr.Dataframe(label="Final Placements"),
        gr.Textbox(label="Detailed Logs", lines=20)
    ],
    title="Ballroom Dance Placement Calculator",
    description="Upload your CSV of judge placings; see final placements and detailed logs of each step."
)

if __name__ == "__main__":
    from dotenv import load_dotenv

    from lachesis.node.project_logging import default_logging

    load_dotenv()
    default_logging()

    iface.launch(server_name="0.0.0.0", auth=(USERNAME, PASSWORD))
