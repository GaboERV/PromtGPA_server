"""
Clientes LLM con patrón Adapter unificado por interfaz ILLMClient.
Patrón Factory para instanciar según configuración.

DEMO: las implementaciones tienen un modo "mock" cuando no hay API key,
para que el proyecto sea ejecutable sin credenciales.
"""
from abc import ABC, abstractmethod
import json
import os
import re
from typing import AsyncGenerator, Literal, Optional



class ILLMClient(ABC):
    @abstractmethod
    async def complete(self, system: str, user: str, max_tokens: int = 1024) -> tuple[str, int]:
        """Devuelve (texto, tokens_used)."""
        ...

    @abstractmethod
    async def stream(self, system: str, user: str, max_tokens: int = 1024) -> AsyncGenerator[str, None]:
        """Genera tokens en streaming."""
        ...


class MockLLMClient(ILLMClient):
    """Cliente de prueba. Devuelve respuestas fijas. Útil para tests y demo sin créditos."""

    async def complete(self, system: str, user: str, max_tokens: int = 1024) -> tuple[str, int]:
        prompt = user.lower()
        if "tarjetas de estudio" in prompt or "tarjetas" in prompt or "flashcards" in prompt or "cards" in prompt:
            count = 3
            match = re.search(r"genera\s+(\d+)\s+(tarjetas|flashcards|cards)", prompt)
            if match:
                count = int(match.group(1))
            prompt_text = prompt.split('prompt:')[-1].strip() if 'prompt:' in prompt else prompt.strip()
            prompt_text = prompt_text.replace('\n', ' ').strip()
            flashcards = [
                {
                    "question": f"¿Qué aspecto importante debes recordar de '{prompt_text[:50]}'?",
                    "answer": f"Una idea clave relacionada con el contexto y el prompt: {prompt_text[:80]}."
                }
                for i in range(1, count + 1)
            ]
            text = json.dumps(flashcards, ensure_ascii=False)
            return text, len(text.split())

        if "examen de práctica" in prompt or "opción múltiple" in prompt or "exam" in prompt:
            title = "Examen de práctica generado por el mock LLM"
            prompt_text = prompt.split('prompt:')[-1].strip() if 'prompt:' in prompt else prompt.strip()
            prompt_text = prompt_text.replace('\n', ' ').strip()
            questions = []
            respuestas = ["B", "C", "B"]
            for i in range(1, 4):
                questions.append({
                    "question_text": f"Según el prompt, ¿qué punto clave corresponde a la pregunta {i}?",
                    "opciones": {
                        "A": "Una opción distractora.",
                        "B": f"{prompt_text[:35]} es la respuesta más probable." if respuestas[i-1] == "B" else "Una alternativa secundaria.",
                        "C": f"{prompt_text[:35]} es la respuesta más probable." if respuestas[i-1] == "C" else "Una opción distractora.",
                        "D": "Otra idea irrelevante."
                    },
                    "correct_answer": respuestas[i-1]
                })
            text = json.dumps({"title": title, "questions": questions}, ensure_ascii=False)
            return text, len(text.split())

        prompt_text = user[:80]
        if "Mensaje actual del estudiante:" in user:
            prompt_text = user.split("Mensaje actual del estudiante:")[-1].strip()[:80]
            
        response = (
            f"[MOCK LLM] He recibido tu mensaje: '{prompt_text}...'. "
            "Esta es una respuesta simulada. Configura una API key real para conversar verdaderamente con el contenido."
        )
        return response, len(response.split())

    async def stream(self, system: str, user: str, max_tokens: int = 1024) -> AsyncGenerator[str, None]:
        text, _ = await self.complete(system, user, max_tokens)
        for word in text.split():
            yield word + " "


class ClaudeClient(ILLMClient):
    def __init__(self, api_key: str):
        try:
            from anthropic import AsyncAnthropic
            self.client = AsyncAnthropic(api_key=api_key)
        except ImportError:
            self.client = None

    async def complete(self, system: str, user: str, max_tokens: int = 1024) -> tuple[str, int]:
        if not self.client:
            return await MockLLMClient().complete(system, user, max_tokens)
        response = await self.client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        text = response.content[0].text if response.content else ""
        return text, response.usage.output_tokens

    async def stream(self, system: str, user: str, max_tokens: int = 1024) -> AsyncGenerator[str, None]:
        if not self.client:
            async for chunk in MockLLMClient().stream(system, user, max_tokens):
                yield chunk
            return
        async with self.client.messages.stream(
            model="claude-haiku-4-5-20251001",
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        ) as stream:
            async for text in stream.text_stream:
                yield text


class OpenAIClient(ILLMClient):
    def __init__(self, api_key: str):
        try:
            from openai import AsyncOpenAI
            self.client = AsyncOpenAI(api_key=api_key)
        except ImportError:
            self.client = None

    async def complete(self, system: str, user: str, max_tokens: int = 1024) -> tuple[str, int]:
        if not self.client:
            return await MockLLMClient().complete(system, user, max_tokens)
        response = await self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ],
            max_tokens=max_tokens,
        )
        text = response.choices[0].message.content if response.choices else ""
        tokens = response.usage.completion_tokens if response.usage else 0
        return text, tokens

    async def stream(self, system: str, user: str, max_tokens: int = 1024) -> AsyncGenerator[str, None]:
        if not self.client:
            async for chunk in MockLLMClient().stream(system, user, max_tokens):
                yield chunk
            return
        stream = await self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ],
            max_tokens=max_tokens,
            stream=True,
        )
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


class GeminiClient(ILLMClient):
    def __init__(self, api_key: str):
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            self.api_key = api_key
            self.is_configured = True
        except ImportError:
            self.is_configured = False

    async def complete(self, system: str, user: str, max_tokens: int = 1024) -> tuple[str, int]:
        if not self.is_configured:
            return await MockLLMClient().complete(system, user, max_tokens)
        try:
            import google.generativeai as genai
            from google.generativeai.types import HarmCategory, HarmBlockThreshold
            
            safety_settings = {
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            }
            model = genai.GenerativeModel('gemini-3.5-flash', system_instruction=system)
            response = await model.generate_content_async(
                user,
                safety_settings=safety_settings
            )
            
            if response.candidates:
                print(f"[Gemini Debug] Finish reason: {response.candidates[0].finish_reason}")
                
            tokens = response.usage_metadata.candidates_token_count if hasattr(response, 'usage_metadata') else len(response.text.split())
            return response.text, tokens
        except Exception as e:
            print(f"[Gemini Error]: {e}")
            return await MockLLMClient().complete(system, user, max_tokens)

    async def stream(self, system: str, user: str, max_tokens: int = 1024) -> AsyncGenerator[str, None]:
        if not self.is_configured:
            async for chunk in MockLLMClient().stream(system, user, max_tokens):
                yield chunk
            return
        try:
            import google.generativeai as genai
            from google.generativeai.types import HarmCategory, HarmBlockThreshold
            
            safety_settings = {
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            }
            model = genai.GenerativeModel('gemini-3.5-flash', system_instruction=system)
            response = await model.generate_content_async(
                user,
                generation_config=genai.types.GenerationConfig(max_output_tokens=max_tokens),
                safety_settings=safety_settings,
                stream=True
            )
            async for chunk in response:
                if chunk.text:
                    yield chunk.text
        except Exception as e:
            print(f"[Gemini Stream Error]: {e}")
            async for chunk in MockLLMClient().stream(system, user, max_tokens):
                yield chunk


class LLMClientFactory:
    """Patrón Factory para seleccionar el cliente LLM según configuración."""

    @staticmethod
    def create(provider: Optional[Literal["claude", "openai", "gemini"]] = None) -> ILLMClient:
        provider = provider or os.getenv("LLM_PROVIDER")

        if provider == "claude":
            if not os.getenv("ANTHROPIC_API_KEY"):
                return MockLLMClient()
            return ClaudeClient(os.getenv("ANTHROPIC_API_KEY"))
        elif provider == "openai":
            if not os.getenv("OPENAI_API_KEY"):
                return MockLLMClient()
            return OpenAIClient(os.getenv("OPENAI_API_KEY"))
        elif provider == "gemini":
            if not os.getenv("GOOGLE_API_KEY"):
                return MockLLMClient()
            return GeminiClient(os.getenv("GOOGLE_API_KEY"))
        else:
            return MockLLMClient()
