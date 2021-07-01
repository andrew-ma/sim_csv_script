# Development

## System Requirements
* Python 3.7 or later ([Python Installation Steps](python-installation.md))

## Python Package Dependencies:
* pysim
    * Currently uses my fork, because of this commit (https://github.com/andrew-ma/pysim/commit/2f10406c9d3ba42787648fb0060475222531d905), and official repo doesn't accept pull requests on Github
* pandas
* PyQt5
* pyqt5-tools

## Development Installation
```
git clone -b main https://github.com/andrew-ma/sim_csv_script
cd sim_csv_script
pip install -e .
```

## Uninstall everything including dependencies
```
pip uninstall sim_csv_script -y
pip uninstall -r requirements.txt -y
pip uninstall -r requirements_gui.txt -y
pip uninstall -r requirements_gui_dev.txt -y
```

---

## __GUI Development__
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
