import os
from llama_cpp import Llama

MODEL_PATH = os.path.abspath("src/prediction_models/mistral-7b-instruct-v0.1.Q4_K_M.gguf")

# Load the model
llm = Llama(
    model_path=MODEL_PATH,
    n_ctx=4096,  # context size
    n_threads=8,  # adjust for your CPU
)

# Define the prompt
# prompt = """<s>[INST] Summarize this meeting transcript:

# Alice: We should focus on finalizing the prototype.
# Bob: Agreed. I’ll update the backend by Wednesday.
# Charlie: I’ll handle the UI testing.
# David: And I’ll prepare the pitch for the client meeting.

# [/INST]"""

# # Run the model
# output = llm(prompt, max_tokens=300, stop=["</s>"])

# # Print the response
# print(output["choices"][0]["text"])


def run_instruction(task: str, content: str, max_tokens: int = 300) -> str:
    prompt = f"<s>[INST] {task}:\n\n{content}\n\n[/INST]"
    output = llm(prompt, max_tokens=max_tokens, stop=["</s>"])
    return output["choices"][0]["text"].strip()
