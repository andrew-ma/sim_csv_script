import os
import sys
import re
import subprocess
import logging
import argparse

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def get_resource_py_filename(filename):
    # Gets basename, Removes .ui extension, Adds '_rc' suffix, Adds .py extension
    return os.path.splitext(os.path.basename(filename))[0] + "_rc.py"


def get_ui_py_filename(filename):
    # Gets basename, Removes .ui extension, Adds .py extension
    return os.path.splitext(os.path.basename(filename))[0] + ".py"


def convert_ui_file_to_python(ui_file_path, ui_python_file_path):
    # Convert UI file to Python
    ui_to_py_command = [
        "pyuic5",
        ui_file_path,
        "-x",
        "-o",
        ui_python_file_path,
    ]
    return subprocess.run(ui_to_py_command)


def convert_resource_file_to_python(resource_file_path, resource_python_file_path):
    # Convert Resource file to Python
    resource_to_py_command = [
        "pyrcc5",
        resource_file_path,
        "-o",
        resource_python_file_path,
    ]
    return subprocess.run(resource_to_py_command)


def prefix_ui_python_file_resource_imports(ui_python_file_path, package_name):
    # Prefix the Resource file imports in UI_PYTHON_FILE_PATH with the current Python Package
    import_resource_pattern = re.compile(r"(import\s)(.*[_]rc)")

    with open(ui_python_file_path, "r") as file:
        contents = file.read()
        found_matches = import_resource_pattern.findall(contents)
        resource_module_names = [x[1] for x in found_matches]
        for r in resource_module_names:
            if not os.path.exists(r + ".py"):
                # try to generate this resource file
                raise Exception(
                    f"UI python file '{ui_python_file_path}' depends on missing resource file '{r}.py'"
                )

    with open(ui_python_file_path, "w") as file:
        replaced_import_resource_contents = import_resource_pattern.sub(
            fr"\g<1>{package_name}.\g<2>", contents
        )
        file.write(replaced_import_resource_contents)

    return None


def FileArgType(filename):
    """
    Used as argparse type validator

    Checks that file exists
    """
    if not os.path.exists(filename):
        raise argparse.ArgumentTypeError(f"File '{filename}' does not exist")
    return filename


def UIFileArgType(filename):
    """
    Used as argparse type validator

    Checks that file exists, and does basic check for filename ending with ".ui"
    """
    filename = FileArgType(filename)

    if not filename.lower().endswith(".ui"):
        raise argparse.ArgumentTypeError(f"Check that '{filename}' ends with '.ui'")

    return filename


def ResourceFileArgType(filename):
    """
    Used as argparse type validator

    Checks that file exists, and does basic check for filename ending with ".qrc"
    """
    filename = FileArgType(filename)

    if not filename.lower().endswith(".qrc"):
        raise argparse.ArgumentTypeError(f"Check that '{filename}' ends with '.qrc'")

    return filename


def get_args():
    parser = argparse.ArgumentParser(
        # prog="pySim-read",
        description="Tool for reading some parts of a SIM card",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    required_group = parser.add_argument_group("required arguments")

    required_group.add_argument(
        "--package-name",
        required=True,
    )

    required_group.add_argument(
        "--ui-files", nargs="+", default=[], required=True, type=UIFileArgType
    )

    parser.add_argument(
        "--resource-files", nargs="+", default=[], type=ResourceFileArgType
    )

    args = parser.parse_args()

    return args


def main():
    args = get_args()

    # Qt Designer UI file (.ui)
    # UI Python file (.py) to be generated. This file is imported in app.py
    # UI_FILE_PATHS = ["ui_mainwindow.ui"]
    UI_FILE_PATHS = args.ui_files

    # Resource file (.qrc)
    # Resource Python file (.py) to be generated.  This file is imported in UI_PYTHON_FILE_PATH
    # RESOURCE_FILE_PATHS = [os.path.join("resources", "resources.qrc")]
    RESOURCE_FILE_PATHS = args.resource_files

    # PACKAGE_NAME = "sim_csv_gui"
    PACKAGE_NAME = args.package_name
    log.info(f"GUI Package Name: '{PACKAGE_NAME}'")

    for res_file in RESOURCE_FILE_PATHS:
        res_py_file = get_resource_py_filename(res_file)
        log.info(f"Converting Resource: '{res_file}' => '{res_py_file}'")
        convert_resource_file_to_python(res_file, res_py_file)

    for ui_file in UI_FILE_PATHS:
        ui_py_file = get_ui_py_filename(ui_file)
        log.info(f"Converting UI: '{ui_file}' => '{ui_py_file}'")
        convert_ui_file_to_python(ui_file, ui_py_file)

        log.info(f"Adding package prefix to resource imports in '{ui_py_file}'")
        prefix_ui_python_file_resource_imports(ui_py_file, PACKAGE_NAME)

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        log.error(e)
        sys.exit(1)
