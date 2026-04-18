# workflow.py
import json
from bedrock_agent import BedrockAgent
from prompts import SYSTEM_PROMPT_AGENT_INTRODUCTION

def get_agent_introduction():
    """
    Initialisiert den CampusPilot-Agenten und lässt ihn seine Vorstellung generieren.

    Verwendet einen spezifischen System-Prompt, um dem Agenten seine Rolle und
    Fähigkeiten zuzuweisen und ihn zu bitten, sich vorzustellen.

    :return: Eine Zeichenkette mit der Vorstellung des Agenten oder eine Fehlermeldung.
    """
    print("Initialisiere den CampusPilot Agenten für die Vorstellung...")

    # Initialisiere den Agenten. Die Region und das Modell werden aus der
    # Standardkonfiguration der BedrockAgent-Klasse übernommen (eu-central-1, Claude 3 Haiku).
    agent = BedrockAgent()

    if not agent.available:
        error_message = f"Bedrock Agent konnte nicht initialisiert werden: {agent.init_error}"
        print(error_message)
        return error_message

    print("Agent initialisiert. Fordere Vorstellung vom LLM an...")

    # Ein einfacher Prompt, um den System-Prompt zu "triggern".
    user_prompt = "Stell dich bitte vor."

    # Rufe das LLM mit dem Rollen-definierenden System-Prompt auf.
    introduction = agent.invoke(
        prompt=user_prompt,
        system_prompt=SYSTEM_PROMPT_AGENT_INTRODUCTION
    )

    if not introduction or "Bedrock invocation failed" in introduction:
        error_message = f"Fehler: Konnte keine Vorstellung vom Agenten erhalten. Details: {introduction}"
        print(error_message)
        return error_message

    return introduction

if __name__ == "__main__":
    print("--- Starte CampusPilot Agenten-Vorstellungs-Workflow ---")
    
    # Rufe die Funktion auf, um die Vorstellung zu generieren
    agent_response = get_agent_introduction()
    
    print("\n" + "="*50)
    print("Antwort des CampusPilot Agenten:")
    print("="*50)
    print(agent_response)
    print("="*50)
    print("\nWorkflow beendet.")
