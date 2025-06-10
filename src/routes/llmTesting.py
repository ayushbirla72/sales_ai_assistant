from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
import uvicorn
import os
from langchain.llms import LlamaCpp
from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferMemory

router = APIRouter()

# Initialize the LlamaCpp model with your Mistral 7B GGUF model path

MODEL_PATH = os.path.abspath("src/prediction_models/mistral-7b-instruct-v0.1.Q4_K_M.gguf")

llm = LlamaCpp(
    model_path=MODEL_PATH,
    n_ctx=4096,
    temperature=0.7,
    max_tokens=1024,
    n_threads=8,
    verbose=True,
)

# Dictionary to keep conversation chains by session_id (user)
conversations = {}

@router.post("/chat")
async def chat(request: Request):
    data = await request.json()
    session_id = data.get("session_id")
    user_message = data.get("message")

    if not session_id or not user_message:
        raise HTTPException(status_code=400, detail="Missing session_id or message")

    # Create conversation with memory if it doesn't exist
    if session_id not in conversations:
        memory = ConversationBufferMemory()
        conversations[session_id] = ConversationChain(llm=llm, memory=memory)

    conversation = conversations[session_id]

    # Run the conversation chain
    response = conversation.run(user_message)

    return JSONResponse(content={"response": response})

