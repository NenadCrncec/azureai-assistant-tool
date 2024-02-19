# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license. See LICENSE.md file in the project root for full license information.

# This software uses the PySide6 library, which is licensed under the GNU Lesser General Public License (LGPL).
# For more details on PySide6's license, see <https://www.qt.io/licensing>

from PySide6.QtWidgets import QDialog, QVBoxLayout, QLineEdit, QLabel, QPushButton, QComboBox, QMessageBox, QTextEdit, QHBoxLayout, QCheckBox, QListWidget, QListWidgetItem
from PySide6.QtCore import Signal, Slot, Qt
from azure.ai.assistant.management.ai_client_factory import AIClientType, AIClientFactory
import os, json, logging
from azure.ai.assistant.management.logger_module import logger


class DebugViewDialog(QDialog):
    appendTextSignal = Signal(str)

    def __init__(self, broadcaster, parent=None):
        super(DebugViewDialog, self).__init__(parent)
        self.setWindowTitle("Debug View")
        self.resize(800, 800)  # Adjusted for additional space
        self.broadcaster = broadcaster
        # Store log messages
        self.logMessages = []

        mainLayout = QVBoxLayout()  # Top level layout is now vertical

        # Filter LineEdit at the top
        self.filterLineEdit = QLineEdit()
        self.filterLineEdit.setPlaceholderText("Add new filter (e.g., 'ERROR') and press Enter")
        self.filterLineEdit.textChanged.connect(self.apply_filter)
        self.filterLineEdit.returnPressed.connect(self.add_filter_word)
        mainLayout.addWidget(self.filterLineEdit)

        # Horizontal layout for filter list and log view
        contentLayout = QHBoxLayout()

        # Filter List Section
        filterListLayout = QVBoxLayout()
        self.filterList = QListWidget()
        self.filterList.setFixedWidth(200)
        self.filterList.itemChanged.connect(self.apply_filter)
        filterListLayout.addWidget(QLabel("Filters:"))
        filterListLayout.addWidget(self.filterList)

        # Log View Section
        logViewLayout = QVBoxLayout()
        self.textEdit = QTextEdit()
        self.textEdit.setReadOnly(True)
        self.textEdit.setStyleSheet("""
            QTextEdit {
                border: 1px solid #c0c0c0; /* Adjusted to have a 1px solid border */
                border-color: #a0a0a0 #ffffff #ffffff #a0a0a0;
                border-radius: 4px;
                padding: 1px; /* Adds padding inside the QTextEdit widget */
            }
        """)
        logViewLayout.addWidget(QLabel("Log:"))
        logViewLayout.addWidget(self.textEdit)

        # Optional: Add other controls like log level selection and clear button to the logViewLayout
        controlLayout = QHBoxLayout()
        self.logLevelComboBox = QComboBox()
        self.clearButton = QPushButton("Clear")
        self.clearButton.setAutoDefault(False)
        self.clearButton.setDefault(False)
        self.clearButton.clicked.connect(self.clear_log_window)
        controlLayout.addWidget(QLabel("Log Level:"))
        controlLayout.addWidget(self.logLevelComboBox)
        controlLayout.addWidget(self.clearButton)
        logViewLayout.addLayout(controlLayout)

        # Populate log level combo box
        for level in ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'):
            self.logLevelComboBox.addItem(level, getattr(logging, level))
        self.logLevelComboBox.currentIndexChanged.connect(self.change_log_level)
        self.change_log_level(0)  # Set default log level

        # Combine filter list and log view sections into the content layout
        contentLayout.addLayout(filterListLayout, 1)  # Filter list section
        contentLayout.addLayout(logViewLayout, 3)  # Log view section

        # Add the content layout below the filter QLineEdit
        mainLayout.addLayout(contentLayout)

        self.setLayout(mainLayout)

        self.appendTextSignal.connect(self.append_text_slot)
        self.broadcaster.subscribe(self.queue_append_text)

    @Slot(str)
    def append_text_slot(self, message):
        self.textEdit.append(message)
        # Store the message
        self.logMessages.append(message)
        # Apply the current filter
        self.apply_filter()

    def queue_append_text(self, message):
        self.appendTextSignal.emit(message)

    def change_log_level(self, index):
        level = self.logLevelComboBox.itemData(index)
        logger.setLevel(level)

        # Set the log level for the OpenAI logger
        openai_logger = logging.getLogger("openai")
        openai_logger.setLevel(level)

    def clear_log_window(self):
        self.textEdit.clear()
        self.logMessages.clear()

    def apply_filter(self):
        # Check if any filter is selected
        is_any_filter_selected = any(self.filterList.item(i).checkState() == Qt.CheckState.Checked for i in range(self.filterList.count()))

        # Clear the textEdit widget
        self.textEdit.clear()

        if is_any_filter_selected:
            # Filter based on selected items in the list box
            selected_filters = [self.filterList.item(i).text().lower() for i in range(self.filterList.count()) if self.filterList.item(i).checkState() == Qt.CheckState.Checked]

            # Re-add messages that match any of the selected filters
            for message in self.logMessages:
                if any(filter_word in message.lower() for filter_word in selected_filters):
                    self.textEdit.append(message)
        else:
            # Get the current filter text
            filter_text = self.filterLineEdit.text().lower()
            # Re-add messages that match the filter
            for message in self.logMessages:
                if filter_text in message.lower():
                    self.textEdit.append(message)
        pass

    def add_filter_word(self):
        # Get the text from QLineEdit
        filter_word = self.filterLineEdit.text()
        if not filter_word:
            return

        # Create a new QListWidgetItem
        item = QListWidgetItem(filter_word)
        #item.setFlags(item.flags() | Qt.ItemIsUserCheckable)  # Make the item checkable
        item.setCheckState(Qt.CheckState.Unchecked)  # Set the item to be checked by default

        # Add the item to the list
        self.filterList.addItem(item)

        # Clear the QLineEdit for the next filter word
        #self.filterLineEdit.clear()

        # Apply the current filter with the new filter word added
        self.apply_filter()


class GeneralSettingsDialog(QDialog):
    def __init__(self, parent=None):
        super(GeneralSettingsDialog, self).__init__(parent)
        self.setWindowTitle("General Settings")
        self.main_window = parent

        # Initialize the UI components
        self.setup_ui()

    def setup_ui(self):
        self.layout = QVBoxLayout(self)

        # Thread timeout configuration
        self.threadTimeoutLayout = QHBoxLayout()
        self.threadTimeoutLabel = QLabel("Thread Timeout (s):", self)
        self.threadTimeoutEdit = QLineEdit(self)
        self.threadTimeoutEdit.setText(str(self.main_window.thread_timeout))
        self.threadTimeoutLayout.addWidget(self.threadTimeoutLabel)
        self.threadTimeoutLayout.addWidget(self.threadTimeoutEdit)
        
        # Run timeout configuration
        self.runTimeoutLayout = QHBoxLayout()
        self.runTimeoutLabel = QLabel("Run Timeout (s):", self)
        self.runTimeoutEdit = QLineEdit(self)
        # self.main_window.run_timeout is float, so we need to convert it to string
        self.runTimeoutEdit.setText(str(self.main_window.run_timeout))
        self.runTimeoutLayout.addWidget(self.runTimeoutLabel)
        self.runTimeoutLayout.addWidget(self.runTimeoutEdit)

        # Chat completion for friendly conversation thread names
        self.useChatCompletionForThreadsCheckbox = QCheckBox("Enable chat completion for friendly conversation thread names", self)
        self.useChatCompletionForThreadsCheckbox.setChecked(self.main_window.use_chat_completion_for_thread_name)

        # Buttons
        self.buttonsLayout = QHBoxLayout()
        self.okButton = QPushButton("OK", self)
        self.cancelButton = QPushButton("Cancel", self)
        self.buttonsLayout.addWidget(self.okButton)
        self.buttonsLayout.addWidget(self.cancelButton)

        # Adding layouts to the main layout
        self.layout.addLayout(self.threadTimeoutLayout)
        self.layout.addLayout(self.runTimeoutLayout)
        self.layout.addWidget(self.useChatCompletionForThreadsCheckbox)
        self.layout.addLayout(self.buttonsLayout)

        # Connect signals
        self.okButton.clicked.connect(self.accept)
        self.cancelButton.clicked.connect(self.reject)

    def accept(self):
        # Validate and save the timeout settings here
        # Example validation:
        try:
            thread_timeout = float(self.threadTimeoutEdit.text())
            run_timeout = float(self.runTimeoutEdit.text())
            use_chat_completion_for_thread_name = self.useChatCompletionForThreadsCheckbox.isChecked()
            self.main_window.thread_timeout = thread_timeout
            self.main_window.run_timeout = run_timeout
            self.main_window.use_chat_completion_for_thread_name = use_chat_completion_for_thread_name
            # Here you would save these values to your settings or pass them to where they are needed
            super(GeneralSettingsDialog, self).accept()  # Close the dialog on success
        except ValueError:
            QMessageBox.warning(self, "Invalid Input", "Please enter valid numbers for the timeouts.")


class ClientSettingsDialog(QDialog):
    def __init__(self, main_window):
        super(ClientSettingsDialog, self).__init__(main_window)
        self.main_window = main_window
        self.init_settings()
        self.init_ui()

    def init_settings(self):
        self.config_folder = "config"
        self.file_name = "chat_completion_settings.json"
        self.file_path = os.path.join(self.config_folder, self.file_name)
        os.makedirs(self.config_folder, exist_ok=True)
        self.settings = {}
        self.load_settings()

    def init_ui(self):
        self.setWindowTitle("Settings")
        self.resize(400, 400)
        self.layout = QVBoxLayout(self)

        # Client Selection Label
        self.clientSelectionLabel = QLabel("Select AI client for Chat Completion:")
        self.layout.addWidget(self.clientSelectionLabel)

        # Create combo box for client selection
        self.clientSelection = QComboBox()
        ai_client_type_names = [client_type.name for client_type in AIClientType]
        self.clientSelection.addItems(ai_client_type_names)
        self.layout.addWidget(self.clientSelection)
        # Connect the client selection change signal to the slot
        self.clientSelection.currentIndexChanged.connect(self.update_model_selection)

        # OpenAI API Key
        self.openai_api_key_input = QLineEdit()
        self.openai_api_key_input.setPlaceholderText("Enter your OpenAI API key")
        self.layout.addWidget(QLabel("OpenAI API Key:"))
        self.layout.addWidget(self.openai_api_key_input)

        # Azure OpenAI API Key
        self.azure_api_key_input = QLineEdit()
        self.azure_api_key_input.setPlaceholderText("Enter your Azure OpenAI API key")
        self.layout.addWidget(QLabel("Azure OpenAI API Key:"))
        self.layout.addWidget(self.azure_api_key_input)

        # Azure Endpoint
        self.azure_endpoint_input = QLineEdit()
        self.azure_endpoint_input.setPlaceholderText("Enter your Azure OpenAI Endpoint")
        self.layout.addWidget(QLabel("Azure OpenAI Endpoint:"))
        self.layout.addWidget(self.azure_endpoint_input)

        # Azure API Version
        self.azure_api_version_input = QLineEdit()
        self.azure_api_version_input.setPlaceholderText("Enter your Azure OpenAI API Version")
        self.layout.addWidget(QLabel("Azure OpenAI API Version:"))
        self.layout.addWidget(self.azure_api_version_input)

        # Model selection
        self.model_selection = QComboBox()
        self.model_selection.setEditable(True)
        ai_client_type = AIClientType[self.clientSelection.currentText()]
        self.layout.addWidget(QLabel("Model for Chat Completion:"))
        self.layout.addWidget(self.model_selection)

        # Apply Button
        self.applyButton = QPushButton("Apply")
        self.applyButton.clicked.connect(self.apply_settings)
        self.layout.addWidget(self.applyButton)

        # Set initial states based on settings
        self.set_initial_states()

    def load_settings(self):
        """ Load settings from JSON file. """
        if os.path.exists(self.file_path):
            with open(self.file_path, 'r') as file:
                loaded_settings = json.load(file)
                self.settings.update(loaded_settings)

    def set_initial_states(self):
        ai_client_type = self.settings.get("ai_client_type", AIClientType.OPEN_AI.name)
        api_version = self.settings.get("api_version", "2023-09-01-preview")
        self.azure_api_version_input.setText(api_version)

        if ai_client_type == AIClientType.OPEN_AI.name:
            api_version = None

        # Fill the model selection
        self.fill_client_model_selection(AIClientType[ai_client_type], api_version)

        # Set the API keys and endpoint values from environment variables
        self.set_key_input_value(self.openai_api_key_input, "OPENAI_API_KEY")
        self.set_key_input_value(self.azure_api_key_input, "AZURE_OPENAI_API_KEY")
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
        self.azure_endpoint_input.setText(endpoint)

    def fill_client_model_selection(self, ai_client_type, api_version=None):

        if ai_client_type == AIClientType.AZURE_OPEN_AI:
            self.clientSelection.setCurrentText(AIClientType.AZURE_OPEN_AI.name)
            self.azure_endpoint_input.setEnabled(True)
            self.azure_api_key_input.setEnabled(True)
            self.openai_api_key_input.setEnabled(False)
            self.azure_api_version_input.setEnabled(True)
        else:
            self.clientSelection.setCurrentText(AIClientType.OPEN_AI.name)
            self.azure_endpoint_input.setEnabled(False)
            self.azure_api_key_input.setEnabled(False)
            self.openai_api_key_input.setEnabled(True)
            self.azure_api_version_input.setEnabled(False)

        # Clear existing items in model_selection
        self.model_selection.clear()

        try:
            if ai_client_type == AIClientType.OPEN_AI:
                # Get the AI client instance, pass the api_version if it's set
                ai_client = AIClientFactory.get_instance().get_client(ai_client_type, api_version)
                # Fetch and add new models to the model_selection
                if ai_client:
                    models = ai_client.models.list().data
                    for model in models:
                        self.model_selection.addItem(model.id)
            elif ai_client_type == AIClientType.AZURE_OPEN_AI:
                models = []

            # Set the default model
            default_model = self.settings.get("model", "")
            if default_model:
                self.model_selection.setCurrentText(default_model)

        except Exception as e:
            QMessageBox.warning(self, "Warning", f"Failed to fill model selection: {e}")

    def update_model_selection(self):
        # Get the current AI client type
        ai_client_type = AIClientType[self.clientSelection.currentText()]

        # Determine the API version for Azure OpenAI, if needed
        api_version = None
        if ai_client_type == AIClientType.AZURE_OPEN_AI:
            api_version = self.azure_api_version_input.text().strip() or "2023-09-01-preview"

        # Call fill_model_selection with the selected AI client type and API version
        self.fill_client_model_selection(ai_client_type, api_version)

    def set_key_input_value(self, input_field, env_var):
        key = os.getenv(env_var, "")
        if key:
            # Obscure all but the last 4 characters of the key
            obscured_key = '*' * (len(key) - 4) + key[-4:]
            input_field.setText(obscured_key)

    def apply_settings(self):
        ai_client_type = self.clientSelection.currentText()
        # Check for empty required fields
        if ai_client_type == AIClientType.OPEN_AI and not self.openai_api_key_input.text():
            QMessageBox.critical(self, "Error", "OpenAI API Key is required when applying OpenAI settings.")
            return
        elif ai_client_type == AIClientType.AZURE_OPEN_AI and (not self.azure_api_key_input.text() or not self.azure_endpoint_input.text()):
            QMessageBox.critical(self, "Error", "Azure OpenAI API Key and Endpoint are required when applying Azure OpenAI settings.")
            return

        settings = {
            "ai_client_type": ai_client_type,
            "model": self.model_selection.currentText(),
            "api_version": self.azure_api_version_input.text()
        }

        # Save the API keys and endpoint to environment variables
        self.save_environment_variable("OPENAI_API_KEY", self.openai_api_key_input.text())
        self.save_environment_variable("AZURE_OPENAI_API_KEY", self.azure_api_key_input.text())
        self.save_environment_variable("AZURE_OPENAI_ENDPOINT", self.azure_endpoint_input.text())

        # Save the settings to file
        self.save_settings(json.dumps(settings, indent=4))
        self.accept()

    def save_environment_variable(self, var_name, value):
        if value and not value.startswith('*******'):
            os.environ[var_name] = value

    def save_settings(self, settings_json : str):
        with open(self.file_path, 'w') as file:
            file.write(settings_json)
