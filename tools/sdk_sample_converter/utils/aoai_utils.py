from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import AzureOpenAI


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

    def convert_code(self, source_code: str, source_lang: str, target_lang: str, sdk_context: str) -> str:
        """
        Convert SDK code from source_lang to target_lang using GPT.
        The prompt is fully constructed here.
        """
        system_prompt = "You are a code conversion assistant."
        user_prompt = f"""
            Convert the following {source_lang} SDK test/sample code into {target_lang}.
            Requirements:
            - Use idiomatic {target_lang} syntax and naming.
            - Follow SDK patterns shown in the provided context.
            - Keep comments, structure, and logic equivalent.
            - Output only valid {target_lang} code (no markdown formatting).

            SDK context:
            {sdk_context}

            Source code:
            {source_code}
            """
        return self.chat(user_prompt, system_prompt)


