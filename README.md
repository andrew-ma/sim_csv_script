# SIM CSV Script

## Installation

System Dependencies:
* swig
    * dependency of pysim
```
# Linux
sudo apt install swig

# Windows
choco install swig
```


Python pip Dependencies:
*  pysim
    * Right now it uses my fork, because of this commit (https://github.com/andrew-ma/pysim/commit/2f10406c9d3ba42787648fb0060475222531d905)
* pandas

```
pip3 install -r requirements.txt
```

## Usage Examples

Help and Documentation
```
./sim_csv_script.py -h
```

Example Read Single
* Mainly used to detect errors like Missing CLI Args or Invalid CSV field names or field values
* To read values without writing, use '--write --dry-run'
```
./sim_csv_script.py -p 0 {example.csv}
```

Example Write Single Dry Run (reading ADM pin from CLI arg)
* Specify ASCII ADM pin without the leading "0x"
```
./sim_csv_script.py -p 0 {example.csv} --write --pin-adm 0x8888888888888888 --dry-run
```

Example Write Single Dry Run (reading hexadecimal ADM pin from JSON file with {"IMSI key" : "ADM pin value"})
* Specify ASCII ADM pins without the leading "0x"
```
./sim_csv_script.py -p 0 {example.csv} --write --pin-adm-json {IMSI_TO_ADM.json} --dry-run
```

Example Read Multiple
```
./sim_csv_script.py -p 0 {example.csv} --multiple
```

Example Write Multiple with Filter Script (with SAME filter script args for each new card)
* You can create a Filter Script (doesn't have to be Python) that reads in a CSV file from STDIN, modifies it, and outputs a new CSV file to STDOUT
* Filter Script must return 0 on Success
* The --filter cli arg can accept more arguments that will be passed to the Filter Script as args
```
./sim_csv_script.py -p 0 {example.csv} --write --pin-adm-json {IMSI_TO_ADM.json} --multiple --filter {filter_script.py} {arg1} {arg2} --dry-run 
```

Example Write Multiple with Filter Script (with DIFFERENT filter script args for each new card)
```
./sim_csv_script.py -p 0 {example.csv} --write --pin-adm-json {IMSI_TO_ADM.json} --multiple --filter {filter_script.py} --multiple-new-args --dry-run 
```