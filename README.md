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


## Usage Examples
   If on Windows, replace `python3` with `python`

Help and Documentation
```
python3 sim_csv_script.py -h
```

Example Read Single
```
python3 ./sim_csv_script.py {example.csv}
```

Example Write Single (reading ADM pin from CLI arg)
* Specify ASCII ADM pin without the leading "0x"
```
python3 sim_csv_script.py {example.csv} --write --pin-adm 0x8888888888888888
```

Example Write Single (reading hexadecimal ADM pin from JSON file with {"IMSI key" : "ADM pin value"})
* Specify ASCII ADM pins without the leading "0x"
```
python3 sim_csv_script.py {example.csv} --write --pin-adm-json {IMSI_TO_ADM.json}
```

Example Read Multiple
```
python3 sim_csv_script.py {example.csv} --multiple
```

Example Write Multiple with Filter Script (with SAME filter script args for each new card)
* You can create a Filter Script (doesn't have to be Python) that reads in a CSV file from STDIN, modifies it, and outputs a new CSV file to STDOUT
* Filter Script must return 0 on Success
* Arguments to filter script can be specified after script name, except when --multiple-filter-args is enabled
* Do not specify filter args in --filter command when using the --multiple-filter-args option
* Filter Script should be able to function as a standalone program `python3 filter_script.py < {example.csv} {arg1}`
   * In Windows, running this in Powershell will cause an error, so run this in Command Prompt
```
python3 sim_csv_script.py {example.csv} --write --pin-adm-json {IMSI_TO_ADM.json} --multiple --filter {python3 filter_script.py arg1}
```

Example Write Multiple with Filter Script (with DIFFERENT filter script args for each new card)
```
python3 sim_csv_script.py {example.csv} --write --pin-adm-json {IMSI_TO_ADM.json} --multiple --filter {python3 filter_script.py} --multiple-new-args
```

---

## Windows Python Installation
* Miniconda is recommended for installing Python on Windows
   * Latest Python 3 version is recommended, but 3.7+ should work (https://docs.conda.io/en/latest/miniconda.html)
   * Run the downloaded Miniconda exe file, and accept all the defaults
   * Once installed, search in your windows start menu (press Windows Button + S) for "miniconda".
   * Click on the item named "Anaconda Prompt (miniconda3)"
   * Type `where python` to confirm that the Python you are using is in a "miniconda3" folder
   * In File Explorer, open the folder where you downloaded this repository, and copy and paste the path
   * Back in the "Anaconda Prompt (miniconda3)" terminal, run `cd {path to downloaded files}`
   * Run `python -m pip install -r requirements.txt`
   * Script should be accessible with `python sim_csv_script.py -h`

## Linux Python Installation
* Run `python3 --version` to check which version of Python is already installed.  Python 3.7+ should work
   * If not installed, run `sudo apt install python3`
* In a terminal, run `cd {path to downloaded files}`
* Run `python3 -m pip install -r requirements.txt`
* If you get an error when installing requirements.txt, try installing swig, which is a dependency of pyscard (dependency of pysim)
   * Run `sudo apt install swig`
   * Then rerun the pip install step again
