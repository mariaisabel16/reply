import asyncio
from CampusPilot.QandA_Agent.agent import run_chat_turn

async def main():
    messages = [{"role": "user", "content": "Wann startet die Vorlesungszeit im nächsten Semester?"}]
    print("Testing Router with NAT API question...")
    reply, dbg = await run_chat_turn(messages)
    print("\n\n--- REPLY ---")
    print(reply)
    print("\n\n--- DEBUG ---")
    for d in dbg:
        print(f"Tool used: {d['tool']}")

if __name__ == "__main__":
    asyncio.run(main())
