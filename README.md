# SIM CSV Script
Python script to read and write SIM cards.
Fields and values are specified in a CSV file, and optionally a filter script can be supplied as a command line argument for dynamically changing the CSV contents for each card.

## System Requirements
* Python 3.6 or later ([Python Installation Steps](python_installation_steps.md))


## Installation
### Method #1: Source Distribution (`.tar.gz` file)
Windows
```
python -m pip install --upgrade {sim_csv_script-VERSION.tar.gz}
```

Linux
```
python3 -m pip install --upgrade {sim_csv_script-VERSION.tar.gz}
```

### Method #2: Source Code
* First, change into the directory that contains *`setup.py`* or *`setup.cfg`* file

Windows
```
python -m pip install --upgrade -e .
```

> _Windows_: if you get a "swig.exe" error while running the installation command, you will need to download the swig prebuilt executable (http://www.swig.org/download.html), extract the zip, and add the folder to your PATH.  Try running the installation steps again, and if it fails with a "Visual Studio Build Tools" error, then you will need to download https://visualstudio.microsoft.com/visual-cpp-build-tools/, install it, and select the "Desktop development with C++"


Linux
```
python3 -m pip install --upgrade -e .
```

> _Linux_: if you get a "swig: not found" error while running the installation command, first ensure that Python 3.6 or later is installed (`python3 --version`).  If so, install swig with `sudo apt install swig` and retry the installation command


---

## __COMMAND LINE SCRIPT__


### Help and Documentation
```
sim_csv_script -h
```

### List valid field names that can used in CSV file
```
sim_csv_script --list-field-names
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


### **Filter Script**
> _Windows_: substitute `python3` with `python`
* Provide a filter script (doesn't have to be Python) that reads in a CSV file from STDIN, modifies it, and outputs a new CSV file to STDOUT

* The filter script should function as a standalone program "`python3 filter_script.py {arg1} < {example.csv}`", and print out the filtered csv file
   * On Windows, run this in Command Prompt because Powershell does not have the "<" operator
   * In theory if standalone program works, copy and paste everything before the "<" as the `--filter`. (e.g. "`--filter python3 filter_script.py {arg1}`")

* Filter script must exit with a 0 return code to indicate Success.
  * Any other return code will be treated as failure

* If each card needs different filter script arguments, specify `--ask-filter-args`.
  * User will be prompted for input, which will be appended to end of `--filter` 


### Example Read Multiple with --filter
```
sim_csv_script {example.csv} --multiple --filter python3 filter_script.py {arg1}
```

### Example Read Multiple with --filter and --ask-filter-args
```
sim_csv_script {example.csv} --multiple --filter python3 filter_script.py --ask-filter-args
```

---

## For [Development Documentation](development.md)