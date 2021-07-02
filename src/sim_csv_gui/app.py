import sys
import logging
from PyQt5 import QtWidgets
from sim_csv_gui.ui_mainwindow import Ui_MainWindow

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)


# Reader
def on_readerDropdown_currentTextChanged(text: str):
    log.debug("on_readerDropdown_currentTextChanged()")


def on_refreshButton_clicked():
    log.debug("on_refreshButton_clicked()")


# Data
def on_dataChooseFileButton_clicked():
    log.debug("on_dataChooseFileButton_clicked()")


# Write
# Radio buttons
def on_admPinFileRadioButton_toggled(checked: bool):
    log.debug("on_admPinFileRadioButton_toggled()")


def on_admPinRadioButton_toggled(checked: bool):
    log.debug("on_admPinRadioButton_toggled()")


# Choose file button
def on_admPinFileChooseFileButton_clicked():
    log.debug("on_admPinFileChooseFileButton_clicked()")


# enter pin
def on_admPinLineEdit_textChanged(text: str):
    log.debug("on_admPinLineEdit_textChanged()")


# hexadecimal checkbox
def on_admPinHexadecimalCheckbox_stateChanged(state: int):
    log.debug("on_admPinHexadecimalCheckbox_stateChanged()")


# Filter
def on_filterCommandLineEdit_textChanged(text: str):
    log.debug("on_filterCommandLineEdit_textChanged()")


def on_filterCheckbox_stateChanged(state: int):
    log.debug("on_filterCheckbox_stateChanged()")


# TODO: implement Table

# Read/Write
def on_readButton_clicked():
    log.debug("on_readButton_clicked()")


def on_writeButton_clicked():
    log.debug("on_writeButton_clicked()")


def main():
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = Ui_MainWindow()
    ui.setupUi(MainWindow)

    # CONNECT SIGNALS WITH SLOTS
    ###########################################################################
    ui.readerDropdown.currentTextChanged.connect(on_readerDropdown_currentTextChanged)
    ui.refreshButton.clicked.connect(on_refreshButton_clicked)
    ui.dataChooseFileButton.clicked.connect(on_dataChooseFileButton_clicked)
    ui.admPinFileRadioButton.toggled.connect(on_admPinFileRadioButton_toggled)
    ui.admPinRadioButton.toggled.connect(on_admPinRadioButton_toggled)
    ui.admPinFileChooseFileButton.clicked.connect(
        on_admPinFileChooseFileButton_clicked
    )
    ui.admPinLineEdit.textChanged.connect(on_admPinLineEdit_textChanged)
    ui.admPinHexadecimalCheckbox.stateChanged.connect(
        on_admPinHexadecimalCheckbox_stateChanged
    )
    ui.filterCommandLineEdit.textChanged.connect(on_filterCommandLineEdit_textChanged)
    ui.filterCheckbox.stateChanged.connect(on_filterCheckbox_stateChanged)
    ui.readButton.clicked.connect(on_readButton_clicked)
    ui.writeButton.clicked.connect(on_writeButton_clicked)
    ###########################################################################

    MainWindow.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
