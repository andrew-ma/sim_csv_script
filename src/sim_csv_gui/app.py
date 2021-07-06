import argparse
import sys
import logging
import shlex
import pandas as pd
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import (
    QHeaderView,
    QMainWindow,
    QApplication,
    QFileDialog,
    QMessageBox,
)
from PyQt5.QtCore import QDir, QRegExp, QVariant, Qt, QModelIndex, QAbstractTableModel
from PyQt5 import QtGui


log = logging.getLogger(__name__)


from sim_csv_gui.ui_mainwindow import Ui_MainWindow
from sim_csv_script.app import (
    argparse_add_reader_args,
    get_filtered_dataframe,
    initialize_card_reader_and_commands,
    get_dataframe_from_csv,
    check_that_fields_are_valid,
    JSONFileArgType,
    set_commands_cla_byte_and_sel_ctrl,
    get_card,
    read_card_initial_data,
    verify_full_field_width,
    write_to_fieldname,
    read_fieldname
)


def get_reader_args():
    parser = argparse.ArgumentParser()
    parser = argparse_add_reader_args(parser)

    # use PC/SC reader as default
    parser.set_defaults(pcsc_dev=0)
    args = parser.parse_args()
    return args


def setup_logging_basic_config():
    LOG_FORMAT = "[%(levelname)s] %(message)s"

    logging.basicConfig(
        level=logging.DEBUG,
        format=LOG_FORMAT,
        handlers=[logging.StreamHandler()],
    )


class DataframeTableModel(QAbstractTableModel):
    def __init__(self, dataframe, parent=None):
        super().__init__(parent)
        self.dataframe = dataframe

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self.dataframe.index)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self.dataframe.columns)

    def data(self, index: QModelIndex, role: int):
        if not index.isValid():
            return QVariant()

        if role == Qt.DisplayRole:
            return QVariant(self.dataframe.iloc[index.row(), index.column()])

        if role == Qt.EditRole:
            return QVariant(self.dataframe.iloc[index.row(), index.column()])

    def headerData(
        self, column_index: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole
    ):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return QVariant(self.dataframe.columns[column_index])

    def flags(self, index: QModelIndex):
        return Qt.ItemIsEditable | Qt.ItemIsEnabled
        # return Qt.ItemIsEnabled | Qt.ItemIsSelectable

    def updateModel(self, dataframe):
        self.beginResetModel()
        self.dataframe = dataframe
        self.endResetModel()

        return self

    def clear(self):
        self.beginResetModel()
        self.dataframe = pd.DataFrame()
        self.endResetModel()


class SIM_CSV_GUI:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.MainWindow = QMainWindow()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self.MainWindow)

        self.connect_signals_with_slots()
        self.add_validators()
        self.MainWindow.show()

        self.default_palettes = {}
        self.window_title = "SIM CSV GUI"

        self.selected_CSV_filename = None
        self.selected_ADM_PIN_JSON_filename = None

        self.table_model = None

        # Right before the Write, should it use the state variables, or read from the field directly for current value??

    def set_ui_defaults(self):
        # ADM PIN file is disabled
        self.ui.admPinFileInpuContainer.setDisabled(True)
        self.look_disabled(self.ui.admPinFileRadioButton)

        # filter command is disabled
        self.ui.filterCommandLineEdit.setDisabled(True)
        self.look_disabled(self.ui.filterCheckbox)
        self.ui.filterApplyButton.setDisabled(True)

        # table
        # self.ui.tableView.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.ui.tableView.horizontalHeader().setStretchLastSection(True)
        self.ui.tableView.horizontalHeader().setDefaultAlignment(Qt.AlignLeft)
        self.ui.tableView.show()

    def connect_signals_with_slots(self):
        # Data
        self.ui.dataChooseFileButton.clicked.connect(
            self.on_dataChooseFileButton_clicked
        )

        # ADM PIN
        self.ui.admPinRadioButton.toggled.connect(self.on_admPinRadioButton_toggled)

        self.ui.admPinHexadecimalCheckbox.stateChanged.connect(
            self.on_admPinHexadecimalCheckbox_stateChanged
        )

        # ADM PIN FILE
        self.ui.admPinFileRadioButton.toggled.connect(
            self.on_admPinFileRadioButton_toggled
        )

        self.ui.admPinFileChooseFileButton.clicked.connect(
            self.on_admPinFileChooseFileButton_clicked
        )

        # Filter
        self.ui.filterCheckbox.stateChanged.connect(self.on_filterCheckbox_stateChanged)
        self.ui.filterApplyButton.clicked.connect(self.on_filterApplyButton_clicked)

        # READ/WRITE BUTTONS
        self.ui.readButton.clicked.connect(self.on_readButton_clicked)
        self.ui.writeButton.clicked.connect(self.on_writeButton_clicked)

    def add_validators(self):
        admPinLineEdit_pattern = QRegExp("(0x)?.{1,8}")
        admPinLineEdit_validator = QtGui.QRegExpValidator(
            admPinLineEdit_pattern, self.ui.admPinLineEdit
        )
        self.ui.admPinLineEdit.setValidator(admPinLineEdit_validator)

    def validate_csv_file(self):
        pass

    def validate_csv_file_with_filter(self):
        pass

    def filter_csv(self):
        pass

    def update_table(self, dataframe):
        # update the Table Model
        if self.table_model:
            self.table_model = self.table_model.updateModel(dataframe)
        else:
            self.table_model = self.populate_table_using_dataframe(dataframe)

    def get_filter_command(self):
        assert self.ui.filterCheckbox.isChecked()

        filter_text = self.ui.filterCommandLineEdit.text().strip()

        if not filter_text:
            raise Exception("Filter command is empty.")

        # FILTER COMMAND
        filter_command = shlex.split(filter_text)
        log.info(f"My Filter: {repr(filter_command)}")
        return filter_command

    def read_mode(self):
        try:
            log.debug("read_mode()")

            if self.selected_CSV_filename is None:
                # TODO: uncomment later
                raise Exception("CSV File is Required")

            if self.ui.filterCheckbox.isChecked():
                filter_command = self.get_filter_command()
                df = get_filtered_dataframe(self.selected_CSV_filename, filter_command)

            else:
                # NO FILTER
                df = get_dataframe_from_csv(self.selected_CSV_filename)
                check_that_fields_are_valid(df)

            self.update_table(df)

            # Card Reader Stuff
            reader_args = get_reader_args()
            sl, scc = initialize_card_reader_and_commands(reader_args)

            sl.wait_for_card(newcardonly=True)

            set_commands_cla_byte_and_sel_ctrl(scc, sl)

            card = get_card("auto", scc)

            _, imsi = read_card_initial_data(card)

            # Checking that FieldValue's length in bytes matches binary size of field (since we want to completely overwrite each field)
            # if we can read the binary size, but it doesn't match FieldValue's length in bytes, then it will raise a ValueError
            # and we alert user to fix the input file
            log.info("Checking that csv field values span full width of field")

            df.apply(
                lambda row: verify_full_field_width(
                    card, row["FieldName"], row["FieldValue"]
                ),
                axis=1,
            )

            # For each FieldName, FieldValue pair, write the value
            df["Read Value On Card"] = df.apply(
                lambda row: read_fieldname(
                    card,
                    row["FieldName"],
                ),
                axis=1,
            )
            print(df)



        except Exception as e:
            log.error(e)
            self.openErrorDialog(e.__class__.__name__, str(e))

    def write_mode(self):
        try:
            pass
        except Exception as e:
            log.error(e)
            self.openErrorDialog(e.__class__.__name__, str(e))
        # _, imsi = read_card_initial_data(card)
        # if self.ui.admPinRadioButton.isChecked():
        #     log.debug("Using pin")
        #     pin_adm = self.ui.admPinLineEdit.text()
        #     log.debug(f"Current ADM PIN: {pin_adm}")
        # elif self.ui.admPinFileRadioButton.isChecked():
        #     log.debug("Using pin File")
        #     log.debug(f"Current PIN FILE Name: {self.selected_ADM_PIN_JSON_filename}")

        #     if self.selected_ADM_PIN_JSON_filename is None:
        #         raise Exception("JSON File is Required")

        #     pin_adm_dict = JSONFileArgType(self.selected_ADM_PIN_JSON_filename)
        #     pin_adm = pin_adm_dict.get(imsi, None)
        #     if pin_adm is None:
        #         raise Exception(f"IMSI {imsi} is not found in PIN ADM JSON file")

    def get_filtered_dataframe(self):
        """Returns dataframe after filter"""
        pass

    def populate_table_using_dataframe(self, dataframe):
        """Populates Qt table using dataframe

        Each time, this creates a new model sets the table View to use this new model

        so only call this function when importing a new CSV file

        for existing CSV file, we just want to update the current model, and add a new column for READ fields
        """
        model = DataframeTableModel(dataframe)
        self.ui.tableView.setModel(model)
        return model

    def run(self):
        setup_logging_basic_config()
        self.set_ui_defaults()

        return self.app.exec_()

    # SLOT FUNCTIONS
    ###########################################################################
    # Data
    def on_dataChooseFileButton_clicked(self):
        log.debug("on_dataChooseFileButton_clicked()")

        csv_filename = self.openFileDialog("*.csv")
        log.debug(csv_filename)
        if csv_filename is not None:
            # update the label
            self.ui.dataFilenameLabel.setText(csv_filename)

            # and show in the Qt Table View
            try:
                df = get_dataframe_from_csv(csv_filename)
                check_that_fields_are_valid(df)
                # if CSV is valid, then display it in the Table, and save the Model that can be updated later
                if self.table_model:
                    self.table_model = self.table_model.updateModel(df)
                else:
                    self.table_model = self.populate_table_using_dataframe(df)

                self.selected_CSV_filename = csv_filename
            except Exception as e:
                # clear the label
                self.ui.dataFilenameLabel.setText("No file selected")
                self.selected_CSV_filename = None

                # Remove table from view
                self.table_model.clear()
                self.table_model = None

                log.error(e)
                self.openErrorDialog(e.__class__.__name__, str(e))

    # Write
    # Radio buttons
    def on_admPinFileRadioButton_toggled(self, checked: bool):
        log.debug("on_admPinFileRadioButton_toggled()")
        # disable the input elements container
        if checked:
            self.ui.admPinFileInpuContainer.setDisabled(False)
            self.look_normal(self.ui.admPinFileRadioButton)
        else:
            self.ui.admPinFileInpuContainer.setDisabled(True)
            self.look_disabled(self.ui.admPinFileRadioButton)

    def on_admPinRadioButton_toggled(self, checked: bool):
        log.debug("on_admPinRadioButton_toggled()")
        # disable the input elements container
        # log.debug(f"admPin is now {checked}")
        if checked:
            self.ui.admPinInputContainer.setDisabled(False)
            self.look_normal(self.ui.admPinRadioButton)
        else:
            self.ui.admPinInputContainer.setDisabled(True)
            self.look_disabled(self.ui.admPinRadioButton)

    # Choose file button
    def on_admPinFileChooseFileButton_clicked(self):
        log.debug("on_admPinFileChooseFileButton_clicked()")
        json_filename = self.openFileDialog("*.json")
        if json_filename is None:
            # clear the label
            self.ui.admPinFileFilenameLabel.setText("No file selected")
        else:
            # update the label
            self.ui.admPinFileFilenameLabel.setText(json_filename)

        log.debug(json_filename)

        self.selected_ADM_PIN_JSON_filename = json_filename

    # hexadecimal checkbox
    def on_admPinHexadecimalCheckbox_stateChanged(self, state: int):
        log.debug("on_admPinHexadecimalCheckbox_stateChanged()")

        admPin = self.ui.admPinLineEdit.text()
        if state == Qt.Checked:
            # prepend '0x' to the current value in input field
            self.ui.admPinLineEdit.setText("0x" + admPin)
        elif state == Qt.Unchecked:
            self.ui.admPinLineEdit.setText(admPin.removeprefix("0x"))

    # Filter
    def on_filterCommandLineEdit_textChanged(self, text: str):
        log.debug("on_filterCommandLineEdit_textChanged()")

    def on_filterCheckbox_stateChanged(self, state: int):
        log.debug("on_filterCheckbox_stateChanged()")

        if state == Qt.Checked:
            self.ui.filterCommandLineEdit.setEnabled(True)
            self.look_normal(self.ui.filterCheckbox)
            self.ui.filterApplyButton.setEnabled(True)
        elif state == Qt.Unchecked:
            # Disable the text edit
            self.ui.filterCommandLineEdit.setEnabled(False)
            self.look_disabled(self.ui.filterCheckbox)
            self.ui.filterApplyButton.setEnabled(False)

    def on_filterApplyButton_clicked(self):
        log.debug("on_filterApplyButton_clicked()")

        try:
            if not self.selected_CSV_filename:
                raise Exception("Requires CSV file")

            filter_command = self.get_filter_command()
            df = get_filtered_dataframe(self.selected_CSV_filename, filter_command)
            self.update_table(df)

        except Exception as e:
            log.error(e)
            self.openErrorDialog(e.__class__.__name__, str(e))

    # Read/Write
    def on_readButton_clicked(self):
        log.debug("on_readButton_clicked()")
        self.read_mode()

    def on_writeButton_clicked(self):
        log.debug("on_writeButton_clicked()")
        self.write_mode()

    ###########################################################################

    # Choose File Dialog
    @staticmethod
    def openFileDialog(name_filter="*.txt"):
        dlg = QFileDialog()
        dlg.setFileMode(QFileDialog.ExistingFile)
        dlg.setFilter(QDir.Files)
        dlg.setNameFilter(name_filter)

        if dlg.exec_():
            filename = dlg.selectedFiles()[0]
        else:
            filename = None

        return filename

    def openMessageBox(
        self,
        text,
        informative_text=None,
        window_title=None,
        icon=QMessageBox.Information,
    ):
        msg = QMessageBox()
        msg.setIcon(icon)
        msg.setText(text)
        if informative_text is not None:
            msg.setInformativeText(informative_text)
        if window_title is not None:
            msg.setWindowTitle(window_title)
        else:
            msg.setWindowTitle(self.window_title)
        msg.exec_()

    def openErrorDialog(self, text, informative_text=None):
        self.openMessageBox(text, informative_text, icon=QMessageBox.Critical)

    def look_disabled(self, widget):
        palette = widget.palette()

        widget_name = widget.objectName()
        if widget_name not in self.default_palettes:
            self.default_palettes[widget_name] = widget.palette()

        palette.setCurrentColorGroup(QtGui.QPalette.Disabled)
        palette.setColorGroup(
            QtGui.QPalette.Normal,
            palette.windowText(),
            palette.button(),
            palette.light(),
            palette.dark(),
            palette.mid(),
            palette.text(),
            palette.brightText(),
            palette.base(),
            palette.window(),
        )

        widget.setPalette(palette)

    def look_normal(self, widget):
        widget_name = widget.objectName()
        if widget_name not in self.default_palettes:
            self.default_palettes[widget_name] = widget.palette()
            return

        widget.setPalette(self.default_palettes[widget_name])


def main():
    gui = SIM_CSV_GUI()
    sys.exit(gui.run())


if __name__ == "__main__":
    main()
