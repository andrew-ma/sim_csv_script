import os
from typing import Union, IO
import pandas as pd


class NoSpaceStringConverter(dict):
    def __contains__(self, item):
        return True

    def __getitem__(self, item):
        if item == "FieldValue":
            # for FieldValue, convert to lowercase as well
            return lambda val: str(val).lower().replace(" ", "")

        # Return function that converts value to a string, and then removes all the spaces
        return lambda val: str(val).replace(" ", "")

    def get(self, default=None):
        return str


def get_dataframe_from_csv(filename_or_buffer: Union[str, IO]):
    # When reading in csv file into Pandas Dataframe, strip all the spaces, and get back a string
    if isinstance(filename_or_buffer, str):
        if not os.path.exists(filename_or_buffer):
            raise Exception(f"CSV file '{filename_or_buffer}' does not exist")

    df = pd.read_csv(filename_or_buffer, converters=NoSpaceStringConverter())

    # Drop csv rows that have FieldName starting with '#'
    df = df[~df["FieldName"].str.startswith("#")]

    return df
