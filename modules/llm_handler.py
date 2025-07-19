# llm_handler.py

from typing import List, Union
from pydantic import BaseModel
import os
import instructor
from openai import OpenAI
from groq import Groq
from ollama import chat as ollama_chat, embeddings as ollama_embeddings
from dotenv import load_dotenv

load_dotenv()

class LLMHandler:
    def __init__(self, provider: str, model: str):
        self.provider = provider.lower()
        self.model = model
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.groq_api_key = os.getenv("GROQ_API_KEY")

        if self.provider == "openai":
            self.client = OpenAI(api_key=self.openai_api_key)
        elif self.provider == "groq":
            self.client = Groq(api_key=self.groq_api_key)
            self.schemed_client = instructor.from_groq(Groq(api_key=self.groq_api_key))
        elif self.provider == "ollama":
            self.client = None  # native methods
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

    def _validate(self, response: str, schema: BaseModel) -> Union[BaseModel, str]:
        try:
            return schema.model_validate_json(response)
        except Exception as e:
            print(f"Schema validation failed: {e}")
            return response

    def _format_messages(self, messages_or_prompt: Union[str, List[dict]]) -> List[dict]:
        """
        Accepts either a string prompt or a list of messages and returns a well-formed message list.
        """
        if isinstance(messages_or_prompt, str):
            return [{"role": "user", "content": messages_or_prompt}]
        elif isinstance(messages_or_prompt, list):
            return messages_or_prompt
        else:
            raise ValueError("Input must be a prompt string or a list of message dictionaries.")

    def stream(self, messages_or_prompt: Union[str, List[dict]], temperature: float = 0.7):
        messages = self._format_messages(messages_or_prompt)

        if self.provider == "openai":
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    stream=True
                )
                for chunk in response:
                    # Extract the content delta if available
                    delta = chunk.choices[0].delta.content
                    if delta:
                        yield {"content": delta}  # Stream the delta as a dictionary
                    else:
                        yield {"content": ""}  # Send an empty string if no delta
            except Exception as e:
                yield {"error": f"Streaming error (OpenAI): {e}"}

        elif self.provider == "ollama":
            try:
                response = ollama_chat(
                    model=self.model,
                    messages=messages,
                    stream=True,
                    options={"temperature": temperature}
                )
                for chunk in response:
                    yield {"content": chunk.message.content or ""}
            except Exception as e:
                yield {"error": f"Streaming error (Ollama): {e}"}

        elif self.provider == "groq":
            try:
                with self.client.chat.completions.with_streaming_response.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature
                ) as response:
                    for line in response.iter_lines():
                        if line:
                            yield {"content": line}  # No .decode() needed
            except Exception as e:
                yield {"error": f"Streaming error (Groq): {e}"}

        else:
            yield {"error": f"Streaming not supported for provider: {self.provider}"}


    def call(self, messages_or_prompt: Union[str, List[dict]], temperature: float = 0.7) -> str:
        messages = self._format_messages(messages_or_prompt)

        if self.provider == "openai":
            return self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature
            ).choices[0].message.content

        elif self.provider == "groq":
            return self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature
            ).choices[0].message.content

        elif self.provider == "ollama":
            return ollama_chat(
                model=self.model,
                messages=messages,
                options={"temperature": temperature}
            ).message.content

        else:
            raise ValueError("Unsupported provider")


    def call_schema(self, messages: List, schema: BaseModel, temperature: float = 0.7) -> Union[BaseModel, str]:
        if self.provider == "openai":
            response = self.client.beta.chat.completions.parse(
                model=self.model,
                messages=messages,
                temperature=temperature,
                response_format=schema
            ).choices[0].message.content
        elif self.provider == "groq":
            response = self.schemed_client.chat.completions.create(
                model=self.model,
                messages=messages,
                response_model=schema
            ).model_dump_json()
        elif self.provider == "ollama":
            response = ollama_chat(
                model=self.model,
                messages=messages,
                format=schema.model_json_schema(),
                options={"temperature": temperature}
            ).message.content
        else:
            raise ValueError("Unsupported provider")

        return self._validate(response, schema)
    
    def call_schema_prompt(self, prompt: str, schema: BaseModel, temperature: float = 0.7) -> Union[BaseModel, str]:
        messages = [{"role": "user", "content": prompt}]
        if self.provider == "openai":
            response = self.client.beta.chat.completions.parse(
                model=self.model,
                messages=messages,
                temperature=temperature,
                response_format=schema
            ).choices[0].message.content
        elif self.provider == "groq":
            response = self.schemed_client.chat.completions.create(
                model=self.model,
                messages=messages,
                response_model=schema
            ).model_dump_json()
        elif self.provider == "ollama":
            response = ollama_chat(
                model=self.model,
                messages=messages,
                format=schema.model_json_schema(),
                options={"temperature": temperature}
            ).message.content
        else:
            raise ValueError("Unsupported provider")

        return self._validate(response, schema)

    def call_json(self, messages_or_prompt: Union[str, List[dict]], temperature: float = 0.7) -> Union[str, dict]:
        messages = self._format_messages(messages_or_prompt)

        if self.provider == "openai":
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                response_format={"type": "json_object"}
            )
            return response.choices[0].message.content
        elif self.provider == "ollama":
            return ollama_chat(
                model=self.model,
                messages=messages,
                format="json",
                options={"temperature": temperature}
            ).message.content
        else:
            raise ValueError("JSON format not supported for this provider")


    def embed(self, text: str) -> List[float]:
        if self.provider == "openai":
            return self.client.embeddings.create(
                model=self.model,
                input=text
            ).data[0].embedding
        elif self.provider == "ollama":
            return ollama_embeddings(
                model=self.model,
                prompt=text
            ).embedding
        else:
            raise ValueError("Embeddings not supported for this provider")