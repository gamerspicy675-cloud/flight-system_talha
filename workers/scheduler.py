import asyncio
from workers.hold_releaser import sweep_expired_holds
from workers.waitlist_promoter import promote_waitlist

async def run_loop():
    print("[SCHEDULER] Background worker loop started...")
    while True:
        try:
            await sweep_expired_holds()
            await promote_waitlist()
        except Exception as e:
            print(f"[SCHEDULER ERROR] {e}")
        await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(run_loop())