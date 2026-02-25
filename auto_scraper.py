import os
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
import json
from supabase import create_client, Client

# ==========================================
# 🌸 幽灵暗哨：全自动化 OSINT 抓取引擎
# ==========================================

# 1. 从云端环境变量获取密钥（而不是 Streamlit Secrets）
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")

if not all([SUPABASE_URL, SUPABASE_KEY, DEEPSEEK_API_KEY]):
    print("🚨 致命错误：环境变量缺失，无人机启动失败！")
    exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# 2. 目标频道清单（必须与主大厅保持同步）
channel_urls = [
    "https://t.me/s/ejdailyru","https://t.me/s/Ateobreaking", "https://t.me/s/theinsider", "https://t.me/s/moscowtimes_ru",
    "https://t.me/s/economica","https://t.me/s/rybar_africa","https://t.me/s/zakupki_time","https://t.me/s/truestorymedia",
    "https://t.me/s/AoMurmansk","https://t.me/s/moscow_laundry","https://t.me/s/svtvnews","https://t.me/s/notes_veterans",
    "https://t.me/s/militarysummary","https://t.me/s/Tolo_news","https://t.me/s/kremlin_sekret","https://t.me/s/dva_majors",
    "https://t.me/s/caucasar","https://t.me/s/rybar","https://t.me/s/olen_nn","https://t.me/s/russicaRU",
    "https://t.me/s/topwar_official","https://t.me/s/RusskajaIdea","https://t.me/s/riakatysha","https://t.me/s/rybar_latam",
    "https://t.me/s/zhivoff","https://t.me/s/anserenko","https://t.me/s/wolframiumZ","https://t.me/s/vatnoeboloto","https://t.me/s/romanromachev",
    "https://t.me/s/thehegemonist","https://t.me/s/budni_manipulyatora","https://t.me/s/ManoiloToday","https://t.me/s/rtechnocom",
    "https://t.me/s/darpaandcia","https://t.me/s/istories_media","https://t.me/s/mediazona_exclusive","https://t.me/s/Russian_OSINT",
    "https://t.me/s/alter_academy","https://t.me/s/rybar_mena","https://t.me/s/rybar_pacific","https://t.me/s/mosnews","https://t.me/s/brieflyru"
]
VIP_CHANNELS = ["anserenko", "kremlin_sekret","rybar","Russian_OSINT","rybar_mena","rybar_pacific","topwar_official"] 

def load_bookmarks():
    try:
        res = supabase.table("bookmarks_db").select("*").execute()
        return {row['channel_name']: row['last_read_id'] for row in res.data}
    except: return {}

def save_bookmarks(bookmarks):
    try:
        data = [{"channel_name": k, "last_read_id": v} for k, v in bookmarks.items()]
        if data: supabase.table("bookmarks_db").upsert(data).execute()
    except: pass

def run_auto_scrape():
    print("🚁 无人机升空：开始执行静默抓取任务...")
    bookmarks = load_bookmarks()
    raw_intelligence = ""
    new_msg_count = 0
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    for url in channel_urls:
        try:
            channel_name = url.split('/s/')[-1]
            last_read_id = bookmarks.get(channel_name, 0)
            highest_id = last_read_id
            
            response = requests.get(url, headers=headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            message_blocks = soup.find_all('div', class_='tgme_widget_message')
            if last_read_id == 0: message_blocks = message_blocks[-5:] 
                
            channel_new_text = ""
            for block in message_blocks:
                post_id_str = block.get('data-post')
                text_div = block.find('div', class_='tgme_widget_message_text')
                time_tag = block.find('time')
                msg_time = time_tag.get('datetime', '')[:16].replace('T', ' ') if time_tag else "未知时间"
                
                if post_id_str and text_div:
                    msg_id = int(post_id_str.split('/')[-1])
                    if msg_id > last_read_id:
                        channel_new_text += f"[发帖时间: {msg_time}] " + text_div.text + "\n"
                        new_msg_count += 1
                        if msg_id > highest_id: highest_id = msg_id
            
            if channel_new_text != "":
                is_vip = "【🔴 VIP 必须提炼】" if channel_name in VIP_CHANNELS else ""
                raw_intelligence += f"\n\n--- 来源：{channel_name} {is_vip} ---\n" + channel_new_text
                bookmarks[channel_name] = highest_id
        except Exception as e: 
            print(f"⚠️ 频道 {channel_name} 抓取失败: {e}")
            
    save_bookmarks(bookmarks)
    
    if new_msg_count == 0:
        print("🟢 侦察完毕：暂无新情报。")
        return

    print(f"🔥 截获 {new_msg_count} 条原始信息，呼叫 DeepSeek 引擎进行提炼...")
    
    client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
    system_prompt = """
    你是一位顶级的地缘政治与 OSINT 分析官。
    请分析原始消息，浓缩成独立情报，必须彻底翻译为简体中文！
    ⚠️ 极其重要指令 1：原始文本中带有 [发帖时间: ...]。如果有多个来源讲述同一件事，请提取出其中最早的那个时间，格式为 YYYY-MM-DD HH:MM。
    ⚠️ 极其重要指令 2：如果该条信息的来源带有 "【🔴 VIP 必须提炼】" 的标记，请在输出的 "summary" 字段最后，追加 "【💎 VIP 原文全译】：" 及完整的中文翻译。
    ⚠️ 极其重要指令 3：输出必须是严格合法的 JSON！JSON 内部换行必须用 "\\n"，双引号必须用 "\\" 转义！
    
    【🎯 核心战术打分量表 (score: 0-100)】：
    - 90-100分 (极高危/战略级)：将改变地缘格局、重大高层清洗/人事突变、涉华重大负面/核心利益链异动。
    - 70-89分 (高价值线索)：中等规模突发冲突、关键供应链/能源网异动。
    - 40-69分 (一般情报)：常规战况播报、例行外交辞令、宏观经济数据的一般波动。
    - 0-39分 (信息噪点)：无意义宣传、未经证实的边缘八卦。（尽量剔除此类信息）。
    
    【输出合法 JSON】：
    {
        "reports": [
            {"title": "中文标题", "summary": "中文概述及VIP全文", "category": "China Nexus 等代号", "score": 85, "source": "频道", "publish_time": "最早发布时间(YYYY-MM-DD HH:MM)"}
        ]
    }
    """
    try:
        ai_response = client.chat.completions.create(
            model="deepseek-chat", messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": raw_intelligence}],
            response_format={"type": "json_object"}, max_tokens=8000
        )
        reports = json.loads(ai_response.choices[0].message.content).get("reports", [])
        for rep in reports:
            supabase.table("intelligence_db").insert({
                "title": rep.get("title", "无标题"), "summary": rep.get("summary", "无内容"),
                "category": rep.get("category", "Global Macro"), "score": rep.get("score", 0), 
                "source": rep.get("source", "未知"), "publish_time": rep.get("publish_time", "未知时间")
            }).execute()
        print(f"✅ 任务圆满完成！已向 Supabase 数据库成功存入 {len(reports)} 条中文高价值情报！")
    except Exception as e:
        print(f"🚨 DeepSeek 解析或写入数据库失败：{e}")

if __name__ == "__main__":
    run_auto_scrape()
