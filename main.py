import random
import textwrap
import os
import requests
import groq
import streamlit as st
import asyncio
from streamlit_local_storage import LocalStorage
from dotenv import load_dotenv
from presets.personas import personas

# Page layout
st.set_page_config(page_title="ITF Chatbot", page_icon="assets/logo-tm.svg", layout="wide")
with open('./assets/style.css') as f:
    st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

# Load environment variables
load_dotenv()

# init local storage
localS = LocalStorage()

async def init_local_storage():
    print("In init_local_storage")
    if localS.storedItems is None:
        localS.storedItems = [{}]

# ----
# Init session states from local storage
# ----
async def init_session_states():
    print("In init_session_states")
    if "groq_api_key" in localS.storedItems:
        groq_api_key = localS.getItem("groq_api_key")
    else:
        groq_api_key = os.getenv("GROQ_API_KEY") or None
        localS.setItem("groq_api_key", groq_api_key, key=str(random.random()))
    if "preferred_model" in localS.storedItems:
        preferred_model = localS.getItem("preferred_model")
    else:
        preferred_model = "llama-3.1-70b-versatile"
        localS.setItem("preferred_model", preferred_model, key=str(random.random()))
    if "my_name" in localS.storedItems:
        my_name = localS.getItem("my_name")
    else:
        my_name = "x"
        localS.setItem("my_name", my_name, key=str(random.random()))
    default_states = {
        "groq_api_key": groq_api_key,
        "preferred_model": preferred_model,
        "my_name": my_name,
        "all_models": [],
        "personality": "Default",
        "temperature": 0.2,
        "messages": []
    }
    for key, value in default_states.items():
        if key not in st.session_state:
            st.session_state[key] = value
    delete_O_keys()

async def fetch_models_from_groq():
    print("in fetch_models_from_groq")
    api_key = st.session_state.groq_api_key
    if not api_key:
        return []

    headers = {
        "Authorization": f"Bearer {api_key}"
    }
    try:
        response = requests.get("https://api.groq.com/openai/v1/models", headers=headers)
        response.raise_for_status()
        models_data = response.json()
        # Remove models that contains "whisper" or "guard" in their name
        filtered_models = [model["id"] for model in models_data["data"]
                           if "whisper" not in model["id"] and "guard" not in model["id"]]
        return filtered_models
    except requests.RequestException as e:
        st.error(f"Failed to fetch models: {str(e)}")
        return []

def delete_O_keys():
    for key in list(st.session_state.keys()):
        if key.startswith('0.'):
            del st.session_state[key]

# ----
# Functions
# ----
def update_delete_api_key(api_key):
    if api_key:
        st.session_state.groq_api_key = api_key
        localS.setItem("groq_api_key", api_key, key=str(random.random()))
    else:
        st.session_state.groq_api_key = None
        localS.setItem("groq_api_key", None, key=str(random.random()))


def update_local_storage():
    with st.container(height=20):
        localS.setItem("preferred_model", st.session_state.preferred_model, key=str(random.random()))
        localS.setItem("my_name", st.session_state.my_name, key=str(random.random()))
        localS.setItem("groq_api_key", st.session_state.groq_api_key, key=str(random.random()))
        # Delete all keys that starts with '0.' from the session state (local storage keys start with '0.')
    #     for key in list(st.session_state.keys()):
    #         if key.startswith('0.'):
    #             del st.session_state[key]
    # update_local_storage()


def update_session_states():
    prefix = f"Hello, I'm {st.session_state.my_name}. " if st.session_state.my_name != "" else ""
    sys_prompt = prefix + personas[st.session_state.personality]
    if len(st.session_state.messages) > 0:
        st.session_state.messages[0]["content"] = sys_prompt
    else:
        st.session_state.messages = [{"role": "system", "content": sys_prompt}]
        st.session_state.messages.append({"role": "assistant", "content": "How can I help you?"})
    update_local_storage()


def stream_response(completion):
    for chunk in completion:
        if chunk.choices[0].delta.content is not None:
            yield chunk.choices[0].delta.content


async def main():
    print("In main")
    await init_local_storage()
    await init_session_states()
    # await fetch_models_from_groq()

    # Sidebar
    with st.sidebar:
        st.title("Chat Settings")

        # API Key input
        api_key = st.session_state.groq_api_key
        if api_key is None:
            new_api_key = st.text_input("Enter Groq API Key", type="password")
            if new_api_key:
                update_delete_api_key(new_api_key)
                st.success("API Key is set")
        else:
            if st.button("Clear API Key"):
                update_delete_api_key(None)
                st.rerun()

        # Models selection
        st.session_state.all_models = await fetch_models_from_groq()
        try:
            index = st.session_state.all_models.index(st.session_state.preferred_model)
        except ValueError:
            index = 0
        st.session_state.preferred_model = st.selectbox("Select Preferred Model", st.session_state.all_models,
                                                        index=index,
                                                        on_change=update_session_states)
        # Personalities selection
        st.session_state.personality = st.selectbox("Select Personality", list(personas.keys()),
                                                    on_change=update_session_states)
        st.session_state.my_name = st.text_input("Enter your name", value=st.session_state.my_name,
                                                 on_change=update_session_states)
        # Temperature slider
        st.session_state.temperature = st.slider("Temperature", 0.0, 2.0, st.session_state.temperature, 0.3)
        # Clear chat history button
        if st.button("Clear Chat History", type="primary"):
            st.session_state.messages = []
            update_session_states()

    # Main chat interface
    with open('assets/logo-tm.svg') as f:
        st.markdown(f'<div id="main_header">{f.read()}<p>ITF Chatbot <span>(v2.0)</span></p></div>',
                    unsafe_allow_html=True)

    # Display a warning if API key is not set
    if st.session_state.groq_api_key is None:
        st.error("""
      Please enter your Groq API key in the sidebar to start chatting.   
      - Login to [Groq](https://groq.com).
      - Go to [API Keys](https://console.groq.com/keys).
      - Create a new API key and enjoy chatting with Groq ;-)
      - And best of all, it's **totally free**! 🎉
      """)
    else:
        # Show chat history
        for msg in st.session_state.messages:
            st.chat_message(msg["role"]).write(msg["content"])
        # Set Groq client
        client = groq.Groq(
            api_key=st.session_state.groq_api_key,
        )
        # New prompt entered
        if prompt := st.chat_input():
            st.session_state.messages.append(
                {"role": "user", "content": prompt}
            )
            st.chat_message("user").write(prompt)
            completion = client.chat.completions.create(
                model=st.session_state.preferred_model,
                temperature=st.session_state.temperature,
                stream=True,
                max_tokens=4096,
                messages=st.session_state.messages
            )
            # Stream completion
            with st.chat_message("assistant"):
                response = st.write_stream(stream_response(completion))
            # Add completion to messages
            st.session_state.messages.append({"role": "assistant", "content": response})

    # Debug: Display session state
    st.write(st.session_state)


if __name__ == "__main__":
    asyncio.run(main())
