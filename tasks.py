from celery import Celery
from models import db, NewsItem
import requests
import os

# 使用Redis作为Celery后端
celery = Celery('tasks', broker='redis://localhost:6379/0')

# 翻译API配置（以百度翻译API为例）
BAIDU_API_URL = "https://fanyi-api.baidu.com/api/trans/vip/translate"
APP_ID = os.getenv('BAIDU_APP_ID')  # 从环境变量获取
APP_KEY = os.getenv('BAIDU_APP_KEY')

@celery.task
def translate_text(news_id):
    with db.app.app_context():
        item = NewsItem.query.get(news_id)
        if not item or item.translated_title:
            return
        
        # 调用翻译API
        params = {
            'q': item.original_title,
            'from': 'en',
            'to': 'zh',
            'appid': APP_ID,
            'salt': '1435660288',
            'sign': generate_sign(item.original_title, APP_ID, APP_KEY)
        }
        
        response = requests.get(BAIDU_API_URL, params=params)
        translation = response.json()
        
        if 'trans_result' in translation:
            item.translated_title = translation['trans_result'][0]['dst']
            db.session.commit()

def generate_sign(text, app_id, app_key):
    import hashlib
    import random
    salt = random.randint(32768, 65536)
    sign_str = app_id + text + str(salt) + app_key
    return hashlib.md5(sign_str.encode()).hexdigest()