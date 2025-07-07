import os
import requests
from dotenv import load_dotenv

load_dotenv()

class MoonshotTranslator:
    def __init__(self):
        self.api_key = os.getenv("MOONSHOT_API_KEY")
        self.base_url = os.getenv("MOONSHOT_API_BASE")
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def translate_title(self, title):
        """使用Moonshot API翻译标题"""
        payload = {
            "model": "moonshot-v1-8k",  # 根据可用模型选择
            "messages": [
                {
                    "role": "system",
                    "content": "你是一名专业的新闻标题翻译员。请将英文新闻标题翻译成中文，优先保证可读性和流畅度，可以适当意译，不必逐字准确。直接返回最自然、易懂的中文标题，不要添加任何额外内容。"
                },
                {
                    "role": "user",
                    "content": f"翻译以下新闻标题：\n\n{title}"
                }
            ],
            "temperature": 0.3,  # 较低的temperature值保证翻译准确性
            "max_tokens": 100
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            return data['choices'][0]['message']['content'].strip()
        except requests.exceptions.RequestException as e:
            print(f"翻译请求失败: {e}")
            return None