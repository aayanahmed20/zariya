import streamlit as st
from core.inference import chat
from core.memory import save_chat

st.title("Zariya – Offline AI Assistant")

user_input = st.text_input("Ask something:")

if user_input:
    response = chat(user_input)
    st.write(response)

    save_chat(user_input, response)
