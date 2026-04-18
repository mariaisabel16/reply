# test_aws_connection.py
import boto3
from botocore.exceptions import NoCredentialsError, PartialCredentialsError, ClientError

def test_aws_bedrock_connection(region_name="us-east-1"):
    """
    Überprüft die AWS-Konnektivität und den Zugriff auf Amazon Bedrock.

    Versucht, eine Liste der verfügbaren Foundation Models abzurufen.
    Gibt detailliertes Feedback basierend auf möglichen Fehlern.
    Dieser Test schlägt fehl, wenn die Verbindung nicht erfolgreich ist.
    """
    print("--- Starte AWS Bedrock Connection Test ---")
    print(f"Versuche, eine Verbindung zur Region '{region_name}' herzustellen...")

    try:
        # Erstelle einen Client für den Bedrock-Service (nicht bedrock-runtime)
        # Dieser Client wird für Verwaltungsaufgaben wie das Auflisten von Modellen verwendet.
        bedrock_client = boto3.client(
            service_name='bedrock',
            region_name=region_name
        )

        # Rufe die Liste der verfügbaren Foundation Models ab
        print("Rufe die Liste der Foundation Models ab...")
        response = bedrock_client.list_foundation_models()
        
        models = response.get('modelSummaries', [])
        
        if not models:
            print("\n[WARNUNG] Die Verbindung war erfolgreich, aber es wurden keine Foundation Models gefunden.")
            print("Mögliche Ursachen:")
            print("1. Du hast in der AWS Management Console unter 'Bedrock -> Model access' noch keinen Zugriff auf Modelle angefordert.")
            print("2. Die ausgewählte Region unterstützt möglicherweise die gewünschten Modelle nicht.")
            assert False, "Verbindung erfolgreich, aber keine Modelle mit Zugriffsberechtigung gefunden."

        print("\n[ERFOLG] AWS-Verbindung und Bedrock-Zugriff erfolgreich hergestellt!")
        print(f"Es wurden {len(models)} Modelle in der Region '{region_name}' gefunden.")
        
        # Gib eine kleine Auswahl der gefundenen Modelle aus
        print("\nEinige verfügbare Modelle:")
        for model in models[:5]:
            print(f"- ID: {model['modelId']}, Name: {model['modelName']}")
            
        print("\n------------------------------------------")
        print("Dein AWS-Setup scheint korrekt konfiguriert zu sein.")
        assert True # Test erfolgreich

    except (NoCredentialsError, PartialCredentialsError):
        print("\n[FEHLER] AWS-Anmeldeinformationen nicht gefunden oder unvollständig.")
        print("Bitte stelle sicher, dass du deine Credentials konfiguriert hast. Überprüfe:")
        print("1. Die Datei `~/.aws/credentials`.")
        print("2. Umgebungsvariablen (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY).")
        print("3. Führe 'aws configure' in deinem Terminal aus.")
        assert False, "AWS Credentials nicht gefunden."
        
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code")
        if error_code == 'AccessDeniedException':
            print(f"\n[FEHLER] Zugriff verweigert (AccessDeniedException).")
            print("Deine AWS-Credentials sind gültig, aber der zugehörige IAM-Benutzer/Rolle hat keine Berechtigung für Bedrock.")
            print("Stelle sicher, dass die IAM-Policy die Aktion 'bedrock:ListFoundationModels' erlaubt.")
            assert False, "Zugriff auf Bedrock verweigert (AccessDeniedException)."
        else:
            print(f"\n[FEHLER] Ein Client-Fehler ist aufgetreten: {e}")
            print("Überprüfe die AWS-Region und deine Service-Endpunkte.")
            assert False, f"Ein Client-Fehler ist aufgetreten: {e}"
        
