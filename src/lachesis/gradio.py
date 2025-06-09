import gradio as gr
import pandas as pd
from lachesis.calculate_ranks import calculate_relative_placement

def process_csv(uploaded_file):
    """
    Read the uploaded CSV into a DataFrame and calculate relative placement.

    Parameters:
    uploaded_file: A file-like object or file path for the uploaded CSV.

    Returns:
    A string representation of the dictionary returned by calculate_relative_placement.
    """
    # Determine path or file-like
    try:
        # If Gradio provides a file-like object
        df = pd.read_csv(uploaded_file.name)
    except AttributeError:
        # If Gradio provides a path string
        df = pd.read_csv(uploaded_file)

    # Call the imported function
    result_df = calculate_relative_placement(df)

    # Return the dataframe as formatted text
    return str(result_df)

# Create the Gradio interface
def main():
    iface = gr.Interface(
        fn=process_csv,
        inputs=gr.File(label="Upload CSV File", file_types=[".csv"]),
        outputs=gr.Textbox(label="Result Dictionary"),
        title="Relative Placement Calculator",
        description="Upload a CSV file to compute relative placements using calculate_relative_placement."
    )
    iface.launch()

if __name__ == "__main__":
    main()
