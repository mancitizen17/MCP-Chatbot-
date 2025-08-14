import streamlit as st
from llama_index.core.llms import ChatMessage
import logging
import time
from llama_index.llms.ollama import Ollama
import requests
import json

#Logging info for DEV environment
logging.basicConfig(level=logging.INFO)

# Initialize chat history in session state if not already present
if 'messages' not in st.session_state:
    st.session_state.messages = []

#Get the list of models deployed on Ollama
def get_models():
    response = requests.get("http://localhost:11434/api/tags")
    if response is not None:
        #print(response)
        response_bytes = response.content
        data_str = response_bytes.decode('utf-8')  # decode bytes to string
        data = json.loads(data_str)  # parse JSON from string
        models =  []
        for key, value in data.items():
             print(f"{key}: {value}")
             models_resp = data['models']
             for model in models_resp:
                 models.append(model['name'])
        return models
        print(f" Response Model names :"+str(models))

# Function to chat with LLM with streaming on selected a model
def prepare_chat(model, messages):
    try:
        # Initialize the language model with a timeout
        llm = Ollama(model=model, request_timeout=180.0) 
        # Stream chat responses from the model
        resp = llm.stream_chat(messages)
        response = ""
        response_placeholder = st.empty()
        # Append each piece of the response to the output
        for r in resp:
            response += r.delta
            response_placeholder.write(response)
        # Log the interaction details
        logging.info(f"Model: {model}, Messages: {messages}, Response: {response}")
        return response
    except Exception as e:
        # Log and re-raise any errors that occur
        logging.error(f"Error during streaming: {str(e)}")
        raise e

def main():
    st.set_page_config(page_title="Local LLM Chat", layout="wide")
    # Custom CSS styling
    st.markdown("""
        <style>
        .user-msg {
            background-color: #1e1e1e;  /* dark gray background */
            color: #d4f1f9;             /* light blue font */
            padding: 10px;
            border-radius: 8px;
            margin-bottom: 8px;
        }
            .assistant-msg {
            background-color: #2e2e2e;  /* slightly lighter dark background */
            color: #e0ffe0;             /* soft light green font */
            padding: 10px;
            border-radius: 8px;
            margin-bottom: 8px;
        }
            .chat-box {
            max-height: 500px;
            overflow-y: auto;
            padding-right: 10px;
        }
        </style>

    """, unsafe_allow_html=True)

    st.title("LLM Client Chat Interface")

    # Sidebar for model selection
    with st.sidebar:
        st.header("Model Selection")
        model = st.selectbox("Choose a model", get_models())
        logging.info(f"Selected Model: {model}")
        st.success(f"Current Model: {model}")

    st.divider()
    st.markdown("#### Chat History")

    chat_container = st.container()
    with chat_container:
        # Wrap chat messages inside a div with chat-box class for scrolling & height
        st.markdown('<div class="chat-box">', unsafe_allow_html=True)
        for message in st.session_state.messages:
            if message["role"] == "user":
                st.markdown(f"<div class='user-msg'><strong>User:</strong> {message['content']}</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div class='assistant-msg'><strong>Assistant:</strong> {message['content']}</div>", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # User input
    if prompt := st.chat_input("Type your message..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        logging.info(f"User input: {prompt}")

        with st.chat_message("assistant"):
            start_time = time.time()
            st.spinner("Generating response...")

            try:
                messages = [ChatMessage(role=msg["role"], content=msg["content"]) for msg in st.session_state.messages]
                response_message = prepare_chat(model, messages)
                duration = time.time() - start_time
                response_with_time = f"{response_message}\n\nTook {duration:.2f} seconds"
                st.session_state.messages.append({"role": "assistant", "content": response_with_time})
                logging.info(f"Response: {response_message}, Duration: {duration:.2f} s")

            except Exception as e:
                st.session_state.messages.append({"role": "assistant", "content": str(e)})
                st.error("❌ An error occurred while generating the response.")
                logging.error(f"Error: {str(e)}")

if __name__ == "__main__":
    main()