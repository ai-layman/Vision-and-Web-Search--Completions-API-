import os
import json
from datetime import datetime
import uuid
import streamlit as st
from PIL import Image
from io import BytesIO
import base64
from openai import OpenAI
import requests
from googleapiclient.discovery import build

# Set page title
st.set_page_config(page_title="My GPT", layout="centered", initial_sidebar_state="collapsed")
st.title("My GPT: Powered by AI Layman")

# Retrieve the OpenAI API Key
api_key = st.secrets["OPENAI_API_KEY"]

# Initialize the OpenAI client with the API key
client = OpenAI(api_key=api_key)

# Initialize or retrieve the message list
if 'messages' not in st.session_state:
    st.session_state['messages'] = []

# Function to resize and encode image
def process_image(image_file):
    size = (2048, 2048)
    image = Image.open(image_file)
    image = image.resize(size, Image.LANCZOS)

    if image.mode == 'RGBA':
        image = image.convert('RGB')

    buffered = BytesIO()
    image.save(buffered, format="JPEG")
    return base64.b64encode(buffered.getvalue()).decode("utf-8")

# Handle image upload
uploaded_file = st.file_uploader("Upload an image", type=["jpg", "png", "jpeg"])

# Store the uploaded image in the session state but don't process it yet
if uploaded_file:
    st.session_state['uploaded_image'] = uploaded_file

# Function for Google Custom Search on item
def search_online(item):
    api_key = st.secrets["GOOGLE_API_KEY"]
    cse_id = st.secrets["GOOGLE_CSE_ID"]
    query = f"{item}"
    url = f"https://www.googleapis.com/customsearch/v1?key={api_key}&cx={cse_id}&q={query}&num=5"
    response = requests.get(url)
    return response.json().get('items', [])

# Function for simplifying Google Custom Search Response
def simplify_tool_response(tool_response):
    try:
        # Load the JSON content
        search_results = json.loads(tool_response['content'])

        # Simplify each search result
        simplified_results = []
        for result in search_results:
            simplified_result = {}

            # Extract the website name (displayLink), link, and if available, snippet that might contain the price
            simplified_result['website'] = result.get('displayLink', 'N/A')
            simplified_result['link'] = result.get('link', 'N/A')
            simplified_result['snippet'] = result.get('snippet', 'No additional info')

            # Append the simplified result to the list
            simplified_results.append(simplified_result)

        # Convert the list of simplified results back to JSON string
        return json.dumps(simplified_results, indent=2)
    except Exception as e:
        print(f"Error simplifying tool response: {e}")
        return "[]"

# Function to handle tool calls
def handle_tool_calls(tool_calls):
    tool_responses = []
    for tool_call in tool_calls:
        if tool_call.function.name == "search_online":
            args = json.loads(tool_call.function.arguments)
            response = search_parts_online(**args)
            tool_responses.append({
                "tool_call_id": tool_call.id,
                "role": "tool",
                "name": tool_call.function.name,
                "content": json.dumps(response)
            })
    return tool_responses

#List of tools available to the GPT
tools = [
    {
        "type": "function",
        "function": {
            "name": "search_online",
            "description": "Search for user's requested item online",
            "parameters": {
                "type": "object",
                "properties": {
                    "item": {
                        "type": "string",
                        "description": "The item user is searching for",
                    },
                },
                "required": ["item"],
            },
        },
    },
]

# Text input for user's question or comment
user_input = st.text_input("Your question or comment:")

# Button to trigger the analysis or conversation continuation
send_button = st.button("Send")

if send_button:
    print("Send button pressed")

    # Define a placeholder for messages
    message_placeholder = st.empty()

    # Initialize previous_image and new_image_uploaded in session state if not already set
    if 'previous_image' not in st.session_state:
        st.session_state['previous_image'] = None
    if 'new_image_uploaded' not in st.session_state:
        st.session_state['new_image_uploaded'] = False

    # Process the uploaded image and check for new upload
    if uploaded_file:
        print("Uploaded file detected.")
        previous_image = st.session_state['previous_image']
        current_image = uploaded_file.getvalue()

        # Debugging print statements
        # Check if previous_image is not None before getting its length
        previous_image_size = len(previous_image) if previous_image is not None else 0
        print("Previous Image Size:", previous_image_size)
        print("Current Image Size:", len(current_image))

        # Check if the current image is different from the previous image
        if previous_image != current_image:
            print("New image detected. Processing and updating session state.")
            st.session_state['new_image_uploaded'] = True
            st.session_state['previous_image'] = current_image
            encoded_image = process_image(uploaded_file)
            st.session_state['messages'].append({"type": "image", "content": encoded_image, "uuid": str(uuid.uuid4())})
        else:
            print("No new image uploaded. Using existing session data.")
            st.session_state['new_image_uploaded'] = False

        print("New image uploaded: ", st.session_state['new_image_uploaded'])

    # Define multiple prompt text instructions
    prompt_text = (
        "You are an AI that analyzes images and searches for the item online."
    )

    # Prepare the payload
    
    # Logic for new image uploaded
    if st.session_state['new_image_uploaded']:
        print("Using gpt-4-vision-preview model for image analysis.")
        print("Session State (last 500 chars):", str(st.session_state['messages'])[-500:])

        # Create payload for gpt-4-vision-preview image analysis
        openai_payload = [{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt_text + (user_input if user_input else "What is in this image?")},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded_image}"}}
            ]
        }]
        print("Payload to OpenAI (first 500 chars):", str(openai_payload)[:500])

        # Send payload to gpt-4-vision-preview and handle response
        try:
            final_response_vision = ""
            for completion in client.chat.completions.create(
                    model="gpt-4-vision-preview",
                    messages=openai_payload,
                    max_tokens=4000,
                    stream=True):
                if completion.choices[0].delta.content:
                    final_response_vision += completion.choices[0].delta.content
            message_placeholder.markdown(final_response_vision)
            st.session_state['messages'].append({"type": "text", "content": final_response_vision})
            print("Session State (last 500 chars):", str(st.session_state['messages'])[-500:])

        except Exception as e:
            st.error(f"An error occurred: {e}")
            print(f"Exception occurred during model interaction: {e}")
    
        print("Final Response from Vision Model:", final_response_vision)

    # Logic for no new image uploaded
    else:
        print("Using gpt-4-1106-preview model for text analysis and function calling.")

        # Prepare the conversation history, including responses and user inputs
        conversation_history = []
        for message in st.session_state['messages']:
            if message['type'] == 'text':
                conversation_history.append({"role": "user", "content": message['content']})

        # Append current user input
        conversation_history.append({"role": "user", "content": user_input})
        print("Conversation History (last 500 chars):", str(conversation_history)[-500:])

        # Send payload to gpt-4-1106-preview and handle response and tool calls
        try:
            # Print the conversation history before sending it to the model
            print("Preparing to send payload to gpt-4-1106-preview model.")
            print("Conversation History (pre-send):", json.dumps(conversation_history, indent=2))

            response = client.chat.completions.create(
                model="gpt-4-1106-preview",
                messages=conversation_history,
                tools=tools,
                max_tokens=4000
            )

            # Serialize tool calls
            serialized_tool_calls = []
            if response.choices[0].message.tool_calls:
                for tool_call in response.choices[0].message.tool_calls:
                    serialized_tool_call = {
                        "id": tool_call.id,
                        "type": tool_call.type,
                        "function": {
                            "name": tool_call.function.name,
                            "arguments": tool_call.function.arguments
                        }
                    }
                    serialized_tool_calls.append(serialized_tool_call)

            # Capture the entire AI's response, including any tool calls
            ai_response = {
                "role": "assistant",
                "content": response.choices[0].message.content,
                "tool_calls": serialized_tool_calls if serialized_tool_calls else None
            }

            # Append AI's entire response to conversation history
            conversation_history.append(ai_response)
            print("Received response from gpt-4-1106-preview model.")
            print("Conversation History (tool call response):", json.dumps(conversation_history, indent=2))

            # Handle tool calls and integrate responses into the conversation history
            if response.choices[0].message.tool_calls:
                print("Model has requested tool calls:", response.choices[0].message.tool_calls)
                tool_responses = handle_tool_calls(response.choices[0].message.tool_calls)

                for tool_response in tool_responses:
                    print("Processing tool response:", json.dumps(tool_response, indent=2))
                    
                    # Simplify the tool response
                    simplified_response_content = simplify_tool_response(tool_response)

                    print("Simplified tool response:", tool_response)

                    # Create a formatted response
                    formatted_tool_response = {
                        "tool_call_id": tool_response['tool_call_id'],
                        "role": "tool",
                        "name": tool_response['name'],
                        "content": simplified_response_content,
                        }

                    # Append the formatted response to the conversation history
                    conversation_history.append(formatted_tool_response)
                    print("Formatted Tool Response Added:", json.dumps(formatted_tool_response, indent=2))

                # Print the updated conversation history with tool responses
                print("Preparing to send updated payload back to gpt-4-1106-preview model with tool responses.")
                print("Updated Conversation History:", json.dumps(conversation_history, indent=2))

                # Send the updated conversation back to the model
                second_response = client.chat.completions.create(
                    model="gpt-4-1106-preview",
                    messages=conversation_history,
                    tools=tools,
                    max_tokens=4000
                )

                final_response_1106 = second_response.choices[0].message.content if second_response.choices else "No response received"
            
            else:
                print("No tool calls requested by the model.")
                final_response_1106 = response.choices[0].message.content
                print("Final Response from 1106 Model:", final_response_1106)
            
            # Print the final response
            print("Final Response:", final_response_1106)

            # Update Streamlit display with final response
            message_placeholder.markdown(final_response_1106)
            st.session_state['messages'].append({"type": "text", "content": final_response_1106})
            # Print updated session state
            print("Updated Session State (last 500 chars):", str(st.session_state['messages'])[-500:])
        
        except Exception as e:
            st.error(f"An error occurred: {e}")
            print(f"Exception occurred during model interaction: {e}")

# Optional: Button to reset the conversation
if st.button("Reset Conversation"):
    print("Resetting conversation.")
    st.session_state['messages'] = []