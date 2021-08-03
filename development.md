# Development

## System Requirements
* Python 3.6 or later ([Python Installation Steps](python-installation.md))

---

## Creating a Source Distribution
* Source distribution file (*`sim_csv_script*-VERSION.tar.gz`*) will be created in *dist/* folder

Windows
```
make_distribution.bat
```

Linux
```
# TODO: create make_distribution.bat equivalent bash script
```

## Installing Source Distribution
Windows
```
python -m pip install {sim_csv_script-VERSION.tar.gz}
```

Linux
```
python3 -m pip install {sim_csv_script-VERSION.tar.gz}
```