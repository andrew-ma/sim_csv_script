#!/usr/bin/env python3
"""
reads CSV file from stdin, changes it, and prints out to stdout

arg1 is a 2 digit number that will change imsi, impi, and impu

Return 0 if success
Return 1 if error
"""

import sys
import logging
from io import StringIO
from sim_csv_script.csv_utils import get_dataframe_from_csv

LOG_FORMAT = "[%(levelname)s] %(message)s"
log = logging.getLogger("filter_script")
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)


def main():
    assert len(sys.argv) > 1, "arg1 is required"
    last_two_digits = sys.argv[1]
    assert len(last_two_digits) == 2, "arg1 must be exactly 2 digits"
    try:
        int(last_two_digits)
    except ValueError:
        raise ValueError("arg1 must be a valid integer")

    csv_str = "".join(sys.stdin.readlines())

    df = get_dataframe_from_csv(StringIO(csv_str))

    imsi = df.loc[df.FieldName == "IMSI", "FieldValue"].to_list()[0]
    # impi = df.loc[df.FieldName == "IMPI", "FieldValue"].to_list()[0]
    # impu = df.loc[df.FieldName == "IMPU", "FieldValue"].to_list()[0]

    imsi = f"{imsi[:-2]}{last_two_digits[::-1]}"
    # impi = f"{impi[:31]}{last_two_digits[0]}{impi[32]}{last_two_digits[1]}{impi[34:]}"
    # impu = f"{impu[:39]}{last_two_digits[0]}{impu[40]}{last_two_digits[1]}{impu[42:]}"

    df.loc[df.FieldName == "IMSI", "FieldValue"] = imsi
    # df.loc[df.FieldName == "IMPI", "FieldValue"] = impi
    # df.loc[df.FieldName == "IMPU", "FieldValue"] = impu

    ret_str = df.to_csv(index=False)
    sys.stdout.write(ret_str)
    sys.stdout.flush()

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        log.error(e)
        sys.exit(1)
