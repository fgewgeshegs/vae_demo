import asyncio, sys
sys.stdout = open(r'D:\jay_demo\vae_demo\backend\import_kb2.log', 'w', encoding='utf-8')
sys.stderr = sys.stdout
from knowledge_base.import_local_kb import import_chunks
asyncio.run(import_chunks())
