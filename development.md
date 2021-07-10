# Development

## System Requirements
* Python 3.7 or later ([Python Installation Steps](python-installation.md))

## Python Package Dependencies:
* pysim
    * Currently uses my fork, because of this commit (https://github.com/andrew-ma/pysim/commit/2f10406c9d3ba42787648fb0060475222531d905), and official repo doesn't accept pull requests on Github
* pandas

## Install for Development
```
git clone -b main https://github.com/andrew-ma/sim_csv_script
cd sim_csv_script
pip install -e .
```

## Uninstall everything including dependencies
```
pip uninstall sim_csv_script -y
pip uninstall -r requirements.txt -y
```

--