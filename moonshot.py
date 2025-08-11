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
                    "content": """你是一名资深的新闻标题翻译专家，具有丰富的中英文表达经验。请将英文新闻标题翻译成地道、流畅的中文标题。

翻译原则：
1. **可读性优先**：确保中文标题读起来自然流畅，符合中文表达习惯
2. **信息准确**：保持原文核心信息完整，但可以适当意译和调整语序
3. **语言地道**：使用符合中文新闻标题的表达方式，避免生硬的直译
4. **简洁明了**：保持标题简洁有力，避免冗长表达
5. **文化适应**：考虑中文读者的阅读习惯和文化背景

翻译技巧：
- 将英文的被动语态转换为中文的主动表达
- 适当调整语序，让中文更符合逻辑
- 使用中文常见的新闻标题表达方式
- 对于专业术语，优先使用中文读者熟悉的表达
- 保持标题的吸引力和新闻价值

请直接返回最自然、最易读的中文标题，不要添加任何解释、标点符号或额外内容。"""
                },
                {
                    "role": "user",
                    "content": f"请翻译以下英文新闻标题：\n\n{title}"
                }
            ],
            "temperature": 0.2,  # 降低temperature值，提高翻译一致性和准确性
            "max_tokens": 150
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=payload,
                timeout=15  # 增加超时时间，确保翻译质量
            )
            response.raise_for_status()
            
            data = response.json()
            translated_title = data['choices'][0]['message']['content'].strip()
            
            # 清理翻译结果，移除可能的标点符号和多余内容
            translated_title = translated_title.replace('"', '').replace('"', '').replace('"', '').replace('"', '')
            translated_title = translated_title.replace('《', '').replace('》', '')
            translated_title = translated_title.replace('【', '').replace('】', '')
            
            return translated_title
        except requests.exceptions.RequestException as e:
            print(f"翻译请求失败: {e}")
            return None