from krita import DockWidget, Krita
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLineEdit, QPushButton, QLabel,
                             QHBoxLayout, QFrame, QSizePolicy, QProgressBar)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QFont, QIcon
import os
import base64
from google import genai
from google.genai import types
import datetime

DOCKER_TITLE = 'KritaFlash'

class DockerTemplate(DockWidget):

    def __init__(self):
        super().__init__()
        self.setWindowTitle(DOCKER_TITLE)
        
        # Create main widget and layout
        self.main_widget = QWidget(self)
        self.layout = QVBoxLayout(self.main_widget)
        self.layout.setContentsMargins(10, 15, 10, 15)
        self.layout.setSpacing(10)
        
        # Create header section
        header_label = QLabel("Gemini Image Generation")
        header_font = QFont()
        header_font.setBold(True)
        header_font.setPointSize(12)
        header_label.setFont(header_font)
        header_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(header_label)
        
        # Add API key configuration button
        api_key_button = QPushButton("Configure API Key")
        api_key_button.clicked.connect(self.show_api_key_setup)
        self.layout.addWidget(api_key_button)
        
        # Add separator
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        self.layout.addWidget(separator)
        
        # Add input section
        input_frame = QFrame()
        input_frame.setFrameShape(QFrame.StyledPanel)
        input_layout = QVBoxLayout(input_frame)
        
        # Add prompt label
        prompt_label = QLabel("Enter your generation prompt:")
        prompt_label.setFont(QFont("", 10))
        input_layout.addWidget(prompt_label)
        
        # Create text box with placeholder
        self.text_box = QLineEdit()
        self.text_box.setPlaceholderText("Example: Make it look like a watercolor painting")
        self.text_box.setMinimumHeight(30)
        input_layout.addWidget(self.text_box)
        
        # Add temperature slider
        temp_container = QWidget()
        temp_layout = QHBoxLayout(temp_container)
        temp_layout.setContentsMargins(0, 5, 0, 0)
        
        temp_label = QLabel("Temperature:")
        temp_layout.addWidget(temp_label)
        
        from PyQt5.QtWidgets import QSlider
        self.temp_slider = QSlider(Qt.Horizontal)
        self.temp_slider.setMinimum(0)
        self.temp_slider.setMaximum(40)  # 0, 0.5, 1.0, 1.5, 2.0 (5 steps)
        self.temp_slider.setValue(1)    # Default to 0.5 (index 1)
        self.temp_slider.setTickPosition(QSlider.TicksBelow)
        self.temp_slider.setTickInterval(1)
        temp_layout.addWidget(self.temp_slider)
        
        self.temp_value_label = QLabel("0.40")  # Default display value
        temp_layout.addWidget(self.temp_value_label)
        
        # Connect slider value change to update the label
        self.temp_slider.valueChanged.connect(self.update_temp_label)
        
        input_layout.addWidget(temp_container)
        
        # Add the input frame to the main layout
        self.layout.addWidget(input_frame)
        
        # Create generate button
        self.button = QPushButton("Generate Image")
        self.button.setMinimumHeight(40)
        self.button.setCursor(Qt.PointingHandCursor)
        self.button.clicked.connect(self.on_button_clicked)
        self.layout.addWidget(self.button)
        
        # Add progress bar (hidden by default)
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        self.progress_bar.hide()
        self.layout.addWidget(self.progress_bar)
        
        # Status label
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.status_label)
        
        # Add some spacing at the bottom
        self.layout.addStretch()
        
        # Instructions/help section
        help_frame = QFrame()
        help_frame.setFrameShape(QFrame.StyledPanel)
        help_layout = QVBoxLayout(help_frame)
        
        help_title = QLabel("How to use:")
        help_title.setFont(QFont("", 9, QFont.Bold))
        help_layout.addWidget(help_title)
        
        help_text = QLabel(
            "1. Enter a prompt describing your image edits\n"
            "2. Click 'Generate Image'\n"
            "3. Wait for Gemini to process your request\n"
            "4. The edited image will appear as a new layer"
        )
        help_text.setWordWrap(True)
        help_layout.addWidget(help_text)
        
        self.layout.addWidget(help_frame)
        
        # Set the main widget
        self.setWidget(self.main_widget)

    # notifies when views are added or removed
    def canvasChanged(self, canvas):
        pass
        
    def on_button_clicked(self):
        # Capture text data
        text_prompt = self.text_box.text()
        if not text_prompt:
            self.status_label.setText("Please enter a prompt first!")
            return
            
        # Check for API key
        if not self.get_api_key():
            self.status_label.setText("Gemini API key not configured. Please set it up first. Obtain your API key from https://aistudio.google.com/app/apikey")
            self.show_api_key_setup()
            return
            
        # Show progress and update status
        self.progress_bar.show()
        self.status_label.setText("Processing request...")
        self.button.setEnabled(False)
        
        # Save current canvas to temp.png (lossless)
        try:
            # Get the Krita instance and active document
            app = Krita.instance()
            document = app.activeDocument()
            
            if document:
                # Get the temp path with PNG extension for lossless saving
                temp_path = os.path.join(os.path.expanduser("~"), "temp.png")
                
                # Save the document to the temp path using PNG format
                document.setBatchmode(True)
                document.saveAs(temp_path)
                self.status_label.setText("Canvas saved. Generating image...")
                
                # Call Gemini to generate the image with the prompt
                output_path = self.generate_image(temp_path, text_prompt)
                
                # Add the generated image as a new layer
                if output_path:
                    self.add_image_as_layer(output_path)
                    self.status_label.setText("Image generated successfully!")
                else:
                    self.status_label.setText("Failed to generate image. Please try again.")
            else:
                self.status_label.setText("No active document found. Please open an image first.")
        except Exception as e:
            self.status_label.setText(f"Error: {str(e)}")
            print(f"Error in generation process: {str(e)}")
        finally:
            # Hide progress and re-enable button
            self.progress_bar.hide()
            self.button.setEnabled(True)

    def save_binary_file(self, file_name, data):
        f = open(file_name, "wb")
        f.write(data)
        f.close()

    def update_temp_label(self):
        """Update the temperature label when slider value changes"""
        # Convert slider value (0-4) to temperature (0.0-2.0)
        value = self.temp_slider.value() * 0.05
        self.temp_value_label.setText(f"{value:.2f}")
        
    def generate_image(self, input_image_path, prompt_text):
        try:
            # Get API key from configuration
            api_key = self.get_api_key()
            if not api_key:
                self.status_label.setText("API key not configured. Please set up your Gemini API key.")
                return None
            
            client = genai.Client(
                api_key=api_key,
            )

            # Get the temperature value from the slider
            temperature = self.temp_slider.value() * 0.05

            files = [
                # Make the file available in local system working directory
                client.files.upload(file=input_image_path),
            ]
            
            # Use the same model as AIDrawer, or try this specific model name
            model = "gemini-2.0-flash-exp-image-generation"
            
            # Simplified request structure similar to AIDrawer
            contents = [
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(text=prompt_text),
                        types.Part.from_uri(
                            file_uri=files[0].uri,
                            mime_type=files[0].mime_type,
                        ),
                    ],
                ),
            ]
            
            # Use generation config similar to AIDrawer
            generate_content_config = types.GenerateContentConfig(
                temperature=temperature,
                top_p=0.95,
                top_k=40,
                max_output_tokens=8192,
                response_modalities=[
                    "image",
                    "text",
                ],
                safety_settings=[
                    types.SafetySetting(
                        category="HARM_CATEGORY_CIVIC_INTEGRITY",
                        threshold="OFF",  # Off
                    ),
                ],
                response_mime_type="text/plain",
            )

            # Get the project directory from the active document
            app = Krita.instance()
            document = app.activeDocument()
            
            # Create output directory if it doesn't exist
            project_path = os.path.dirname(document.fileName())
            output_dir = os.path.join(project_path, "gemini_generations")
            
            # If the document hasn't been saved yet, use a temp directory
            if not project_path or project_path == "":
                output_dir = os.path.join(os.path.expanduser("~"), "gemini_generations")
            
            # Create the output directory if it doesn't exist
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            # Create a unique output filename with timestamp
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"gemini_output_{timestamp}.png"
            output_path = os.path.join(output_dir, output_filename)
            
            for chunk in client.models.generate_content_stream(
                model=model,
                contents=contents,
                config=generate_content_config,
            ):
                if not chunk.candidates or not chunk.candidates[0].content or not chunk.candidates[0].content.parts:
                    continue
                if chunk.candidates[0].content.parts[0].inline_data:
                    self.save_binary_file(
                        output_path, chunk.candidates[0].content.parts[0].inline_data.data
                    )
                    print(
                        "File of mime type"
                        f" {chunk.candidates[0].content.parts[0].inline_data.mime_type} saved"
                        f" to: {output_path}"
                    )
                    return output_path
                else:
                    print(chunk.text)
            
            return None
        except Exception as e:
            print(f"Error generating image: {str(e)}")
            return None

    def get_api_key(self):
        """Get the API key from configuration file or environment variable"""
        # Try to get API key from environment variable first
        api_key = os.environ.get('GEMINI_API_KEY')
        if api_key:
            return api_key
        
        # Then try from configuration file
        config_path = os.path.join(os.path.expanduser("~"), ".krita_flash_config")
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    api_key = f.read().strip()
                    if api_key:
                        return api_key
            except Exception as e:
                print(f"Error reading API key from config file: {str(e)}")
        
        return None

    def setup_api_key(self):
        """Set up the API key in configuration file"""
        api_key = self.api_key_input.text().strip()
        if not api_key:
            self.status_label.setText("Please enter a valid API key")
            return
        
        config_path = os.path.join(os.path.expanduser("~"), ".krita_flash_config")
        try:
            with open(config_path, 'w') as f:
                f.write(api_key)
            self.status_label.setText("API key saved successfully!")
            self.setup_dialog.accept()
        except Exception as e:
            self.status_label.setText(f"Error saving API key: {str(e)}")

    def show_api_key_setup(self):
        """Show dialog to set up API key"""
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton
        
        self.setup_dialog = QDialog(self)
        self.setup_dialog.setWindowTitle("Gemini API Key Setup")
        layout = QVBoxLayout(self.setup_dialog)
        
        layout.addWidget(QLabel("Enter your Gemini API Key:"))
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.Password)  # Hide the API key while typing
        layout.addWidget(self.api_key_input)
        
        save_button = QPushButton("Save")
        save_button.clicked.connect(self.setup_api_key)
        layout.addWidget(save_button)
        
        self.setup_dialog.setLayout(layout)
        self.setup_dialog.setMinimumWidth(300)
        self.setup_dialog.exec_()

    def add_image_as_layer(self, image_path):
        try:
            app = Krita.instance()
            document = app.activeDocument()
            
            if document:
                # Create a unique layer name with timestamp
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                layer_name = f"Gemini Generated {timestamp}"
                
                # Create a new file layer with the generated image
                layer = document.createFileLayer(layer_name, image_path, "None")
                
                # Add the layer to the document
                root = document.rootNode()
                root.addChildNode(layer, None)
                
                # Refresh the document view
                document.refreshProjection()
                app.activeWindow().activeView().canvas().update()
                
                print(f"Added generated image as new layer: {layer_name}")
            else:
                print("No active document to add layer to")
        except Exception as e:
            print(f"Error adding image as layer: {str(e)}")
