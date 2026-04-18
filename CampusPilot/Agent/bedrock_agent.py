import json

try:
    import boto3
except ImportError:
    boto3 = None

class BedrockAgent:
    def __init__(
        self,
        region_name: str = "eu-central-1",
        model_id: str = "anthropic.claude-3-haiku-20240307-v1:0", # Changed to Haiku for better availability
        profile_name: str | None = None,
    ):
        """
        Initializes an Amazon Bedrock client when boto3 and credentials are available.
        The rest of the hackathon workflow can still run without Bedrock.
        """
        self.model_id = model_id
        self.available = False
        self.bedrock_client = None
        self.init_error = None

        if boto3 is None:
            self.init_error = "boto3 is not installed."
            return

        try:
            session = boto3.Session(profile_name=profile_name) if profile_name else boto3.Session()
            self.bedrock_client = session.client(
                service_name="bedrock-runtime",
                region_name=region_name,
            )
            self.available = True
        except Exception as exc:
            self.init_error = str(exc)

    def invoke(self, prompt, system_prompt=None, max_tokens=1000, temperature=0.7):
        """
        Sends a prompt to Bedrock if available. Returns None when running in local fallback mode.
        """
        if not self.available or self.bedrock_client is None:
            return None

        # The request body format depends on the model provider.
        # This example is for Anthropic Claude models.
        messages = [{"role": "user", "content": prompt}]
        body_dict = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": messages,
        }

        if system_prompt:
            body_dict["system"] = system_prompt

        try:
            response = self.bedrock_client.invoke_model(
                body=json.dumps(body_dict),
                modelId=self.model_id,
                accept="application/json",
                contentType="application/json",
            )
            response_body = json.loads(response.get("body").read())
            return response_body["content"][0]["text"]
        except Exception as exc:
            # Return the specific exception to the caller for better error handling
            # This is better than just printing it.
            return f"Bedrock invocation failed: {exc}"


def main():
    """
    Tests access to a  Bedrock model to verify AWS setup.
    and test invoke method
    """
    agent = BedrockAgent()
    if agent.available:
        test_prompt = "Hello, Bedrock! nenn mir einen interessanten fakt"
        print(f"\nInvoking model with prompt: '{test_prompt}'")
        response = agent.invoke(test_prompt)
        if response:
            print(f"Model response: {response}")
        else:
            print("Failed to get a response from the model.")

if __name__ == "__main__":
    main()
