import os
from typing import Union, IO
import pandas as pd


def get_dataframe_from_csv(filename_or_buffer: Union[str, IO]):
    # When reading in csv file into Pandas Dataframe, strip all the spaces, and get back a string
    if isinstance(filename_or_buffer, str):
        if not os.path.exists(filename_or_buffer):
            raise Exception(f"CSV file '{filename_or_buffer}' does not exist")

    df = pd.read_csv(filename_or_buffer)

    return df
