from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
import requests
from models import db, NewsItem, User, Favorite
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
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

db.init_app(app)

# 初始化Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = '请先登录后再访问此页面'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

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

# 网络请求配置
REQUEST_TIMEOUT = 15
MAX_RETRIES = 3

# 简单的内存缓存（进程级，重启失效）
translate_cache = {}

def fetch_and_translate_news():
    """获取并翻译新闻的后台任务"""
    with app.app_context():
        try:
            # 获取最新和热门故事ID
            # 默认抓取最新和热门各30条，避免数据库缺失
            top_response = requests.get(TOP_STORIES_URL, proxies=PROXIES, timeout=REQUEST_TIMEOUT)
            new_response = requests.get(NEW_STORIES_URL, proxies=PROXIES, timeout=REQUEST_TIMEOUT)
            
            if top_response.status_code != 200 or new_response.status_code != 200:
                print("获取新闻列表失败，跳过本次更新")
                return
                
            top_ids = top_response.json()[:30]
            new_ids = new_response.json()[:30]
            story_ids = list(dict.fromkeys(new_ids + top_ids))  # 保证唯一且顺序优先最新
            
            for story_id in story_ids:
                # 检查是否已在数据库中
                item = NewsItem.query.get(story_id)
                if not item:
                    try:
                        # 从HN API获取详情
                        story_response = requests.get(f"{ITEM_URL}{story_id}.json", proxies=PROXIES, timeout=REQUEST_TIMEOUT)
                        if story_response.status_code == 200:
                            story_data = story_response.json()
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
                    except Exception as e:
                        print(f"获取新闻 {story_id} 详情失败: {e}")
                        continue
                        
                # 只有未翻译或翻译失败时才调用API
                if item and (not item.translated_title or item.translation_status in [0, 3]):
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
                        if item:
                            item.translation_status = 3
                            db.session.commit()
        except Exception as e:
            print(f"后台任务执行失败: {e}")

@app.route('/')
def index():
    sort = request.args.get('sort', 'time')
    page = int(request.args.get('page', 1))
    per_page = 30
    
    if sort == 'favorites':
        if not current_user.is_authenticated:
            return redirect(url_for('login'))
        # 获取用户收藏的新闻
        favorites = Favorite.query.filter_by(user_id=current_user.id).order_by(Favorite.created_at.desc()).all()
        news_items = []
        for fav in favorites:
            news_item = NewsItem.query.get(fav.news_id)
            if news_item:
                news_items.append(news_item)
        
        # 手动分页
        total_items = len(news_items)
        total_pages = (total_items + per_page - 1) // per_page
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        news_items = news_items[start_idx:end_idx]
        
        pagination = type('obj', (object,), {
            'pages': total_pages,
            'has_prev': page > 1,
            'has_next': page < total_pages,
            'prev_num': page - 1 if page > 1 else 1,
            'next_num': page + 1 if page < total_pages else total_pages
        })()
    else:
        # 获取已翻译的新闻
        query = NewsItem.query.filter(NewsItem.translated_title != None, NewsItem.translated_title != '')
        if sort == 'score':
            query = query.order_by(NewsItem.score.desc())
        else:
            query = query.order_by(NewsItem.time.desc())
        
        # 计算分页
        total_items = query.count()
        total_pages = (total_items + per_page - 1) // per_page
        news_items = query.offset((page - 1) * per_page).limit(per_page).all()
        
        pagination = type('obj', (object,), {
            'pages': total_pages,
            'has_prev': page > 1,
            'has_next': page < total_pages,
            'prev_num': page - 1 if page > 1 else 1,
            'next_num': page + 1 if page < total_pages else total_pages
        })()
    
    return render_template('index.html', news_items=news_items, pagination=pagination, page=page, sort=sort)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # 验证输入
        if not username or not email or not password:
            flash('请填写所有必填字段', 'error')
            return render_template('register.html')
        
        if password != confirm_password:
            flash('两次输入的密码不一致', 'error')
            return render_template('register.html')
        
        # 检查用户名和邮箱是否已存在
        if User.query.filter_by(username=username).first():
            flash('用户名已存在', 'error')
            return render_template('register.html')
        
        if User.query.filter_by(email=email).first():
            flash('邮箱已被注册', 'error')
            return render_template('register.html')
        
        # 创建新用户
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        flash('注册成功！请登录', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            flash('登录成功！', 'success')
            return redirect(url_for('index'))
        else:
            flash('用户名或密码错误', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('已退出登录', 'info')
    return redirect(url_for('index'))

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
    limit = int(request.args.get('limit', 30))
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

@app.route('/api/favorite', methods=['POST'])
@login_required
def toggle_favorite():
    data = request.get_json()
    news_id = data.get('news_id')
    
    if not news_id:
        return jsonify({'success': False, 'message': '缺少新闻ID'})
    
    # 检查新闻是否存在
    news_item = NewsItem.query.get(news_id)
    if not news_item:
        return jsonify({'success': False, 'message': '新闻不存在'})
    
    # 检查是否已收藏
    existing_favorite = Favorite.query.filter_by(
        user_id=current_user.id, 
        news_id=news_id
    ).first()
    
    if existing_favorite:
        # 取消收藏
        db.session.delete(existing_favorite)
        db.session.commit()
        return jsonify({'success': True, 'favorited': False, 'message': '已取消收藏'})
    else:
        # 添加收藏
        favorite = Favorite(user_id=current_user.id, news_id=news_id)
        db.session.add(favorite)
        db.session.commit()
        return jsonify({'success': True, 'favorited': True, 'message': '已添加到收藏'})

@app.route('/api/favorites')
@login_required
def get_favorites():
    favorites = Favorite.query.filter_by(user_id=current_user.id).order_by(Favorite.created_at.desc()).all()
    news_items = []
    for fav in favorites:
        news_item = NewsItem.query.get(fav.news_id)
        if news_item:
            news_items.append({
                'id': news_item.id,
                'title': news_item.original_title,
                'translated_title': news_item.translated_title,
                'url': news_item.original_url,
                'score': news_item.score,
                'time': news_item.time,
                'favorited_at': fav.created_at.isoformat()
            })
    return jsonify(news_items)

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
    app.run(host='0.0.0.0', port=3000, debug=True)