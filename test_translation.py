#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
翻译质量测试脚本
用于测试优化后的新闻标题翻译效果
"""

import os
from dotenv import load_dotenv
from moonshot import MoonshotTranslator

# 加载环境变量
load_dotenv()

def test_translation_quality():
    """测试翻译质量"""
    
    # 测试用的英文新闻标题
    test_titles = [
        "Tesla deactivates Cybertruck in the middle of traffic after dispute with owner",
        "Cybertruck Leads Tesla's Used-Car Collapse",
        "Show HN: UwU – Generate CLI commands inline with GPT-5",
        "Ask HN: What's Your Take on Perplexity AI?",
        "Design for Women, by Women",
        "Sneaky Git Commits",
        "How to Save for a House: A Step-by-Step Guide",
        "The Future of AI in Healthcare: Opportunities and Challenges",
        "Breaking: Major Tech Company Announces Revolutionary New Product",
        "Why Remote Work is Here to Stay: A Comprehensive Analysis"
    ]
    
    # 初始化翻译器
    translator = MoonshotTranslator()
    
    print("=" * 80)
    print("新闻标题翻译质量测试")
    print("=" * 80)
    
    for i, title in enumerate(test_titles, 1):
        print(f"\n{i}. 原文: {title}")
        print("-" * 60)
        
        try:
            translated = translator.translate_title(title)
            if translated:
                print(f"翻译: {translated}")
                
                # 简单的质量检查
                if translated.lower().strip() == title.lower().strip():
                    print("⚠️  警告: 翻译结果与原文相同")
                elif len(translated) < 5:
                    print("⚠️  警告: 翻译结果过短")
                else:
                    print("✅ 翻译成功")
            else:
                print("❌ 翻译失败")
                
        except Exception as e:
            print(f"❌ 翻译异常: {e}")
        
        print("-" * 60)
    
    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)

if __name__ == "__main__":
    # 检查环境变量
    if not os.getenv("MOONSHOT_API_KEY"):
        print("错误: 请设置 MOONSHOT_API_KEY 环境变量")
        exit(1)
    
    if not os.getenv("MOONSHOT_API_BASE"):
        print("错误: 请设置 MOONSHOT_API_BASE 环境变量")
        exit(1)
    
    test_translation_quality()
