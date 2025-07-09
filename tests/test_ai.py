from openai import AzureOpenAI
import os

client = AzureOpenAI(
    api_key       = os.getenv("AZURE_OPENAI_KEY"),
    azure_endpoint= os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_version   = "2024-05-15-preview",
)

resp = client.chat.completions.create(
    model    = os.getenv("AZURE_OPENAI_DEPLOYMENT"),
    messages = [
        {"role": "system", "content": "Você é útil."},
        {"role": "user",   "content": "Diga oi em português bem curto."},
    ],
)
print(resp.choices[0].message.content)   # → “Oi!”
