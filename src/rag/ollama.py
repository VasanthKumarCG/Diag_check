import requests,json
from src.rag import settings
class Client:
 def embed(self,texts):
  if not settings.EMBED:raise RuntimeError('OLLAMA_EMBED_MODEL is not configured')
  r=requests.post(settings.BASE+'/api/embed',json={'model':settings.EMBED,'input':texts},timeout=180);r.raise_for_status();v=r.json()['embeddings']
  if any(len(x)!=settings.DIM for x in v):raise ValueError('Embedding dimension mismatch')
  return v
 def chat(self,payload):
  r=requests.post(settings.BASE+'/api/chat',json={'model':settings.CHAT,'messages':payload,'format':'json','stream':False},timeout=300);r.raise_for_status();return json.loads(r.json()['message']['content'])
