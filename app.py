from flask import Flask, render_template, request, jsonify
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

# 简单的内存缓存（进程级，重启失效）
translate_cache = {}

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
    sort = request.args.get('sort', 'featured')
    if sort == 'featured':
        news_items = custom_news
        pagination = type('obj', (object,), {'pages': 1, 'has_prev': False, 'has_next': False, 'prev_num': 1, 'next_num': 1})()
        page = 1
    else:
        # 其他情况也返回空列表和空分页，防止模板报错
        news_items = []
        pagination = type('obj', (object,), {'pages': 1, 'has_prev': False, 'has_next': False, 'prev_num': 1, 'next_num': 1})()
        page = 1
    return render_template('index.html', news_items=news_items, pagination=pagination, page=page, sort=sort)

@app.route('/api/translate', methods=['POST'])
def api_translate():
    data = request.get_json()
    title = data.get('title', '')
    if not title:
        return jsonify({'translated': ''})
    # 缓存命中直接返回
    if title in translate_cache:
        return jsonify({'translated': translate_cache[title]})
    try:
        translated = translator.translate_title(title)
        translate_cache[title] = translated
        return jsonify({'translated': translated})
    except Exception as e:
        return jsonify({'translated': ''})

@app.route('/api/report_news', methods=['POST'])
def report_news():
    news_list = request.get_json() or []
    saved_ids = []
    for item in news_list:
        news_id = item.get('id')
        if not news_id:
            continue
        # 查找数据库是否已有
        news = NewsItem.query.get(news_id)
        if not news:
            # 翻译标题
            translated = translator.translate_title(item.get('title', ''))
            news = NewsItem(
                id=news_id,
                original_title=item.get('title', ''),
                translated_title=translated,
                original_url=item.get('url', ''),
                score=item.get('score', 0),
                time=item.get('time', 0),
                translation_status=2 if translated else 3
            )
            db.session.add(news)
            saved_ids.append(news_id)
        else:
            # 已有则可选择更新翻译（可选）
            pass
    db.session.commit()
    return jsonify({'saved': saved_ids, 'count': len(saved_ids)})

@app.route('/api/news')
def api_news():
    sort = request.args.get('sort', 'time')
    limit = int(request.args.get('limit', 20))
    query = NewsItem.query.filter(NewsItem.translated_title != None, NewsItem.translated_title != '')
    if sort == 'score':
        query = query.order_by(NewsItem.score.desc())
    else:
        query = query.order_by(NewsItem.time.desc())
    news = query.limit(limit).all()
    return jsonify([
        {
            'id': n.id,
            'title': n.original_title,
            'translated_title': n.translated_title,
            'url': n.original_url,
            'score': n.score,
            'time': n.time
        } for n in news
    ])

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