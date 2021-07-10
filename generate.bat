set "sim_csv_gui_dir=src\sim_csv_gui"
pushd %cd%
cd %sim_csv_gui_dir%
echo %cd%
python generate.py --package-name sim_csv_gui --ui-files UI\ui_mainwindow.ui --resource-files resources\resources.qrc
popd
sim_csv_gui