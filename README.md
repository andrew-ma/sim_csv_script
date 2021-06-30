# SIM CSV Script
Python script to read and write SIM cards.
Fields and values are specified in a CSV file, and optionally a filter script can be supplied as a command line argument for dynamically changing the CSV contents for each card.

## Installation
* Requires Python 3 (version 3.7+)
* On Windows, recommended Python installation method is with Miniconda https://docs.conda.io/en/latest/miniconda.html).
* Look at Python Installation sections below.

Python pip Dependencies:
* pysim
    * Right now it uses my fork, because of this commit (https://github.com/andrew-ma/pysim/commit/2f10406c9d3ba42787648fb0060475222531d905), and official repo doesn't accept pull requests on Github
* pandas

To install for use
```
pip install https://github.com/andrew-ma/sim_csv_script/archive/main.zip --upgrade
```


To install for development
```
git clone -b main https://github.com/andrew-ma/sim_csv_script
cd sim_csv_script
pip install -e .
```

To uninstall
```
pip uninstall sim_csv_script -y
pip uninstall -r requirements.txt -y
pip uninstall -r requirements_gui.txt -y
pip uninstall -r requirements_gui_dev.txt -y
```

## __SIM CSV SCRIPT__

## Usage Examples

### Help and Documentation
```
sim_csv_script -h
```

### Example Read Single
```
sim_csv_script {example.csv}
```

### Example Write Single (reading ADM pin from CLI arg)
* Specify ASCII ADM pin without the leading "0x"
```
sim_csv_script {example.csv} --write --pin-adm 0x8888888888888888
```

### Example Write Single (reading hexadecimal ADM pin from JSON file with {"IMSI key" : "ADM pin value"})
* Specify ASCII ADM pins without the leading "0x"
```
sim_csv_script {example.csv} --write --pin-adm-json {IMSI_TO_ADM.json}
```

### Example Read Multiple
```
sim_csv_script {example.csv} --multiple
```

---

### **Filters**
>  On Windows, replace `python3` with `python`
* You can create a filter script (doesn't have to be Python) that reads in a CSV file from STDIN, modifies it, and outputs a new CSV file to STDOUT

* The filter script should be able to function as a standalone program "`python3 filter_script.py unchanging_arg_1} < {example.csv}`"
   * In Windows, running this in Powershell will cause an error because Powershell doesn't have the '<' STDIN redirect operator, so run this in Command Prompt

* Filter script must return 0 on Success.  It should also raise Exceptions if it requires certain arguments.

* Supply a valid command (that can run in the terminal) to --filter, like "`--filter ./filter_script.py`" or "`--filter python3 ./filter_script.py`" on Linux, or "`--filter python .filter_script.py`" on Windows
* Unchanging arguments can be specified immediately after the command.
* If different arguments need to be specified for each card, then we can set --ask-filter-args, which will ask user to type new arguments that will be appended to --filter command. 


### Example Read Multiple with --filter
>  On Windows, replace `python3` with `python`
```
sim_csv_script {example.csv} --multiple --filter {python3 filter_script.py unchanging_arg1}
```

### Example Read Multiple with --filter and --ask-filter-args
```
sim_csv_script {example.csv} --multiple --filter {python3 filter_script.py} --ask-filter-args
```

---
## __SIM CSV GUI__

Launch the GUI
```
sim_csv_gui
```

### __GUI Development__
To install Qt Designer
```
pip install -r requirements_gui_dev.txt
```

To launch Qt Designer to modify the UI
```
pyqt5-tools designer
```

Then, you can import the .ui file in Qt Designer to modify the GUI.

After you modify the Qt Designer .ui file, you can regenerate the python code by running (from the 'sim_csv_gui' folder):
```
# Windows
python generate.py --package-name sim_csv_gui --ui-files UI\ui_mainwindow.ui --resource-files resources\resources.qrc
```

To launch the GUI while in development, run (from the 'sim_csv_gui' folder)
```
python3 ui_mainwindow.py
```

The entry point for the gui is the main function in sim_csv_gui/app.py.

---

## Windows Python Installation
* Miniconda is recommended for installing Python on Windows
   * Latest Python 3 version is recommended, but 3.7+ should work (https://docs.conda.io/en/latest/miniconda.html)
   * Run the downloaded Miniconda exe file, and accept all the defaults
   * Once installed, search in your windows start menu (press Windows Button + S) for "miniconda".
   * Click on the item named "Anaconda Prompt (miniconda3)"
   * Type "`where python`" to confirm that the Python you are using is in a "miniconda3" folder
   * Run the above "pip install ..." command

## Linux Python Installation
* Run "`python3 --version`" to check which version of Python is already installed.  Python 3.7+ should work
   * If not installed, run "`sudo apt install python3`"
* If you get an error when running the above "pip install ..." command, try installing swig, which is a dependency of pyscard (dependency of pysim)
   * Run "`sudo apt install swig`"
   * Then rerun the above "pip install ..." command again
