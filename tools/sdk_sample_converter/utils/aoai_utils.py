import json

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import AzureOpenAI
from pydantic import BaseModel


class FileCategories(BaseModel):
    helpers: list[str]
    samples: list[str]
    docs: list[str]
    other_files: list[str]

    def total_len(self) -> int:
        """Return total number of items across all lists."""
        return sum(len(v) for v in self.model_dump().values())

class AzureOpenAIAssistant:
    """Azure OpenAI Assistant client"""

    def __init__(
        self,
        aoai_end_point: str,
        aoai_api_version: str,
        deployment_name: str,
        aoai_api_key: str,
    ):
        if not aoai_end_point:
            raise ValueError("Azure OpenAI endpoint is required.")
        if not aoai_api_version:
            raise ValueError("Azure OpenAI API version is required.")

        if not aoai_api_key:
            print("Using Entra ID/AAD to authenticate...")
            token_provider = get_bearer_token_provider(
                DefaultAzureCredential(),
                "https://cognitiveservices.azure.com/.default",
            )
            self.client = AzureOpenAI(
                api_version=aoai_api_version,
                azure_endpoint=aoai_end_point,
                azure_ad_token_provider=token_provider,
            )
        else:
            print("Using API key to authenticate...")
            self.client = AzureOpenAI(
                api_version=aoai_api_version,
                azure_endpoint=aoai_end_point,
                api_key=aoai_api_key,
            )

        self.model = deployment_name

    def chat(self, user_prompt: str, system_prompt: str) -> str:
        """
        Send a chat prompt to Azure OpenAI and return the model response.

        Args:
            user_prompt (str): The main user instruction or text to send.
            system_prompt (str): The system message providing context or role.

        Returns:
            str: The model's textual response.
        """
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            if user_prompt:
                messages.append({"role": "user", "content": user_prompt})

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.0,
            )
            print(f"OpenAI Usage: {response.usage}")
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Error during chat completion: {e}")
            return ""
        
    def chat_with_structured_output(self, user_prompt: str, system_prompt: str, response_format: BaseModel) -> FileCategories:
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            if user_prompt:
                messages.append({"role": "user", "content": user_prompt})

            completion = self.client.chat.completions.parse(
                model=self.model,
                messages=messages,
                response_format=response_format,
            )
            response = completion.choices[0].message.parsed
            return response
        except Exception as e:
            print(f"Error during structured chat completion: {e}")
            return None

    def convert_code(self, source_code: str, source_lang: str, target_lang: str, sdk_context: str) -> str:
        """
        Convert SDK code from source_lang to target_lang using GPT.
        """
        system_prompt = """
            You are an expert Azure SDK sample and test translator.
            You deeply understand SDK design patterns, idioms, and testing conventions across languages
            (e.g., Python, Java, C#, JavaScript/TypeScript).

            Your task is to translate sample or test code between SDKs while preserving:
            - the intent, structure, and instructional flow of the original sample/test,
            - SDK semantics, client patterns, and setup/cleanup logic,
            - comments and docstrings that explain usage.

            You adapt idioms, syntax, and frameworks naturally for the target language.
            Output must be **only** valid source code in the target language, ready to run.
        """
        user_prompt = f"""
            Translate the following {source_lang} SDK sample or test into {target_lang}.

            Requirements:
            1. **SDK Semantics**
            - Use equivalent client setup, method calls, and configuration patterns in {target_lang}.
            - Adapt SDK namespaces, imports, and async/sync usage idiomatically.
            - Match error handling and resource management conventions for {target_lang}.

            2. **Testing & Sample Conventions**
            - If it's a *sample*, keep the instructional and step-by-step style.
            - If it's a *test*, adapt to the typical test framework used in {target_lang} (e.g., pytest, JUnit, MSTest).
            - Keep the logical flow identical.

            3. **Output Rules**
            - Output only {target_lang} source code (no markdown, explanations, or comments outside code).
            - Ensure the code is syntactically correct and runnable.

            ### SDK Context
            {sdk_context}

            ### Source Code ({source_lang})
            {source_code}
        """
        return self.chat(user_prompt, system_prompt)



    def classify_file_paths(self, file_paths: list[str], target_lang: str) -> FileCategories:
        """
        Classify repository file paths by their purpose.

        Args:
            file_paths (list[str]): List of file paths to classify.
            target_lang (str): Target SDK language.

        Returns:
            FileCategories: Classified file paths.
        """
        system_prompt = """
            You are a software repository analyst that classifies files by their purpose.

            Sort the given list of file paths into 4 groups:
            1. helpers: SDK/helper scripts (e.g., setup files, utilities)
            2. samples: Sample/test scripts (to convert)
            3. docs: Documentation files (README.md, .md, .rst, etc.)
            4. other_files: Other files (json, pdf, jpg, csv, etc.)
        """

        user_prompt = f"""
            You are classifying files from a SDK repository in another programming language that will be converted to {target_lang}.

            Here is the list of file paths to classify:
            {file_paths}
        """

        result = self.chat_with_structured_output(
            user_prompt=user_prompt.strip(),
            system_prompt=system_prompt.strip(),
            response_format=FileCategories,
        )

        return result