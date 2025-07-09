from flask import Flask, render_template, request
import requests
from models import db, NewsItem
from moonshot import MoonshotTranslator
from dotenv import load_dotenv
import os
import threading
from datetime import datetime
from custom_news import custom_news

load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///news.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# 创建数据库表
with app.app_context():
    db.create_all()

# Hacker News API配置
HN_API = "https://hacker-news.firebaseio.com/v0"
TOP_STORIES_URL = f"{HN_API}/topstories.json"
NEW_STORIES_URL = f"{HN_API}/newstories.json"
ITEM_URL = f"{HN_API}/item/"

# 初始化翻译器
translator = MoonshotTranslator()

# === 添加 PROXIES 配置 ===
PROXIES = {
    "http": "http://183.129.171.18:8080",
    "https": "http://183.129.171.18:8080"
}

def fetch_and_translate_news():
    """获取并翻译新闻的后台任务"""
    with app.app_context():
        # 获取最新和热门故事ID
        # 默认抓取最新和热门各30条，避免数据库缺失
        top_ids = requests.get(TOP_STORIES_URL, proxies=PROXIES, timeout=10).json()[:30]
        new_ids = requests.get(NEW_STORIES_URL, proxies=PROXIES, timeout=10).json()[:30]
        story_ids = list(dict.fromkeys(new_ids + top_ids))  # 保证唯一且顺序优先最新
        
        for story_id in story_ids:
            # 检查是否已在数据库中
            item = NewsItem.query.get(story_id)
            if not item:
                # 从HN API获取详情
                story_data = requests.get(f"{ITEM_URL}{story_id}.json", proxies=PROXIES, timeout=10).json()
                # 创建新记录
                item = NewsItem(
                    id=story_id,
                    original_title=story_data.get('title', ''),
                    original_url=story_data.get('url', ''),
                    score=story_data.get('score', 0),
                    time=story_data.get('time', 0)
                )
                db.session.add(item)
                db.session.commit()
            # 只有未翻译或翻译失败时才调用API
            if not item.translated_title or item.translation_status in [0, 3]:
                try:
                    # 更新状态为翻译中
                    item.translation_status = 1
                    db.session.commit()
                    # 调用翻译API
                    translated = translator.translate_title(item.original_title)
                    if translated:
                        item.translated_title = translated
                        item.translation_status = 2  # 标记为已翻译
                    else:
                        item.translation_status = 3  # 标记为翻译失败
                    db.session.commit()
                except Exception as e:
                    print(f"翻译新闻 {item.id} 失败: {e}")
                    item.translation_status = 3
                    db.session.commit()

@app.route('/')
def index():
    # 只渲染精选新闻，其他新闻由前端JS获取
    sort = request.args.get('sort', 'featured')
    if sort == 'featured':
        news_items = custom_news
        pagination = type('obj', (object,), {'pages': 1, 'has_prev': False, 'has_next': False, 'prev_num': 1, 'next_num': 1})()
        page = 1
    else:
        news_items = []
        pagination = None
        page = 1
    return render_template('index.html', news_items=news_items, pagination=pagination, page=page, sort=sort)

def run_background_task():
    """启动后台任务定时获取并翻译新闻"""
    import time
    while True:
        print("开始获取并翻译新闻...")
        fetch_and_translate_news()
        # 每5分钟更新一次
        time.sleep(300)

def datetimeformat_filter(ts):
    try:
        now = datetime.now()
        dt = datetime.fromtimestamp(int(ts))
        diff = (now - dt).total_seconds()
        if diff < 60:
            return f"{int(diff)}秒前"
        elif diff < 3600:
            return f"{int(diff//60)}分钟前"
        elif diff < 86400:
            return f"{int(diff//3600)}小时前"
        else:
            return dt.strftime('%Y年%m月%d日 %H:%M')
    except Exception:
        return ''

app.jinja_env.filters['datetimeformat'] = datetimeformat_filter

if __name__ == '__main__':
    # 启动后台任务线程
    bg_thread = threading.Thread(target=run_background_task, daemon=True)
    bg_thread.start()
    
    # 启动Flask应用
    app.run(host='0.0.0.0', port=5000, debug=True)