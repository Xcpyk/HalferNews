from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class NewsItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)  # Hacker News ID
    original_title = db.Column(db.String(500))
    translated_title = db.Column(db.String(500))
    original_url = db.Column(db.String(500))
    score = db.Column(db.Integer)  # 新闻评分
    time = db.Column(db.Integer)   # 发布时间戳
    
    # 翻译状态: 0=未翻译, 1=翻译中, 2=已翻译, 3=翻译失败
    translation_status = db.Column(db.Integer, default=0)
    
    def __repr__(self):
        return f'<News {self.id}: {self.original_title}>'