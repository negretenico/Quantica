from transformers import pipeline
from app.config import Config
import threading 
class HuggingFace:

    def __init__(self,token:str):
        self.generator =  pipeline(
    "text-generation",
model="google/gemma-2-2b",
    trust_remote_code=True,
    device_map="auto",
    use_auth_token=token
)
    def create_story(self,prompt, count):
        result = self.generator(prompt)
        story_md = result[0]['generated_text']
        return {"story_md": story_md, "meta": {"events_count": count}}