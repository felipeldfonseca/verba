from openai import AzureOpenAI
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

client = AzureOpenAI(
    api_key       = os.getenv("AZURE_OPENAI_API_KEY"),
    azure_endpoint= os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_version   = "2023-05-15",
)

resp = client.chat.completions.create(
    model    = os.getenv("AZURE_OPENAI_DEPLOYMENT"),
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user",   "content": "Say hi in one word in Portuguese."},
    ],
)
print(resp.choices[0].message.content)
