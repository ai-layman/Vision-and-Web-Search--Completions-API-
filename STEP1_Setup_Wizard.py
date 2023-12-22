import os
import sys
import json
import subprocess
import toml
from getpass import getpass

# List of required packages
REQUIRED_PACKAGES = [
    "openai",
    "streamlit",
    "toml",
    "requests",
    "Pillow",
    "google-api-python-client"
]

# Function to create a virtual environment
def create_virtual_environment(base_path):
    venv_path = os.path.join(base_path, "VisionWebSearchvenv")

    # Check if the virtual environment already exists
    if os.path.exists(venv_path):
        print(f"Virtual environment already exists at {venv_path}.")
    else:
        print(f"Creating virtual environment in {venv_path}...")
        subprocess.run([sys.executable, "-m", "venv", venv_path])
        print(f"Virtual environment created successfully in {venv_path}.")

        # Modified subprocess.run to capture and display errors
        result = subprocess.run([sys.executable, "-m", "venv", venv_path], capture_output=True, text=True)
        
        if result.returncode != 0:
            print("Error creating virtual environment:")
            print(result.stdout)
            print(result.stderr)
        else:
            print(f"Virtual environment created successfully in {venv_path}.") 

    return venv_path

# Function to install packages in the virtual environment
def install_packages(venv_path):
    for package in REQUIRED_PACKAGES:
        print(f"Installing {package}...")
        subprocess.run([os.path.join(venv_path, "Scripts", "pip"), "install", package])
    print("All required packages have been installed.")

# Function to gather API information and write to a secrets.toml file
def create_secrets_file(base_path):
    print("Please provide the following API information:")

    # Get API information from the user
    openai_api_key = getpass("Enter your OpenAI API key: ")
    google_api_key = getpass("Enter your Google API key: ")
    google_cse_id = getpass("Enter your Google CSE ID: ")
    pinecone_api_key = getpass("Enter your Pinecone API key: ")
    pinecone_api_env = input("Enter your Pinecone API environment: ")
    pinecone_index_name = input("Enter your Pinecone index name: ")

    # Data to write to secrets.toml
    secrets_data = {
        'OPENAI_API_KEY': openai_api_key,
        'GOOGLE_API_KEY': google_api_key,
        'GOOGLE_CSE_ID': google_cse_id,
        'PINECONE_API_KEY': pinecone_api_key,
        'PINECONE_API_ENV': pinecone_api_env,
        'PINECONE_INDEX_NAME': pinecone_index_name
    }

    # Create .streamlit directory if it doesn't exist
    streamlit_dir = os.path.join(base_path, '.streamlit')
    os.makedirs(streamlit_dir, exist_ok=True)

    # Write data to secrets.toml
    with open(os.path.join(streamlit_dir, 'secrets.toml'), 'w') as file:
        toml.dump(secrets_data, file)

    print("secrets.toml file has been created successfully.")

def main():
    print("Welcome to the Vision and Web Search AI Setup Wizard powered by AI Layman!")
    base_path = os.getcwd()  
    venv_path = create_virtual_environment(base_path)  # Create a virtual environment inside the base path
    install_packages(venv_path)  # Install the required packages in the virtual environment
    create_secrets_file(base_path)  # Request API information from the user and create .env file
    print("Setup complete! You can now proceed to the next steps of the project.")

if __name__ == "__main__":
    main()
