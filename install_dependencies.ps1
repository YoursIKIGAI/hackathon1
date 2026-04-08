# install_dependencies.ps1
# This script installs all necessary dependencies for the Speech-to-Text and Text-to-Speech components.

Write-Host "Installing dependencies for Voice Agent..."
pip install SpeechRecognition pyttsx3 pyaudio torch transformers accelerate
pip install oumi openai python-dotenv

Write-Host "Dependencies installed successfully!"
