from llama_cpp import Llama

llm = Llama(
    model_path="models/model.gguf",
    n_ctx=2048
)

SYSTEM_PROMPT = """
You are Zariya, an offline AI assistant.
You respond in English or simple Urdu depending on the user.
You are helpful and educational.
"""

def chat(user_input):
    prompt = SYSTEM_PROMPT + "\nUser: " + user_input + "\nAssistant:"
    
    output = llm(prompt, max_tokens=200)
    return output["choices"][0]["text"]
