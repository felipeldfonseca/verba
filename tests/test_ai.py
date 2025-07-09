from openai import AzureOpenAI
import os
from dotenv import load_dotenv
from pathlib import Path

# --- Debugging Steps ---
print(f"Current working directory: {Path.cwd()}")
dotenv_path = Path.cwd() / '.env'
print(f"Checking for .env file at: {dotenv_path}")
if dotenv_path.exists():
    print("✅ .env file found.")
    load_dotenv(dotenv_path=dotenv_path)
else:
    print("❌ .env file NOT found.")
# --- End Debugging Steps ---

# Check if the key was loaded
api_key_loaded = os.getenv("AZURE_OPENAI_API_KEY")
if api_key_loaded:
    print("✅ AZURE_OPENAI_API_KEY loaded successfully.")
else:
    print("❌ AZURE_OPENAI_API_KEY not found in environment.")

client = AzureOpenAI(
    api_key       = api_key_loaded,
    azure_endpoint= os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_version   = "2024-05-15-preview",
)

print("\nAttempting to connect to Azure OpenAI...")

resp = client.chat.completions.create(
    model    = os.getenv("AZURE_OPENAI_DEPLOYMENT"),
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user",   "content": "Say hi in one word in Portuguese."},
    ],
)
print("\n🎉 Success! Response from model:")
print(resp.choices[0].message.content)
