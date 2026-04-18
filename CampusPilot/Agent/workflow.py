# workflow.py
import json
import os

# Annahme: bedrock_agent.py und prompts.py befinden sich im selben Verzeichnis
from bedrock_agent import BedrockAgent
from prompts import (
    SYSTEM_PROMPT_EXTRACT_USER_INFO, 
    USER_PROMPT_TEMPLATE_EXTRACT_USER_INFO,
    SYSTEM_PROMPT_DETERMINE_INTENT,
    SYSTEM_PROMPT_GENERATE_FEEDBACK
)

# --- Platzhalter für Vektordatenbank-Interaktion ---
def save_to_vector_db(user_id, extracted_data):
    """
    Platzhalter-Funktion zum Speichern von Daten in einer Vektordatenbank.
    """
    print("--- Vektordatenbank-Speicherung (simuliert) ---")
    print(f"Speichere Daten für User-ID: {user_id}")
    # In einer echten Implementierung würden hier Embeddings erzeugt.
    print("-------------------------------------------------")
    return True

# --- Workflow Komponenten ---

def determine_intent(agent, user_profile, user_query):
    """
    Bestimmt die Absicht des Nutzers basierend auf seinem Profil und der Anfrage.
    """
    print("Bestimme Nutzer-Intent...")
    prompt = f"User Profile: {json.dumps(user_profile)}\nUser Query: {user_query}"
    intent_str = agent.invoke(prompt=prompt, system_prompt=SYSTEM_PROMPT_DETERMINE_INTENT)
    try:
        return json.loads(intent_str)
    except:
        return {"intent": "unknown", "parameters": {}}

def execute_action(intent_data):
    """
    Führt eine Aktion basierend auf dem erkannten Intent aus (Action over Conversation).
    """
    intent = intent_data.get("intent")
    params = intent_data.get("parameters", {})
    print(f"--- Führe Aktion aus: {intent} mit Parametern {params} ---")
    # Simulation von Tool-Checkouts oder Datenbank-Updates
    return {"status": "success", "action_performed": intent}

def generate_feedback(agent, action_result, user_query):
    """
    Erstellt eine finale Rückmeldung für den Nutzer.
    """
    print("Generiere Feedback...")
    prompt = f"Action Result: {json.dumps(action_result)}\nOriginal Query: {user_query}"
    return agent.invoke(prompt=prompt, system_prompt=SYSTEM_PROMPT_GENERATE_FEEDBACK)

# --- Haupt-Workflow-Funktion ---
def process_and_store_user_info(user_data_json_string, user_id="user_123"):
    """
    Verarbeitet einen JSON-String mit Nutzerdaten, extrahiert relevante Informationen
    mithilfe eines LLM und speichert sie in einer Vektordatenbank.
    """
    print("Starte Workflow: Extrahiere und speichere Nutzerinformationen...")
    agent = BedrockAgent()

    user_prompt = USER_PROMPT_TEMPLATE_EXTRACT_USER_INFO.format(
        user_data_json=user_data_json_string
    )

    extracted_info_str = agent.invoke(
        prompt=user_prompt,
        system_prompt=SYSTEM_PROMPT_EXTRACT_USER_INFO
    )

    if not extracted_info_str:
        return None

    try:
        extracted_info_json = json.loads(extracted_info_str)
        save_to_vector_db(user_id, extracted_info_json)
        return extracted_info_json
    except Exception as e:
        print(f"Fehler bei der Verarbeitung: {e}")
        return None

def run_agent_interaction(user_id, user_query, user_profile):
    """
    Der vollständige "Chief of Staff" Cycle: Intent -> Action -> Feedback.
    """
    agent = BedrockAgent()
    
    # 1. Intent Determination
    intent_data = determine_intent(agent, user_profile, user_query)
    
    # 2. Action Execution
    action_result = execute_action(intent_data)
    
    # 3. Feedback Generation
    feedback = generate_feedback(agent, action_result, user_query)
    
    return feedback

# --- Beispielhafte Ausführung ---
if __name__ == "__main__":
    base_path = "TemporaryUserInfoFiles"
    mock_files = ["MockUser.json", "MockModules.json", "MockStudy_plan.json"]
    combined_data = {}
    
    try:
        for file_name in mock_files:
            file_path = os.path.join(os.path.dirname(__file__), base_path, file_name)
            with open(file_path, "r") as f:
                combined_data[file_name] = json.load(f)
            
        sample_data_string = json.dumps(combined_data, indent=2)
        user_id = "TUM_12345678"
        
        # Phase 1: Profiling
        profile = process_and_store_user_info(sample_data_string, user_id=user_id)
        
        if profile:
            print("\nProfil erfolgreich erstellt. Starte Test-Anfrage...")
            # Phase 2: Action-Cycle
            query = "Welche Wahlpflichtfächer passen zu meinen Interessen in Machine Learning für das nächste Semester?"
            response = run_agent_interaction(user_id, query, profile)
            print(f"\nAgent Antwort:\n{response}")
            
    except Exception as e:
        print(f"Fehler im Workflow: {e}")
