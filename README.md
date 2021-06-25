# SIM CSV Script

## Installation

Python pip Dependencies:
*  pysim
    * Right now it uses my fork, because of this commit (https://github.com/andrew-ma/pysim/commit/2f10406c9d3ba42787648fb0060475222531d905)
* pandas

```
pip3 install -r requirements.txt
```
If you get an error when installing requirements.txt, try installing swig, which is a dependency of pyscard (dependency of pysim)

```
# Linux
sudo apt install swig
```


## Usage Examples

Help and Documentation
```
./sim_csv_script.py -h
```

Example Read Single
```
./sim_csv_script.py {example.csv}
```

Example Write Single (reading ADM pin from CLI arg)
* Specify ASCII ADM pin without the leading "0x"
```
./sim_csv_script.py {example.csv} --write --pin-adm 0x8888888888888888
```

Example Write Single (reading hexadecimal ADM pin from JSON file with {"IMSI key" : "ADM pin value"})
* Specify ASCII ADM pins without the leading "0x"
```
./sim_csv_script.py {example.csv} --write --pin-adm-json {IMSI_TO_ADM.json}
```

Example Read Multiple
```
./sim_csv_script.py {example.csv} --multiple
```

Example Write Multiple with Filter Script (with SAME filter script args for each new card)
* You can create a Filter Script (doesn't have to be Python) that reads in a CSV file from STDIN, modifies it, and outputs a new CSV file to STDOUT
* Filter Script must return 0 on Success
* Arguments to filter script can be specified after script name, except when --multiple-filter-args is enabled
* Do not specify filter args in --filter command when using the --multiple-filter-args option
* Filter Script should be able to function as a standalone program `./filter_script.py < {example.csv} {arg1}`
```
./sim_csv_script.py {example.csv} --write --pin-adm-json {IMSI_TO_ADM.json} --multiple --filter {filter_script.py} {arg1} {arg2}
```

Example Write Multiple with Filter Script (with DIFFERENT filter script args for each new card)
```
./sim_csv_script.py {example.csv} --write --pin-adm-json {IMSI_TO_ADM.json} --multiple --filter {filter_script.py} --multiple-new-args
```
