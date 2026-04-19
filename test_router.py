import asyncio
from CampusPilot.QandA_Agent.agent import run_chat_turn

async def main():
    messages = [{"role": "user", "content": "Was passiert wenn ich eine Prüfung nicht bestehe?"}]
    print("Testing Router with general KB question...")
    reply, dbg = await run_chat_turn(messages)
    print("Reply:", reply)
    print("Debug:", dbg)

if __name__ == "__main__":
    asyncio.run(main())
