from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 关联收藏
    favorites = db.relationship('Favorite', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'

class NewsItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)  # Hacker News ID
    original_title = db.Column(db.String(500))
    translated_title = db.Column(db.String(500))
    original_url = db.Column(db.String(500))
    score = db.Column(db.Integer)  # 新闻评分
    time = db.Column(db.Integer)   # 发布时间戳
    
    # 翻译状态: 0=未翻译, 1=翻译中, 2=已翻译, 3=翻译失败
    translation_status = db.Column(db.Integer, default=0)
    
    # 关联收藏
    favorites = db.relationship('Favorite', backref='news_item', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<News {self.id}: {self.original_title}>'

class Favorite(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    news_id = db.Column(db.Integer, db.ForeignKey('news_item.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 确保用户不能重复收藏同一条新闻
    __table_args__ = (db.UniqueConstraint('user_id', 'news_id', name='_user_news_uc'),)
    
    def __repr__(self):
        return f'<Favorite {self.user_id}-{self.news_id}>'