#!/usr/bin/env python3
import argparse
import os
import sys
import logging
import json
import subprocess
from io import StringIO
import shlex
import pandas as pd
from typing import Optional, Union, List
from pySim.ts_51_011 import EF
from pySim.ts_31_102 import EF_USIM_ADF_map
from pySim.ts_31_103 import EF_ISIM_ADF_map

from pySim.commands import SimCardCommands
from pySim.transport import init_reader, argparse_add_reader_args
from pySim.cards import card_detect, _cards_classes, SimCard, UsimCard, IsimCard
from pySim.utils import h2b
from pySim.utils import sanitize_pin_adm

from sim_csv_script.csv_utils import get_dataframe_from_csv

ALL_FieldName_to_EF = {**EF_ISIM_ADF_map, **EF_USIM_ADF_map, **EF}

FIELDS_THAT_USE_RECORDS = ("SMSP", "PCSCF", "IMPU")

LOG_FORMAT = "[%(levelname)s] %(message)s"

log = logging.getLogger(__name__)

HexStr = str

############################################################################


class UsimAndIsimCard(UsimCard, IsimCard):
    pass


####################  CUSTOM EXCEPTIONS ####################################


class InvalidFieldError(Exception):
    pass


class InvalidDataframeError(Exception):
    pass


class RequiresIsimError(Exception):
    pass


class RequiresUsimError(Exception):
    pass


class InvalidADMPinError(Exception):
    pass


class ReadFieldError(Exception):
    pass


class WriteFieldError(Exception):
    pass


class VerifyFieldError(Exception):
    pass


class FilterCSVError(Exception):
    pass


############################################################################


def is_valid_hex(test_string: str) -> bool:
    """
    Returns True if valid
    Returns False if invalid
    """
    try:
        int(test_string, 16)
        return True
    except ValueError:
        return False


def is_even_number_hex_characters(test_string: str) -> bool:
    """
    Returns True if string length is even
    Returns False if string length is odd
    """
    return not (len(test_string) & 1)


def has_spaces(test_string: str) -> bool:
    """
    Returns True if there are spaces
    Returns False if there are no spaces
    """
    return " " in test_string


def check_that_field_is_valid(field_name, field_value):
    """Validates passed values
    1. FieldName must match keys (case-sensitive) in Pysim's EF, EF_USIM_ADF_map, or EF_ISIM_ADF_map python dictionaries
    2. FieldValues must not have spaces
    3. FieldValues must have even number of hex characters. If odd number of characters and correct, manually add a '0' in front of FieldValue in CSV file
    4. FieldValues must be valid hex

    InvalidFieldError: if doesn't meet checks above
    """
    log.info(f"Checking that field name {field_name} is valid")
    if field_name not in ALL_FieldName_to_EF:
        raise InvalidFieldError(f"Invalid Field Name: {field_name}")

    ############################################################################

    # Checking that there are no spaces
    log.info("Checking that field value does not have any spaces")
    if has_spaces(field_value):
        raise InvalidFieldError(f"Field values can not contain spaces")

    ############################################################################

    # Checking that field value hex strings have even number of characters (since each 2 character represents 1 byte)
    log.info("Checking that field value has even number of hex characters")
    if not is_even_number_hex_characters(field_value):
        raise InvalidFieldError(f"Odd number of hex characters for field: {field_name}")

    ############################################################################

    # Are there any Invalid field values? Checking if they are valid hex
    log.info("Checking that field value is valid hex")
    if not is_valid_hex(field_value):
        raise InvalidFieldError(f"Invalid hex value for field: {field_name}")

    return None


def check_that_fields_are_valid(df: pd.DataFrame):
    """Validates CSV file parsed dataframe
    1. FieldName must match keys (case-sensitive) in Pysim's EF, EF_USIM_ADF_map, or EF_ISIM_ADF_map python dictionaries
    2. There can't be FieldName duplicates
    3. FieldValues must not have spaces
    4. FieldValues must have even number of hex characters. If odd number of characters and correct, manually add a '0' in front of FieldValue in CSV file
    5. FieldValues must be valid hex

    InvalidDataframeError: if doesn't meet checks above
    """
    # Are there any Invalid field names? Checking if they exist in EF, EF_USIM_ADF_map, or EF_ISIM_ADF_map
    log.info("Checking that field names are all valid")
    isValidFieldNameDf = df["FieldName"].apply(lambda x: x in ALL_FieldName_to_EF)
    if (~isValidFieldNameDf).any():
        raise InvalidDataframeError(
            f"Invalid Field Names: {df['FieldName'][~isValidFieldNameDf].to_list()}.  Valid field names are keys in EF, EF_USIM_ADF_map, and EF_ISIM_ADF_map"
        )

    # Are there are duplicate field names?
    if not df["FieldName"].is_unique:
        raise InvalidDataframeError(
            f"Duplicate Field Names: {df['FieldName'][df['FieldName'].duplicated(keep=False)].to_dict()}"
        )

    ############################################################################
    
    # Checking that there are no spaces
    log.info("Checking that field value does not have any spaces")
    has_spaces_df = df["FieldValue"].apply(has_spaces)
    if (has_spaces_df.any()):
        raise InvalidDataframeError(f"Found spaces in fields: {df['FieldName'][has_spaces_df].to_list()}")

    ############################################################################


    # Checking that field value hex strings have even number of characters (since each 2 character represents 1 byte)
    log.info("Checking that field values have even number of hex characters")
    isEvenHexCharactersDf = df["FieldValue"].apply(is_even_number_hex_characters)
    if (~isEvenHexCharactersDf).any():
        raise InvalidDataframeError(
            f"Odd number of hex characters for fields: {df['FieldName'][~isEvenHexCharactersDf].to_list()}"
        )

    ############################################################################

    # Are there any Invalid field values? Checking if they are valid hex
    log.info("Checking that field values are all valid hex")
    isValidHexDf = df["FieldValue"].apply(is_valid_hex)
    if (~isValidHexDf).any():
        # For those FieldValues that are not a valid hex, they might be a format string
        # right now, just raise Exception if there are any field values that are not valid hex
        # Are there any that are false
        raise InvalidDataframeError(
            f"Invalid hex values for fields: {df['FieldName'][~isValidHexDf].to_list()}"
        )
    return None


def run_filter_command_on_csv_bytes(
    csv_bytes: bytes, filter_command: list
) -> pd.DataFrame:
    """
    Run filter command on csv filename, and returns dataframe

    Errors:
        subprocess.run errors

        FilterCSVError
    """

    p = subprocess.run(
        filter_command, stdout=subprocess.PIPE, input=csv_bytes, stderr=subprocess.PIPE
    )

    if p.returncode != 0:
        raise FilterCSVError(p.stderr.decode())
    else:
        filtered_csv = p.stdout.decode()
        try:
            df = get_dataframe_from_csv(StringIO(filtered_csv))
        except Exception:
            raise FilterCSVError("Failed to parse filtered csv")

        return df


def filter_dataframe(df, filter_command):
    """This takes in an existing dataframe, converts it to bytes, and passes it to filter command's STDIN
    It then returns a new dataframe object

    Args:
        df ([type]): [description]
        filter_command ([type]): [description]

    Returns:
        [type]: [description]
    """
    

    # Convert dataframe to bytes, so it can be passed to filter script's STDIN
    df_bytes = df.to_csv(index=False).encode()

    try:
        df = run_filter_command_on_csv_bytes(df_bytes, filter_command)
    except Exception as e:
        raise FilterCSVError(str(e))

    return df


def check_for_added_fields_after_filter(
    previous_field_names: List[str], after_filter_field_names: List[str]
):
    # only can drop fields, not add new fields
    if (len(after_filter_field_names) > len(previous_field_names)) or (
        set(after_filter_field_names) - set(previous_field_names)
    ):
        raise FilterCSVError(
            "Filter must not add new fields, only change values or remove fields."
        )


############################################################################


def check_isim_field(card: SimCard, field_name: str) -> None:
    """
    Checks if field_name is an Isim field
    if so, then ensure that card object inherits from IsimCard

    RequiresIsimError: if fails checks
    """
    if field_name in EF_ISIM_ADF_map:
        # ensure that card is of Isimcard type
        assert isinstance(card, IsimCard), f"[{field_name}]: SimCard is not ISIM"

        try:
            _, sw = card.select_adf_by_aid(adf="isim")
        except Exception as e:
            raise RequiresIsimError(f"[{field_name}]: Select ISIM adf by aid: {e}")

        if sw != "9000":
            raise RequiresIsimError(f"[{field_name}]: Select ISIM adf by aid: {sw}")
        else:
            ef = ALL_FieldName_to_EF[field_name]
            if not card.file_exists(ef):
                raise RequiresIsimError(
                    f"[{field_name}]: ISIM file {ef} does not exist on card"
                )

    return None


def check_usim_field(card: SimCard, field_name: str) -> None:
    """
    Checks if field_name is an Usim field
    if so, then ensure that card object inherits from UsimCard

    RequiresUsimError: if fails checks
    """
    if field_name in EF_USIM_ADF_map:
        # ensure that card is of UsimCard type
        assert isinstance(card, UsimCard), f"[{field_name}]: SimCard is not Usim"

        try:
            _, sw = card.select_adf_by_aid(adf="usim")
        except Exception as e:
            raise RequiresUsimError(f"[{field_name}]: Select USIM adf by aid: {e}")

        if sw != "9000":
            raise RequiresUsimError(f"[{field_name}]: Select USIM adf by aid: {sw}")
        else:
            ef = ALL_FieldName_to_EF[field_name]
            if not card.file_exists(ef):
                raise RequiresUsimError(
                    f"[{field_name}]: USIM file {ef} does not exist on card"
                )
    return None


def verify_full_field_width(card: SimCard, field_name: str, field_value: HexStr):
    """Used in dataframe.apply function

    ValueError: if hexStr argument's length of bytes != SimCard read field width

    Return Values don't really matter, since the main goal is to raise Error
        Return True if can read binary size of field, and the binary size matches the hexStr's length of bytes
        Return pd.NA if we can't read binary size of field
    """
    field_value_num_bytes = len(field_value) // 2

    check_isim_field(card, field_name)
    check_usim_field(card, field_name)

    ef = ALL_FieldName_to_EF[field_name]

    try:
        field_width = card._scc.binary_size(ef)  # in Bytes
    except Exception:
        log.warning(f"[{field_name}]: Failed to read binary size")
        return pd.NA

    if field_width == field_value_num_bytes:
        log.debug(f"[{field_name}]: Field Width = {field_width} bytes")
        return True
    else:
        raise ValueError(
            f"[{field_name}]: Hex Str Num Bytes {field_value_num_bytes} != Field Width {field_width}"
        )
    return None


############################################################################


def check_pin_adm(card: SimCard, pin_adm: Union[str, HexStr]) -> None:
    """
    Enter ADM pin, and it will be treated as hex if it starts with "0x",
    otherwise it will be treated as ASCII

    InvalidADMPinError: if invalid ADM pin
    """
    if pin_adm.startswith("0x"):
        pin_adm = sanitize_pin_adm(None, pin_adm_hex=pin_adm[2:])
    else:
        pin_adm = sanitize_pin_adm(pin_adm)
    key = h2b(pin_adm)
    log.info("Verifying ADM Key")
    (res, sw) = card._scc.verify_chv(0x0A, key)
    if sw != "9000":
        raise InvalidADMPinError(f"Entered invalid ADM pin: {pin_adm}")
    else:
        log.info("Entered valid ADM key")
    return None


def read_field_data(
    card: SimCard, field_name: str, *, record_number: Optional[int] = None
) -> str:
    """
    ReadFieldError: if problems reading record (for fields with records), or data (for normal fields)

    Returns read_value if successful
    """
    ef = ALL_FieldName_to_EF[field_name]

    if field_name in FIELDS_THAT_USE_RECORDS:
        # NOTE: only tested to work on IMPU

        number_of_records = card._scc.record_count(ef)
        read_value = ""

        if record_number is None:
            # Read All Records
            for rec_no in range(1, number_of_records + 1):
                try:
                    (res, sw) = card._scc.read_record(ef, rec_no)
                except Exception as e:
                    raise ReadFieldError(
                        f"[{field_name}]: Failed while reading record {rec_no} of {number_of_records} -- {e}"
                    )

                if sw != "9000":
                    raise ReadFieldError(
                        f"[{field_name}]: Failed while reading record {rec_no} of {number_of_records} (Status {sw})"
                    )

                read_value += res
        else:
            # Read only specific record
            try:
                (res, sw) = card._scc.read_record(ef, record_number)
            except Exception as e:
                raise ReadFieldError(
                    f"[{field_name}]: Failed while reading binary field -- {e}"
                )

            if sw != "9000":
                raise ReadFieldError(
                    f"[{field_name}]: Failed while reading binary field (Status {sw})"
                )

            read_value = res

    else:
        # Default read
        try:
            (read_value, sw) = card._scc.read_binary(ef)
        except Exception as e:
            raise ReadFieldError(
                f"[{field_name}]: Failed while reading binary field -- {e}"
            )

        if sw != "9000":
            raise ReadFieldError(
                f"[{field_name}]: Failed while reading binary field (Status {sw})"
            )

    return read_value


def write_field_data(
    card: SimCard,
    field_name: str,
    value_to_write: HexStr,
    *,
    record_number: Optional[int] = None,
    dry_run: bool = True,
) -> bool:
    """
    AssertionError: if invalid arguments like:
        - record_number provided when value_to_write is full field width
        - value_to_write's number of bytes != full field width when record_number is not provided
        - record_number is more than max number of records for this field

    WriteFieldError: if problems writing record (for fields with records), or data (for normal fields)
    """
    ef = ALL_FieldName_to_EF[field_name]

    if field_name in FIELDS_THAT_USE_RECORDS:
        # NOTE: only tested to work on IMPU

        # TODO: in CSV file have IMPU.{record_number} for record number to read, write, and verify
        #       and only
        #       and find other fields that use Records, instead of the default binary read and write
        #       will have a list of fields that use Records, and for these fields, when reading in the CSV, allow field.record_num syntax to not cause an error
        # Also will have to change Write function that raises VerifyFieldError (because record verification is different)

        # If value_to_write fills entire field, then record_number must be None
        number_of_records = card._scc.record_count(ef)  # 10
        field_width = card._scc.binary_size(ef)  # 750
        record_size = field_width // number_of_records  # 75
        value_to_write_size = len(value_to_write) // 2  # bytes

        if value_to_write_size == field_width:
            assert (
                record_number is None
            ), f"[{field_name}]: Value fills entire field ({field_width} bytes), so record_number must be None."

        if record_number is None:
            assert (
                value_to_write_size == field_width
            ), f"[{field_name}]: If didn't provide a record_number, then value must be field's full width ({field_width} bytes)"
        else:
            assert (
                record_number > 0 and record_number <= number_of_records
            ), f"[{field_name}]: Invalid record number {record_number}. Max record number = {number_of_records}"
            assert (
                value_to_write_size == record_size
            ), f"[{field_name}]: Provided a record number, so value must be each record's width ({record_size} bytes)"

        if record_number is None:
            log.info(
                f"[{field_name}]: Overwriting full field width ({number_of_records} records, each with {record_size} bytes)"
            )
            # Overwrite Full Field Width (all records)
            for i in range(number_of_records):
                rec_no = i + 1
                # Update Each Record One By One
                write_record_hex_str = value_to_write[
                    i * record_size * 2 : (i * record_size + record_size) * 2
                ]
                log.info(
                    f"[{field_name}]: Updating record {rec_no}: '{write_record_hex_str}'"
                )
                if not dry_run:
                    try:
                        card._scc.update_record(
                            ef, rec_no, write_record_hex_str, conserve=True
                        )
                    except Exception as e:
                        raise WriteFieldError(
                            f"[{field_name}]: Failed to update current record {record_number} / {number_of_records} -- {e}"
                        )
        else:
            # Write to Specific Record Number
            log.info(
                f"[{field_name}]: Updating single record {record_number}: '{value_to_write}'"
            )
            if not dry_run:
                try:
                    card._scc.update_record(
                        ef, record_number, value_to_write, conserve=True
                    )
                except Exception as e:
                    raise WriteFieldError(
                        f"[{field_name}]: Failed to update single record {record_number} / {number_of_records} -- {e}"
                    )

    else:
        # Default write
        log.info(f"[{field_name}]: Updating data: '{value_to_write}'")
        if not dry_run:
            try:
                (_, sw) = card._scc.update_binary(ef, value_to_write)
            except Exception as e:
                raise WriteFieldError(f"[{field_name}]: Failed to update binary -- {e}")

            if sw != "9000":
                raise WriteFieldError(
                    f"[{field_name}]: Failed to update binary (Status {sw})"
                )

    log.info(f"[{field_name}]: Finished Writing")
    return True


def read_fieldname_simple(
    card: SimCard,
    field_name: str,
) -> str:
    """This is used in dataframe.apply function to read and return Card's value for field_name"""
    check_isim_field(card, field_name)
    check_usim_field(card, field_name)
    read_value_before_write = read_field_data(card, field_name)

    log.info(f"[{field_name}]: {read_value_before_write}")

    return read_value_before_write


def write_fieldname_simple(
    card: SimCard,
    field_name: str,
    field_value: str,
    *,
    dry_run: bool = True,
    num_chars_to_display=60,
) -> str:
    """This is used in dataframe.apply function to write and return Card's value for field_name"""
    # Convert field value to lowercase since pysim reads and writes lowercase hex values
    field_value = field_value.lower()

    check_isim_field(card, field_name)
    check_usim_field(card, field_name)
    read_value_before_write = read_field_data(card, field_name)

    show_ellipses = "..." if len(read_value_before_write) > num_chars_to_display else ""
    log.info(
        f"[{field_name}]: {'Read Value':<12}: {read_value_before_write[:num_chars_to_display]}{show_ellipses}"
    )
    log.info(
        f"[{field_name}]: {'Write Value':<12}: {field_value[:num_chars_to_display]}{show_ellipses}"
    )

    write_field_data(card, field_name, field_value, dry_run=dry_run)

    ####### VERIFY PORTION #######
    # Verify Changed Successfully by reading new value after write
    read_value_after_write = read_field_data(card, field_name)

    if field_value != read_value_after_write:
        raise VerifyFieldError(
            f"[{field_name}]: Verification Error. FieldValue argument ('{field_value}') != Card's value after writing ('{read_value_after_write}')"
        )
    else:
        log.info(
            f"[{field_name}]: Verified successful write: Before writing ('{read_value_before_write}') => After writing ('{read_value_after_write}')"
        )

    return read_value_after_write


def read_write_to_fieldname(
    card: SimCard,
    field_name: str,
    field_value: str,
    *,
    dry_run=True,
    num_chars_to_display=50,
    report_differences=True,
) -> bool:
    """
    This is used in dataframe.apply function

    Errors:
        errors in isim_field_checks
        errors in usim_field_checks

        errors in read_field_data
        errors in write_field_data

        VerifyFieldError: if verification error
    """
    # Convert field value to lowercase since pysim reads and writes lowercase hex values
    field_value = field_value.lower()

    check_isim_field(card, field_name)
    check_usim_field(card, field_name)

    read_value_before_write = read_field_data(card, field_name)

    show_ellipses = "..." if len(read_value_before_write) > num_chars_to_display else ""
    log.info(
        f"[{field_name}]: {'Read Value':<12}: {read_value_before_write[:num_chars_to_display]}{show_ellipses}"
    )
    log.info(
        f"[{field_name}]: {'Write Value':<12}: {field_value[:num_chars_to_display]}{show_ellipses}"
    )

    if field_value == read_value_before_write:
        # Don't Write if Current value on card == Value to Write, but return True immediately
        log.info(f"[{field_name}]: Skipping Write since unchanged")
        return True
    elif report_differences:
        # Print the index where the differences begin
        diff_indexes = [
            i
            for i in range(len(field_value))
            if read_value_before_write[i] != field_value[i]
        ]
        diff_symbols = list(" " * num_chars_to_display)
        for i in diff_indexes:
            if i >= num_chars_to_display:
                break
            diff_symbols[i] = "^"
        log.info(f"[{field_name}]: {'Differences':<12}: " + "".join(diff_symbols))
        log.info(f"[{field_name}]: Differences indexes: {diff_indexes}")

    ####### WRITE PORTION #######
    if not dry_run:
        write_field_data(card, field_name, field_value, dry_run=dry_run)

        ####### VERIFY PORTION #######
        # Verify Changed Successfully by reading new value after write
        read_value_after_write = read_field_data(card, field_name)

        if field_value != read_value_after_write:
            raise VerifyFieldError(
                f"[{field_name}]: Verification Error. FieldValue argument ('{field_value}') != Card's value after writing ('{read_value_after_write}')"
            )
        else:
            log.info(
                f"[{field_name}]: Verified successful write: Before writing ('{read_value_before_write}') => After writing ('{read_value_after_write}')"
            )

    return True


############################################################################


def setup_logging_basic_config():
    logging.basicConfig(
        level=logging.INFO,
        format=LOG_FORMAT,
        handlers=[logging.StreamHandler()],
    )


def FileArgType(filename):
    """
    Used as argparse type validator

    Checks that file exists
    """
    if not os.path.exists(filename):
        raise argparse.ArgumentTypeError(f"File '{filename}' does not exist")
    return filename


def CSVFileArgType(filename):
    """
    Used as argparse type validator

    Checks that file exists, and does basic check for filename ending with ".csv"
    """
    filename = FileArgType(filename)

    if not filename.lower().endswith(".csv"):
        raise argparse.ArgumentTypeError(f"Check that '{filename}' ends with '.csv'")

    return filename


def JSONFileArgType(filename):
    """
    Used as argparse type validator

    Checks that file exists, and does basic check for filename ending with ".json"
    """
    filename = FileArgType(filename)

    if not filename.lower().endswith(".json"):
        raise argparse.ArgumentTypeError(f"Check that '{filename}' ends with '.json'")

    try:
        json_dict = json.load(open(filename, "r"))
    except Exception:
        raise argparse.ArgumentTypeError(f"Failed to parse JSON file {filename}")

    return json_dict


def get_package_version():
        import pkg_resources
        return pkg_resources.require("sim_csv_script")[0].version

def get_args():
    parser = argparse.ArgumentParser(
        # prog="pySim-read",
        description="Tool for reading some parts of a SIM card",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument("--version", action="version", version=get_package_version())
    parser.add_argument(
        "CSV_FILE",
        help="Read FieldNames and FieldValues from CSV file",
        type=CSVFileArgType,
        nargs="?"
    )
    parser.add_argument(
        "--list-field-names",
        help="Lists all possible field names",
        default=False,
        action="store_true"
    )
    parser.add_argument(
        "--type",
        dest="card_type",
        help="SimCard type (use '--type list' to list possible types)",
        default="auto",
    )
    parser.add_argument(
        "--log-file",
        type=str,
        default="sim.log",
        help="Specify log filename",
    )
    parser.add_argument(
        "--show-diff",
        help="Show symbols that point to difference in Read and Write values",
        default=False,
        action="store_true",
    )
    parser.add_argument(
        "--multiple",
        action="store_true",
        help="If multiple, loop and wait for next card once done. Press Ctrl+C to stop",
    )
    write_group = parser.add_argument_group("write arguments")
    write_group.add_argument(
        "--write",
        dest="write",
        default=False,
        action="store_true",
        help="Turn on Write Mode.",
    )
    write_group.add_argument(
        "--pin-adm",
        dest="pin_adm",
        type=str,
        help="ADM PIN required for write mode. If it starts with '0x' it will be treated as hex. Otherwise it will be treated as ASCII.",
    )
    write_group.add_argument(
        "--pin-adm-json",
        dest="pin_adm_json",
        type=JSONFileArgType,
        help="JSON file with {key IMSI: value ADM PIN}. If value starts with '0x', it will be treated as hex. Otherwise it will be treated as ASCII",
    )
    write_group.add_argument(
        "--skip-write-prompt",
        help="Don't show write prompt for each card to speed up writing",
        default=False,
        action="store_true",
    )
    filter_group = parser.add_argument_group("filter arguments")
    filter_group.add_argument(
        "--filter",
        nargs="+",
        default=[],
        help="Supply a command that receives the CSV file from STDIN, modifies it, and outputs the new CSV file to STDOUT.  Unchanging filter arguments can be supplied immediately after the command.  If different arguments are needed per card, then set --ask-filter-args and it will ask for new arguments that will be appended to this --filter command.",
    )
    filter_group.add_argument(
        "--ask-filter-args",
        action="store_true",
        help="Only works when --filter is set.  For each card, prompt user for arguments that will be appended to the --filter command.",
    )
    parser = argparse_add_reader_args(parser)

    # use PC/SC reader as default
    parser.set_defaults(pcsc_dev=0)

    args = parser.parse_args()


    if args.card_type == "list":
        print(repr([card_cls.name for card_cls in _cards_classes]))
        parser.exit()

    if args.list_field_names:
        print(repr(list(ALL_FieldName_to_EF.keys())))
        parser.exit()

    if args.CSV_FILE is None:
        parser.error("the following arguments are required: CSV_FILE")

    if args.write:
        if args.pin_adm is None and args.pin_adm_json is None:
            parser.error("--write requires at least one: --pin-adm or --pin-adm-json")
        elif args.pin_adm is not None and args.pin_adm_json is not None:
            parser.error(
                "--pin-adm and pin-adm-json can't be selected at the same time"
            )

    if args.ask_filter_args:
        if not args.filter:
            parser.error("--ask-filter-args requires --filter")

    return args


############################################################################
# GUI requires Inputs:

# Data CSV file: str

# ADM pin: str or ADM pin file : str

# Filter command : str

# Easy access to Read function and Write function when Button pressed


# When enabled is check, it refilters the dataframe using the filter command
# If there are any errors, it will show a
############################################################################


def initialize_card_reader_and_commands(reader_args):
    # Init card reader driver
    log.info("Init card reader driver")
    sl = init_reader(reader_args)
    if sl is None:
        raise Exception(
            "Failed to init card reader driver. Try unplugging and replugging in card reader."
        )

    # Create command layer
    log.info("Setting up SimCardCommands")
    scc = SimCardCommands(transport=sl)
    return (sl, scc)


def set_commands_cla_byte_and_sel_ctrl(scc, sl):
    # Assuming UICC SIM
    scc.cla_byte = "00"
    scc.sel_ctrl = "0004"

    # Testing for Classic SIM or UICC
    log.info("Testing for Classic SIM or UICC")
    (res, sw) = sl.send_apdu(scc.cla_byte + "a4" + scc.sel_ctrl + "02" + "3f00")
    if sw == "6e00":
        log.info("Is a Classic SIM")
        # Just a Classic SIM
        scc.cla_byte = "a0"
        scc.sel_ctrl = "0000"
    else:
        log.info("Is a UICC")


def get_card(card_type, scc):
    if card_type is None:
        card_type = "auto"

    try:
        card = card_detect(card_type, scc)
    except Exception as e:
        log.error(f"({e.__class__.__name__}) {e}")
        card = None

    if card is None:
        default_card = UsimAndIsimCard(scc)
        return default_card
    else:
        return card


def read_card_initial_data(card):
    # Read all AIDs on the UICC
    log.info("Reading card AIDs")
    card.read_aids()

    # EF.ICCID
    (iccid, sw) = card.read_iccid()
    if sw == "9000":
        log.info(f"[ICCID]: {iccid}")
    else:
        log.info(f"[ICCID]: Can't read, response code = {sw}")

    # EF.IMSI
    (imsi, sw) = card.read_imsi()
    if sw == "9000":
        log.info(f"[IMSI]:  {imsi}")
    else:
        log.info(f"[IMSI]: Can't read, response code {sw}")

    return iccid, imsi


def get_filtered_dataframe(csv_filename, filter_command):
    csv_bytes = open(csv_filename, "rb").read()
    # Get Previous Keys
    df = get_dataframe_from_csv(csv_filename)
    previous_field_names = df["FieldName"].to_list()

    df = run_filter_command_on_csv_bytes(csv_bytes, filter_command)
    log.info(df)

    after_filter_field_names = df["FieldName"].to_list()
    check_for_added_fields_after_filter(previous_field_names, after_filter_field_names)
    check_that_fields_are_valid(df)

    return df


def main():
    setup_logging_basic_config()
    args = get_args()

    file_handler = logging.FileHandler(args.log_file)
    formatter = logging.Formatter(LOG_FORMAT)
    file_handler.setFormatter(formatter)
    log.addHandler(file_handler)

    ############################################################################
    if not args.filter:
        # If no filter script, then parse CSV and validate CSV immediately
        try:
            df = get_dataframe_from_csv(args.CSV_FILE)
            check_that_fields_are_valid(df)
        except Exception as e:
            log.error(f"({e.__class__.__name__}) {e}")
            return 1
    ############################################################################

    try:
        sl, scc = initialize_card_reader_and_commands(args)
    except Exception as e:
        log.error(f"({e.__class__.__name__}) {e}")
        return 1

    while True:
        # Wait for SIM card
        log.info("Waiting for new SIM card...")
        sl.wait_for_card(newcardonly=True)

        set_commands_cla_byte_and_sel_ctrl(scc, sl)

        card = get_card(args.card_type, scc)

        _, imsi = read_card_initial_data(card)

        ############################################################################
        # We Can Modify The Field Values Dynamically Using A filter Script

        if args.filter:
            filter_command = args.filter

            if args.ask_filter_args:
                new_filter_args = input(
                    f"Enter filter args (if blank use {repr(args.filter)}): "
                )
                if new_filter_args != "":
                    new_filter_args = shlex.split(new_filter_args)
                    filter_command = args.filter + new_filter_args

            log.info(f"Running Filter: {repr(filter_command)}")

            try:
                df = get_filtered_dataframe(args.CSV_FILE, filter_command)
            except Exception as e:
                log.error(f"({e.__class__.__name__}) {e}")
                return 1
        ############################################################################

        # Checking that FieldValue's length in bytes matches binary size of field (since we want to completely overwrite each field)
        # if we can read the binary size, but it doesn't match FieldValue's length in bytes, then it will raise a ValueError
        # and we alert user to fix the input file
        log.info("Checking that csv field values span full width of field")

        try:
            df.apply(
                lambda row: verify_full_field_width(
                    card, row["FieldName"], row["FieldValue"]
                ),
                axis=1,
            )
        except Exception as e:
            log.error(f"({e.__class__.__name__}) {e}")
            return 1

        ############################################################################

        if args.write:
            if not args.skip_write_prompt:
                ask_write = input(f"Sure you want to write? [y/N] ")
                if ask_write.lower() != "y":
                    log.info("You chose to not write.  Quitting")
                    return 0

            # Need ADM Key if Writing Values to SimCard
            if args.pin_adm is not None:
                pin_adm = args.pin_adm
            elif args.pin_adm_json is not None:
                pin_adm = args.pin_adm_json.get(imsi, None)
                if pin_adm is None:
                    log.error(f"IMSI {imsi} is not found in PIN ADM JSON file")
                    return 1

            try:
                check_pin_adm(card, pin_adm)
            except Exception as e:
                log.error(f"({e.__class__.__name__}) {e}")
                return 1

        #############################################################################

        # For each FieldName, FieldValue pair, write the value
        df.apply(
            lambda row: read_write_to_fieldname(
                card,
                row["FieldName"],
                row["FieldValue"],
                dry_run=not args.write,
                report_differences=args.show_diff,
            ),
            axis=1,
        )

        if args.multiple:
            log.info(
                "Eject the sim card, and plug in another card. Press Ctrl+C to exit.\n"
            )
        else:
            log.info("Done!")
            break

    return 0


def main_safe():
    try:
        sys.exit(main())
    except Exception as e:
        log.exception(e)
        sys.exit(1)


if __name__ == "__main__":
    main_safe()
