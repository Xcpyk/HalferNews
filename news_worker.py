"""
独立的抓取/翻译 worker，供生产环境用 systemd/pm2/supervisor 常驻执行。
用法：
  source venv/bin/activate
  python3 news_worker.py
环境变量：
  HTTP_PROXY / HTTPS_PROXY 可选，用于代理；不设置则直连
  INTERVAL_SECONDS 抓取间隔（默认 300 秒）
"""

import os
import time
from app import app, fetch_and_translate_news


def main():
    interval = int(os.getenv('INTERVAL_SECONDS', '300'))
    with app.app_context():
        while True:
            print('worker: 开始获取并翻译新闻...')
            try:
                fetch_and_translate_news()
            except Exception as e:
                print('worker: 抓取失败:', e)
            time.sleep(interval)


if __name__ == '__main__':
    main()


