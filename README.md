# SIM CSV Script
Python script to read and write SIM cards.
Fields and values are specified in a CSV file, and optionally a filter script can be supplied as a command line argument for dynamically changing the CSV contents for each card.

## System Requirements
* Python 3.7 or later ([Python Installation Steps](python-installation.md))

## Python Package Dependencies:
* pysim
    * Right now it uses my fork, because of this commit (https://github.com/andrew-ma/pysim/commit/2f10406c9d3ba42787648fb0060475222531d905), and official repo doesn't accept pull requests on Github
* pandas
* PyQt5

## Installation
```
pip install https://github.com/andrew-ma/sim_csv_script/archive/main.zip --upgrade --no-cache-dir
```

## Uninstall
```
pip uninstall sim_csv_script -y
```

---

## __COMMAND LINE SCRIPT__


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


### **Filters**
>  On Windows, replace `python3` with `python`
* You can create a filter script (doesn't have to be Python) that reads in a CSV file from STDIN, modifies it, and outputs a new CSV file to STDOUT

* The filter script should be able to function as a standalone program "`python3 filter_script.py unchanging_arg_1} < {example.csv}`"
   * In Windows, running this in Powershell will cause an error because Powershell doesn't have the '<' STDIN redirect operator, so run this in Command Prompt

* Filter script must return 0 on Success.  It should also raise Exceptions if it requires certain arguments.

* Supply a valid command (that can run in the terminal) to --filter, like "`--filter python3 filter_script.py`"
* Unchanging arguments can be specified immediately after the command.
* If different arguments need to be specified for each card, then we can set --ask-filter-args, which will ask user to type new arguments that will be appended to --filter command. 


### Example Read Multiple with --filter
```
sim_csv_script {example.csv} --multiple --filter {python3 filter_script.py unchanging_arg1}
```

### Example Read Multiple with --filter and --ask-filter-args
```
sim_csv_script {example.csv} --multiple --filter {python3 filter_script.py} --ask-filter-args
```

---
## __Graphical User Interface__

```
sim_csv_gui
```
