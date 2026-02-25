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
    print("🚁 无人机升空：开始执行网格化静默抓取任务...")
    bookmarks = load_bookmarks()
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    # 🌟 战术升级 1：分队网格化搜索（每 8 个频道为一组，防止 AI 注意力涣散）
    BATCH_SIZE = 8
    channel_batches = [channel_urls[i:i + BATCH_SIZE] for i in range(0, len(channel_urls), BATCH_SIZE)]
    
    total_saved = 0
    client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
    
    for batch_index, batch_urls in enumerate(channel_batches):
        raw_intelligence = ""
        new_msg_count = 0
        
        for url in batch_urls:
            try:
                channel_name = url.split('/s/')[-1]
                last_read_id = bookmarks.get(channel_name, 0)
                highest_id = last_read_id
                
                channel_new_text = ""
                current_url = url
                pages_fetched = 0
                
                # 🌟 V5.2 时光倒流引擎：最多往前翻阅 5 页（约 100 条历史消息），防止死循环
                while pages_fetched < 5:
                    response = requests.get(current_url, headers=headers)
                    soup = BeautifulSoup(response.text, 'html.parser')
                    message_blocks = soup.find_all('div', class_='tgme_widget_message')
                    
                    if not message_blocks: break
                    
                    # 第一次收录该频道时，限制抓取最新 20 条，不翻页
                    if last_read_id == 0 and pages_fetched == 0: 
                        message_blocks = message_blocks[-20:] 
                        
                    page_has_new_msg = False
                    oldest_msg_id_on_page = 999999999
                    page_text = ""
                    
                    for block in message_blocks:
                        post_id_str = block.get('data-post')
                        text_div = block.find('div', class_='tgme_widget_message_text')
                        time_tag = block.find('time')
                        msg_time = time_tag.get('datetime', '')[:16].replace('T', ' ') if time_tag else "未知时间"
                        
                        if post_id_str and text_div:
                            msg_id = int(post_id_str.split('/')[-1])
                            if msg_id < oldest_msg_id_on_page: 
                                oldest_msg_id_on_page = msg_id
                            
                            if msg_id > last_read_id:
                                page_text += f"[发帖时间: {msg_time}] " + text_div.text + "\n"
                                new_msg_count += 1
                                page_has_new_msg = True
                                if msg_id > highest_id: highest_id = msg_id
                    
                    # 巧妙拼接：把旧网页捞出来的信息，垫在前面，保证最终 AI 阅读的时间线是顺畅的！
                    channel_new_text = page_text + channel_new_text
                    
                    # 💡 核心机关：如果这一页最老的消息依然比书签新，且这不是个新频道，触发翻页！
                    if oldest_msg_id_on_page > last_read_id and page_has_new_msg and last_read_id != 0:
                        current_url = f"{url}?before={oldest_msg_id_on_page}"
                        pages_fetched += 1
                    else:
                        break # 无缝衔接成功，退出翻页循环
                        
                if channel_new_text != "":
                    is_vip = "【🔴 VIP 必须提炼】" if channel_name in VIP_CHANNELS else ""
                    raw_intelligence += f"\n\n--- 来源：{channel_name} {is_vip} ---\n" + channel_new_text
                    bookmarks[channel_name] = highest_id
            except Exception as e: 
                print(f"⚠️ 频道 {url} 抓取异常: {e}")
                
        # 存下书签
        save_bookmarks(bookmarks)
        
        # 🌟 战术升级 3：小队独立汇报制
        if new_msg_count > 0:
            print(f"🔥 第 {batch_index + 1} 小队截获 {new_msg_count} 条信息，呼叫 AI 提炼...")
            system_prompt = """
            你是一位顶级的地缘政治与 OSINT 分析官。
            请分析原始消息，浓缩成独立情报，必须彻底翻译为简体中文！
            ⚠️ 极其重要指令：由于你现在处理的是精细化小批次数据，请务必“宁滥勿缺”！只要包含具体事件、观点、动向，即便你认为价值不高，也要提取出来（可以打低分），绝不能随意丢弃原始信息！
            ⚠️ VIP 频道必须在 summary 结尾追加【💎 VIP 原文全译】：。
            ⚠️ 输出必须是严格合法的 JSON！JSON 内部换行必须用 "\\n"，双引号必须用 "\\" 转义！
            
            【输出合法 JSON】：
            {
                "reports": [
                    {"title": "中文标题", "summary": "中文概述", "category": "China Nexus 或其他", "score": 85, "source": "频道", "publish_time": "YYYY-MM-DD HH:MM"}
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
                total_saved += len(reports)
            except Exception as e:
                print(f"🚨 第 {batch_index + 1} 小队 DeepSeek 解析失败：{e}")
        else:
            print(f"🟢 第 {batch_index + 1} 小队暂无新情报。")

    print(f"✅ 全网格扫荡完毕！共向 Supabase 存入 {total_saved} 条高价值情报！")

if __name__ == "__main__":
    run_auto_scrape()
