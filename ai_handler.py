from groq import Groq
import os
from dotenv import load_dotenv

load_dotenv()

def get_ai_advice(product_url, price, title=None):
    """
    Uses the Groq API (llama-3.1 model) to analyze the product deal.
    Provides a 3-line concise summary in English for the user.
    """
    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
    product_name = title if title else product_url
    prompt = f"Product: {product_name}. Price: ${price}. Write 3 lines in English: Name, Price quality, Recommendation. Don't repeat the prompt."

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"AI Error: {e}"