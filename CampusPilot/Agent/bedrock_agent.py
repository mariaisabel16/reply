import boto3
import json

class BedrockAgent:
    def __init__(self, region_name: str = "us-east-1", model_id: str = "anthropic.claude-3-haiku-20240307-v1:0", profile_name: str = None):
        """
        Initialisiert den Amazon Bedrock Client.
        Stelle sicher, dass du AWS-Credentials konfiguriert hast (z.B. via aws configure)
        und Zugriff auf das gewählte Modell in der AWS Console (Model access) freigeschaltet ist.
        """
        # Erstelle eine spezifische Session, falls ein Profilname übergeben wurde
        if profile_name:
            session = boto3.Session(profile_name=profile_name)
        else:
            session = boto3.Session()

        # Wir nutzen den bedrock-runtime Client für Inferenzen
        self.bedrock_client = session.client(
            service_name='bedrock-runtime',
            region_name=region_name
        )
        self.model_id = model_id

    def invoke(self, prompt, system_prompt=None, max_tokens=1000, temperature=0.7):
        """
        Sendet einen Prompt an das Bedrock Modell (hier optimiert für Claude 3).
        """
        messages = [
            {
                "role": "user",
                "content": prompt
            }
        ]
        
        body_dict = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": messages
        }
        
        # Falls ein System-Prompt verwendet werden soll
        if system_prompt:
            body_dict["system"] = system_prompt

        body = json.dumps(body_dict)

        try:
            response = self.bedrock_client.invoke_model(
                body=body,
                modelId=self.model_id,
                accept='application/json',
                contentType='application/json'
            )
            
            response_body = json.loads(response.get('body').read())
            return response_body['content'][0]['text']

        except Exception as e:
            print(f"Fehler bei der Kommunikation mit Bedrock: {e}")
            return None

# Beispielhafte Ausführung
if __name__ == "__main__":
    # Du kannst hier auch stärkere Modelle wie 'anthropic.claude-3-sonnet-20240229-v1:0' nutzen
    agent = BedrockAgent()
    
    system_instruction = "Du bist ein hilfsbereiter KI-Assistent für unser Hackathon-Projekt 'CampusPilot'."
    user_prompt = "Erkläre mir kurz, was Amazon Bedrock ist."
    
    print(f"User: {user_prompt}\n")
    
    response = agent.invoke(
        prompt=user_prompt, 
        system_prompt=system_instruction
    )
    
    if response:
        print(f"Agent:\n{response}")
