import argparse
from os import write
import sys
import logging
import shlex
import pandas as pd
from PyQt5.QtWidgets import (
    QHeaderView,
    QMainWindow,
    QApplication,
    QFileDialog,
    QMessageBox,
)
from PyQt5.QtCore import (
    QDir,
    QMutex,
    QRegExp,
    QVariant,
    Qt,
    QModelIndex,
    QAbstractTableModel,
    QObject,
    QThread,
    pyqtSignal,
)
from PyQt5 import QtGui


log = logging.getLogger(__name__)


from sim_csv_gui.ui_mainwindow import Ui_MainWindow
from sim_csv_script.app import (
    argparse_add_reader_args,
    check_pin_adm,
    get_filtered_dataframe,
    initialize_card_reader_and_commands,
    get_dataframe_from_csv,
    check_that_fields_are_valid,
    JSONFileArgType,
    read_fieldname_simple,
    write_fieldname_simple,
    set_commands_cla_byte_and_sel_ctrl,
    get_card,
    read_card_initial_data,
    verify_full_field_width,
    is_valid_hex,
)


def get_card_reader_args():
    parser = argparse.ArgumentParser()
    parser = argparse_add_reader_args(parser)

    # use PC/SC reader as default
    parser.set_defaults(pcsc_dev=0)
    args = parser.parse_args()
    return args


def setup_logging_basic_config():
    LOG_FORMAT = "[%(levelname)s] %(message)s"

    logging.basicConfig(
        level=logging.INFO,
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


class WaitForSIMCardWorker(QObject):
    finished = pyqtSignal(int)
    progress = pyqtSignal(int)

    def __init__(self, sl, parent=None):
        super(WaitForSIMCardWorker, self).__init__()
        self._sl = sl
        self._mutex = QMutex()
        self._running = True
        self._finish_code = 0

    def running(self):
        # If variable is currently being modified, then it will be locked
        # we try to lock it, and if it is currently locked, this call will block until it is unlocked (and can be changed)

        self._mutex.lock()
        running = self._running
        self._mutex.unlock()
        return running

    def run(self):
        log.debug("Running WaitForSIMCardWorker run() function")
        while self.running():
            try:
                # Every second, stop to check if we are still running
                self._sl.wait_for_card(timeout=1, newcardonly=True)
            except Exception as e:
                pass
            else:
                # If no exception, stop running
                self._mutex.lock()
                self._running = False
                self._mutex.unlock()

        self.finished.emit(self._finish_code)

    def stop(self):
        self._mutex.lock()
        self._running = False
        self._finish_code = 1
        self._mutex.unlock()


class ReadCardWorker(QObject):
    finished = pyqtSignal(int, object)
    progress = pyqtSignal(int)

    def __init__(self, df, scc, sl, parent=None):
        super(ReadCardWorker, self).__init__()
        self._df = df
        self._scc = scc
        self._sl = sl
        self._finish_code = 0

    def run(self):
        log.debug("Running ReadCardWorker run() function")

        set_commands_cla_byte_and_sel_ctrl(self._scc, self._sl)

        card = get_card("auto", self._scc)

        _, imsi = read_card_initial_data(card)

        # Checking that FieldValue's length in bytes matches binary size of field (since we want to completely overwrite each field)
        # if we can read the binary size, but it doesn't match FieldValue's length in bytes, then it will raise a ValueError
        # and we alert user to fix the input file

        self._df.apply(
            lambda row: verify_full_field_width(
                card, row["FieldName"], row["FieldValue"]
            ),
            axis=1,
        )

        num_fields = len(self._df.index)

        def read_each_field(row):
            percent_completed = int(((row.name + 1) / num_fields) * 100)
            self.progress.emit(percent_completed)

            return read_fieldname_simple(
                card,
                row["FieldName"],
            )

        # For each FieldName, FieldValue pair, write the value
        self._df["Value On Card"] = self._df.apply(
            read_each_field,
            axis=1,
        )

        differences = self._df["FieldValue"] != self._df["Value On Card"]
        self._df["Differences"] = differences.apply(lambda b: "X" if b else "")

        self.finished.emit(self._finish_code, self._df)


class WriteCardWorker(QObject):
    finished = pyqtSignal(int, object)
    progress = pyqtSignal(int)

    def __init__(
        self,
        df,
        scc,
        sl,
        pin_adm=None,
        imsi_to_pin_dict=None,
        dry_run=True,
        parent=None,
    ):
        super(WriteCardWorker, self).__init__()
        self._df = df
        self._scc = scc
        self._sl = sl
        self._finish_code = 0

        self._pin_adm = pin_adm
        self._imsi_to_pin_dict = imsi_to_pin_dict

        self._dry_run = dry_run

    def run(self):
        log.debug("Running WriteCardWorker run() function")

        # set_commands_cla_byte_and_sel_ctrl(self._scc, self._sl)

        card = get_card("auto", self._scc)

        _, imsi = read_card_initial_data(card)
        if self._imsi_to_pin_dict is not None:
            pin_adm = self._imsi_to_pin_dict.get(imsi, None)
            assert pin_adm is not None, f"IMSI {imsi} is not found in PIN ADM JSON file"
        else:
            pin_adm = self._pin_adm
            assert pin_adm is not None, "ADM PIN is None"

        # Checking that FieldValue's length in bytes matches binary size of field (since we want to completely overwrite each field)
        # if we can read the binary size, but it doesn't match FieldValue's length in bytes, then it will raise a ValueError
        # and we alert user to fix the input file

        self._df.apply(
            lambda row: verify_full_field_width(
                card, row["FieldName"], row["FieldValue"]
            ),
            axis=1,
        )

        num_fields = len(self._df.index)

        # Submit the PIN to the sim card
        if not self._dry_run:
            log.debug("Submitting PIN to card before writing values")
            check_pin_adm(card, pin_adm)

        def write_each_field(row):
            percent_completed = int(((row.name + 1) / num_fields) * 100)
            self.progress.emit(percent_completed)

            return write_fieldname_simple(
                card,
                row["FieldName"],
                row["FieldValue"],
                dry_run=self._dry_run,
            )

        # For each FieldName, FieldValue pair, write the value
        self._df["Value On Card"] = self._df.apply(
            write_each_field,
            axis=1,
        )

        differences = self._df["FieldValue"] != self._df["Value On Card"]
        self._df["Differences"] = differences.apply(lambda b: "X" if b else "")

        self.finished.emit(self._finish_code, self._df)


class TempSettings:
    def __init__(self):
        self._settings_dict = {}

    def setValue(self, key, value):
        self._settings_dict[key] = value

    def value(self, key, defaultValue=None):
        return self._settings_dict.get(key, defaultValue)

    def status(self):
        return 0

    def sync(self):
        pass


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

        self.dry_run = True

        self.settings = TempSettings()

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

        # Progress bar is initially hidden
        self.setup_progress_bar()
        self.ui.readWriteProgressBar.setVisible(False)

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
        # admPinLineEdit_pattern = QRegExp("(0x)?.{1,8}")
        # admPinLineEdit_validator = QtGui.QRegExpValidator(
        #     admPinLineEdit_pattern, self.ui.admPinLineEdit
        # )
        # self.ui.admPinLineEdit.setValidator(admPinLineEdit_validator)
        pass

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
        log.debug(f"My Filter: {repr(filter_command)}")
        return filter_command

    def wait_for_sim_card(self, _sl):
        # create a QThread object
        wait_for_sim_card_thread = QThread()

        # create a worker object
        self.wait_for_sim_card_worker = WaitForSIMCardWorker(_sl)

        # Move worker to the thread
        self.wait_for_sim_card_worker.moveToThread(wait_for_sim_card_thread)

        # Connect signals and slots

        # When Thread emits 'started' signal, run the Worker slot function
        wait_for_sim_card_thread.started.connect(self.wait_for_sim_card_worker.run)

        def __worker_finished(finish_code):
            log.debug(f"Wait For SIM Card Worker Finished With {finish_code}")

            if finish_code == 0:
                # Close the Message Box
                self.modal_msg_box.accept()
            else:
                # Don't reject(), just close, since reject will try to stop the Wait For Sim Card Thread
                self.modal_msg_box.done(2)

            self.wait_for_sim_card_worker.deleteLater()
            wait_for_sim_card_thread.quit()

        self.wait_for_sim_card_worker.finished.connect(__worker_finished)

        def __thread_finished():
            wait_for_sim_card_thread.deleteLater()

        wait_for_sim_card_thread.finished.connect(__thread_finished)

        log.debug("Starting thread")
        wait_for_sim_card_thread.start()

    def read_card(self, dataframe, scc, sl, callback=None):
        """[summary]

        Args:
            dataframe ([type]): [description]
            scc ([type]): [description]
            sl ([type]): [description]
            callback (dataframe, scc, sl): Is called if read worker finishes with finish_code == 0
        """
        # create a QThread object
        read_card_thread = QThread()

        # create a Worker object
        read_card_worker = ReadCardWorker(dataframe, scc, sl)

        # Move worker to the thread
        read_card_worker.moveToThread(read_card_thread)

        # Connect Signals and Slots

        # When Thread emits 'started' signal, run the Worker slot function
        def __run_read_card_worker():
            try:
                read_card_worker.run()
            except Exception as e:
                # Show Error
                self.openErrorDialog(e.__class__.__name__, informative_text=str(e))
                # Emit finished signal, but error, and show unchanged dataframe in table
                read_card_worker.finished.emit(1, None)

        read_card_thread.started.connect(__run_read_card_worker)

        # When Worker emits 'progress' signal, update the progress bar value
        read_card_worker.progress.connect(self.set_progress_bar_value)

        def __worker_finished(finish_code, new_dataframe):
            log.debug(f"Read Card Worker Finished With {finish_code}")
            # Enable Buttons before callback is called, because callback might want to Disable buttons
            self.enable_input_elements()

            if finish_code == 0:
                if callback is not None:
                    callback(dataframe=dataframe, scc=scc, sl=sl)

            read_card_worker.deleteLater()
            read_card_thread.quit()

            # Update Table with New Dataframe
            if new_dataframe is not None:
                self.update_table(new_dataframe)

        read_card_worker.finished.connect(__worker_finished)

        def __thread_finished():
            log.debug("Read Card Thread Finished")
            read_card_thread.deleteLater()

        read_card_thread.finished.connect(__thread_finished)

        ########################################################
        # Disable Buttons
        self.disable_input_elements()

        # Reset the progress bar
        self.ui.readWriteProgressBar.setValue(0)
        self.ui.readWriteProgressBar.setVisible(True)

        # Start the Thread
        read_card_thread.start()

    def setup_card_reader_and_wait_for_sim_card(self, callback=None):
        if self.selected_CSV_filename is None:
            raise Exception("CSV File is Required")

        if self.ui.filterCheckbox.isChecked():
            filter_command = self.get_filter_command()
            df = get_filtered_dataframe(self.selected_CSV_filename, filter_command)
        else:
            # NO FILTER
            df = get_dataframe_from_csv(self.selected_CSV_filename)
            check_that_fields_are_valid(df)

        self.update_table(df)

        ###############################################
        # Card Reader Stuff
        reader_args = get_card_reader_args()
        log.debug("Initializing Card Reader and Commands")

        sl, scc = initialize_card_reader_and_commands(reader_args)

        # Disable buttons while msg box
        self.disable_input_elements()

        # Wait for SIM card to be inserted in Separate Thread
        self.wait_for_sim_card(sl)

        def __insert_sim_reject_callback():
            log.debug("REJECTED INSERTING SIM CARD")
            try:
                # Depending on if worker is already deleted, when inserted card
                # This will work if we press Cancel button, which will trigger the worker to stop
                self.wait_for_sim_card_worker.stop()
            except Exception:
                pass

        def __insert_sim_accept_callback():
            log.debug("INSERTED SIM CARD")

            # Run read_card, or write_card
            if callback is not None:
                callback(dataframe=df, scc=scc, sl=sl)

        def __insert_sim_finished_callback():
            # Enable Buttons
            self.enable_input_elements()

        log.debug("Opening insert sim message box")
        self.openInsertSimMessageBox(
            reject_slot=__insert_sim_reject_callback,
            accept_slot=__insert_sim_accept_callback,
            finished_slot=__insert_sim_finished_callback,
        )

    def read_mode(self):
        def read_callback(dataframe, scc, sl):
            self.read_card(dataframe=dataframe, scc=scc, sl=sl)

        try:
            self.setup_card_reader_and_wait_for_sim_card(callback=read_callback)
        except Exception as e:
            log.error(e)
            self.openErrorDialog(e.__class__.__name__, informative_text=str(e))

    def get_adm_pin_from_input_fields(self):
        if self.ui.admPinRadioButton.isChecked():
            # Make sure that the ADM pin is valid
            pin_adm = self.ui.admPinLineEdit.text().strip()
            if pin_adm.startswith("0x") and not is_valid_hex(pin_adm):
                raise Exception("ADM PIN is not valid hex")
            imsi_to_pin_dict = None
        elif self.ui.admPinFileRadioButton.isChecked():
            # Make sure that a valid file is selected
            imsi_to_pin_dict = JSONFileArgType(self.selected_ADM_PIN_JSON_filename)
            pin_adm = None

        return pin_adm, imsi_to_pin_dict

    def disable_input_elements(self):
        # Disable all elements except for table, so user can review the values but not change the inputs
        self.ui.dataGroup.setDisabled(True)
        self.ui.writeGroup.setDisabled(True)
        self.ui.filterGroup.setDisabled(True)
        self.ui.readWriteGroup.setDisabled(True)

    def enable_input_elements(self):
        self.ui.dataGroup.setDisabled(False)
        self.ui.writeGroup.setDisabled(False)
        self.ui.filterGroup.setDisabled(False)
        self.ui.readWriteGroup.setDisabled(False)

    def write_mode(self):
        try:
            pin_adm, imsi_to_pin_dict = self.get_adm_pin_from_input_fields()

            def read_then_write_callback(dataframe, scc, sl):
                def ask_user_if_write_callback(*args, **kwargs):
                    # finished reading successfully

                    self.disable_input_elements()

                    def __accept_ask_write_callback():
                        log.debug("Writing SIM Card")
                        self.write_card(
                            dataframe,
                            scc,
                            sl,
                            pin_adm,
                            imsi_to_pin_dict,
                            dry_run=self.dry_run,
                        )

                    def __finished_ask_write_callback():
                        # Restore disabled elements
                        self.enable_input_elements()

                    self.openNonModalMessageBox(
                        "Write Values?",
                        buttons=QMessageBox.Cancel | QMessageBox.Ok,
                        icon=QMessageBox.Warning,
                        default_button=QMessageBox.Cancel,
                        accept_slot=__accept_ask_write_callback,
                        finished_slot=__finished_ask_write_callback,
                    )

                self.read_card(
                    dataframe=dataframe,
                    scc=scc,
                    sl=sl,
                    callback=ask_user_if_write_callback,
                )

            self.setup_card_reader_and_wait_for_sim_card(
                callback=read_then_write_callback
            )

        except Exception as e:
            log.error(e)
            self.openErrorDialog(e.__class__.__name__, informative_text=str(e))

    ##########################################################

    def write_card(
        self,
        dataframe,
        scc,
        sl,
        pin_adm=None,
        imsi_to_pin_dict=None,
        callback=None,
        dry_run=True,
    ):
        # create a QThread object
        write_card_thread = QThread()

        # create a Worker object
        write_card_worker = WriteCardWorker(
            dataframe, scc, sl, pin_adm, imsi_to_pin_dict, dry_run=dry_run
        )

        # Move worker to the thread
        write_card_worker.moveToThread(write_card_thread)

        # Connect Signals and Slots

        # When Thread emits 'started' signal, run the Worker slot function
        def __run_write_card_worker():
            try:
                write_card_worker.run()
            except Exception as e:
                # Show Error
                self.openErrorDialog(e.__class__.__name__, informative_text=str(e))
                # Emit finished signal, but error, and show unchanged dataframe in table
                write_card_worker.finished.emit(1, None)

        write_card_thread.started.connect(__run_write_card_worker)

        # When Worker emits 'progress' signal, update the progress bar value
        write_card_worker.progress.connect(self.set_progress_bar_value)

        def __worker_finished(finish_code, new_dataframe):
            # Enable Buttons before callback is called, because callback might want to Disable buttons
            self.enable_input_elements()

            if finish_code == 0:
                if callback is not None:
                    log.debug("Running write_card() callback function")
                    callback(dataframe=dataframe, scc=scc, sl=sl)

            write_card_worker.deleteLater()
            write_card_thread.quit()

            # Update Table with New Dataframe
            if new_dataframe is not None:
                self.update_table(new_dataframe)

        write_card_worker.finished.connect(__worker_finished)

        def __thread_finished():
            write_card_thread.deleteLater()

        write_card_thread.finished.connect(__thread_finished)

        ########################################################
        # Disable Buttons
        self.disable_input_elements()

        # Reset the progress bar
        self.ui.readWriteProgressBar.setValue(0)
        self.ui.readWriteProgressBar.setVisible(True)

        # Start the Thread
        write_card_thread.start()

    def setup_progress_bar(self):
        self.ui.readWriteProgressBar.reset()
        self.ui.readWriteProgressBar.setMinimum(0)
        self.ui.readWriteProgressBar.setMaximum(100)

    def set_progress_bar_value(self, value):
        self.ui.readWriteProgressBar.setValue(value)

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
        if csv_filename is not None:
            # update the label
            self.ui.dataFilenameLabel.setText(csv_filename)

            # and show in the Qt Table View
            try:
                df = get_dataframe_from_csv(csv_filename)
                check_that_fields_are_valid(df)
                # if CSV is valid, then display it in the Table, and save the Model that can be updated later
                self.update_table(df)

                self.selected_CSV_filename = csv_filename
            except Exception as e:
                # clear the label
                self.ui.dataFilenameLabel.setText("No file selected")
                self.selected_CSV_filename = None

                # Remove table from view
                if self.table_model:
                    self.table_model.clear()
                else:
                    self.table_model = None

                log.error(e)
                self.openErrorDialog(e.__class__.__name__, informative_text=str(e))

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
        if json_filename is not None:
            # update the label
            self.ui.admPinFileFilenameLabel.setText(json_filename)

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

            # return the Table to unfiltered form
            if self.selected_CSV_filename:
                df = get_dataframe_from_csv(self.selected_CSV_filename)
                self.update_table(df)

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
            self.openErrorDialog(e.__class__.__name__, informative_text=str(e))

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

    def save_dialog_position(self, dialog):
        self.settings.setValue("last_pos", dialog.pos())
        self.settings.sync()

    def restore_dialog_position(self, dialog):
        last_pos = self.settings.value("last_pos")
        if last_pos is not None:
            dialog.move(last_pos)

    @staticmethod
    def newMesssageBox(
        text,
        *,
        informative_text=None,
        window_title=None,
        icon=QMessageBox.Information,
        buttons=None,
        default_button=None,
        reject_slot=None,
        accept_slot=None,
        finished_slot=None,
        parent=None,
    ):
        # Returns the QMessageBox
        msg_box = QMessageBox(parent=parent)
        msg_box.setIcon(icon)
        msg_box.setText(text)

        if buttons is not None:
            msg_box.setStandardButtons(buttons)
        if default_button is not None:
            msg_box.setDefaultButton(default_button)
        if informative_text is not None:
            msg_box.setInformativeText(informative_text)
        if window_title is not None:
            msg_box.setWindowTitle(window_title)
        else:
            msg_box.setWindowTitle(window_title)

        if reject_slot is not None:
            msg_box.rejected.connect(reject_slot)

        if accept_slot is not None:
            msg_box.accepted.connect(accept_slot)

        if finished_slot is not None:
            msg_box.finished.connect(finished_slot)

        return msg_box

    def openNonModalMessageBox(self, text, *args, **kwargs):
        non_modal_msg_box = SIM_CSV_GUI.newMesssageBox(
            text,
            parent=self.MainWindow,
            window_title=self.window_title,
            *args,
            **kwargs,
        )
        non_modal_msg_box.setModal(False)

        self.restore_dialog_position(non_modal_msg_box)
        non_modal_msg_box.finished.connect(
            lambda: self.save_dialog_position(non_modal_msg_box)
        )

        non_modal_msg_box.show()
        return non_modal_msg_box

    def openMessageBox(self, text, *args, **kwargs):
        modal_msg_box = SIM_CSV_GUI.newMesssageBox(
            text,
            parent=self.MainWindow,
            window_title=self.window_title,
            *args,
            **kwargs,
        )

        # Save to instance variables, so other methods can close box
        self.modal_msg_box = modal_msg_box

        modal_msg_box.exec_()
        return modal_msg_box

    def openErrorDialog(self, text, *args, **kwargs):
        return self.openMessageBox(text, icon=QMessageBox.Critical, *args, **kwargs)

    def openInsertSimMessageBox(self, *args, **kwargs):
        return self.openMessageBox(
            "Insert SIM card...", buttons=QMessageBox.Cancel, *args, **kwargs
        )

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
        palette.setColorGroup(
            QtGui.QPalette.Inactive,
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
