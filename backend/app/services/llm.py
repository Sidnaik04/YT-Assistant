import os
import tiktoken
from dotenv import load_dotenv
from openai import OpenAI
import google.generativeai as genai

load_dotenv()

openai_client = OpenAI(
    api_key=os.getenv("GEMINI_API_KEY"),
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
)


# split text into token-based chunks
def chunk_text(text, model="gemini-2.5-flash", max_tokens=2000):
    enc = tiktoken.get_encoding("cl100k_base")
    tokens = enc.encode(text)
    chunks = []

    for i in range(0, len(tokens), max_tokens):
        chunk = tokens[i : i + max_tokens]
        chunks.append(enc.decode(chunk))
    return chunks


# summarize using gemini
def summarize_with_gemini(text):
    prompt = f"Summarize the following transcript concisely:\n\n{text}"

    completion = openai_client.chat.completions.create(
        model="gemini-2.5-flash", messages=[{"role": "user", "content": prompt}]
    )

    return completion.choices[0].message.content
