from groq import Groq

from app.core.config import settings


class LLMService:
    def __init__(self):
        if not settings.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY is not set in environment variables.")

        self.client = Groq(api_key=settings.GROQ_API_KEY)

    def generate_answer(self, question: str, matches: list[dict]) -> str:
        context_parts = []

        for i, match in enumerate(matches, start=1):
            context_parts.append(
                f"[Source {i}] File: {match['filename']} | Chunk: {match['chunk_index']}\n"
                f"{match['content']}"
            )

        context = "\n\n".join(context_parts)

        prompt = f"""
You are a helpful assistant for document question answering.

Answer the user's question using ONLY the provided context.
If the answer is not in the context, say:
"I could not find the answer in the uploaded documents."

Question:
{question}

Context:
{context}
"""

        response = self.client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": "You answer questions using only retrieved document context."
                },
                {
                    "role": "user",
                    "content": prompt
                },
            ],
            temperature=0.2,
        )

        return response.choices[0].message.content