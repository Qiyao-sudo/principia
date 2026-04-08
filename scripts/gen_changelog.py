import os
import requests
from pathlib import Path

# 读取环境变量
API_KEY = os.getenv("DEEPSEEK_API_KEY")
API_URL = os.getenv("DEEPSEEK_API_ENDPOINT")
main_version = os.getenv("MAIN_VERSION")
sub_version = os.getenv("SUB_VERSION")
current_tag = os.getenv("CURRENT_TAG")

# 读取commit差异日志
with open("commit_diff.txt", "r", encoding="utf-8") as f:
    commit_content = f.read().strip()

# 构造专业Prompt，让DeepSeek输出标准结构化Changelog
prompt = f"""
你是一名软件开发文档工程师，请根据以下Git提交记录，生成一份规范、易读、结构化的版本更新日志Changelog：
要求：
1. 输出使用Markdown格式，适配App项目文档风格
2. 分类整理：新增功能、性能优化、Bug修复、代码重构、依赖更新
3. 语言简洁正式，剔除无效merge、wip提交描述
4. 头部标注主版本号、完整版本号、当前Tag、更新日期
5. 最终只输出纯Markdown正文，不要额外解释、不要开场白

基础信息：
主版本号：{main_version}
完整版本号：{sub_version}
Git Tag：{current_tag}
更新日期：{os.popen('date +%Y-%m-%d').read().strip()}

提交记录详情：
{commit_content}
"""

# 请求DeepSeek API
headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}
body = {
    "model": "deepseek-chat",
    "messages": [
        {"role": "user", "content": prompt}
    ],
    "temperature": 0.3  # 低随机性，保证文档稳定
}

resp = requests.post(API_URL, json=body, headers=headers, timeout=60)
resp.raise_for_status()
result = resp.json()
changelog_md = result["choices"][0]["message"]["content"]

# 创建目标目录：doc/{主版本号}/{版本号}/
save_dir = Path(f"doc/{main_version}/{sub_version}")
save_dir.mkdir(parents=True, exist_ok=True)

# 写入App.md文件
save_path = save_dir / "App.md"
with open(save_path, "w", encoding="utf-8") as f:
    f.write(changelog_md)

print(f"Changelog 已生成完毕，路径：{save_path}")