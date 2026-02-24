import streamlit as st
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
import json
import os
from supabase import create_client, Client # 🌟 新增：数据库通信工具

# ==========================================
# 🌸 1. 网页基础与密码门
# ==========================================
st.set_page_config(page_title="花魁 OSINT", page_icon="🌸", layout="wide", initial_sidebar_state="expanded")

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🔒 绝密区域：请输入访问许可")
    st.markdown("---")
    pwd = st.text_input("长官，请核验您的访问口令：", type="password")
    if st.button("验证身份"):
        if pwd == st.secrets["APP_PASSWORD"]:
            st.session_state.authenticated = True
            st.success("✅ 身份核验通过！正在开启指挥中心...")
            st.rerun()
        else:
            st.error("🚨 警告：授权失败！口令错误！")
    st.stop() 

# ==========================================
# 🌸 2. 核心配置与云端连接
# ==========================================
API_KEY = st.secrets["DEEPSEEK_API_KEY"]

# 🌟 初始化 Supabase 数据库连接
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

channel_urls = [
    "https://t.me/s/ejdailyru", "https://t.me/s/Ateobreaking", "https://t.me/s/theinsider", 
    "https://t.me/s/moscowtimes_ru", "https://t.me/s/economica", "https://t.me/s/rybar_africa",
    "https://t.me/s/zakupki_time", "https://t.me/s/truestorymedia", "https://t.me/s/AoMurmansk",
    "https://t.me/s/moscow_laundry", "https://t.me/s/svtvnews", "https://t.me/s/notes_veterans",
    "https://t.me/s/militarysummary", "https://t.me/s/Tolo_news", "https://t.me/s/kremlin_sekret",
    "https://t.me/s/dva_majors", "https://t.me/s/caucasar", "https://t.me/s/rybar",
    "https://t.me/s/olen_nn", "https://t.me/s/russicaRU", "https://t.me/s/topwar_official",
    "https://t.me/s/RusskajaIdea", "https://t.me/s/riakatysha", "https://t.me/s/rybar_latam",
    "https://t.me/s/zhivoff", "https://t.me/s/anserenko", "https://t.me/s/wolframiumZ",
    "https://t.me/s/vatnoeboloto", "https://t.me/s/romanromachev", "https://t.me/s/thehegemonist",
    "https://t.me/s/budni_manipulyatora", "https://t.me/s/ManoiloToday", "https://t.me/s/rtechnocom",
    "https://t.me/s/darpaandcia", "https://t.me/s/istories_media", "https://t.me/s/mediazona_exclusive",
    "https://t.me/s/Russian_OSINT", "https://t.me/s/alter_academy", "https://t.me/s/rybar_mena",
    "https://t.me/s/rybar_pacific", "https://t.me/s/mosnews", "https://t.me/s/brieflyru"
]
VIP_CHANNELS = ["anserenko", "kremlin_sekret","rybar","Russian_OSINT","rybar_mena","rybar_pacific","topwar_official"] 

# 书签系统暂时保留本地机制，未来V3.0再将其云端化
BOOKMARK_FILE = "bookmark.json"
def load_bookmarks():
    if os.path.exists(BOOKMARK_FILE):
        with open(BOOKMARK_FILE, "r", encoding="utf-8") as f: return json.load(f)
    return {}
def save_bookmarks(bookmarks):
    with open(BOOKMARK_FILE, "w", encoding="utf-8") as f: json.dump(bookmarks, f)

# ==========================================
# 🌸 3. 左侧战术侧边栏 (Sidebar)
# ==========================================
with st.sidebar:
    st.title("⚙️ 战术控制台")
    st.caption("操作员：最高指挥官")
    st.markdown("---")
    
    run_btn = st.button("🚀 启动全网深度侦察", use_container_width=True, type="primary")
    
    st.markdown("---")
    st.subheader("🎯 情报筛选器")
    filter_category = st.selectbox("领域锁定：", ["全部领域", "China Nexus", "Espionage", "Kremlin Core", "RU Local Event", "Global Macro"])
    filter_score = st.slider("最低威胁分阀值：", 0, 100, 0)
    
    # 新增：协作状态过滤
    filter_assignee = st.selectbox("人员追踪：", ["全部人员", "未分配", "张三", "李四", "王五"])
    
    st.markdown("---")
    st.caption("🌸 花魁 OSINT v2.0 | Supabase 强力驱动")

# ==========================================
# 🌸 4. 抓取并【写入数据库】逻辑
# ==========================================
if run_btn:
    with st.spinner('花魁正在隐秘抓取并呼叫大脑，随后将刻录至云端数据库...'):
        try:
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
                        if post_id_str and text_div:
                            msg_id = int(post_id_str.split('/')[-1])
                            if msg_id > last_read_id:
                                channel_new_text += text_div.text + "\n"
                                new_msg_count += 1
                                if msg_id > highest_id: highest_id = msg_id
                    
                    if channel_new_text != "":
                        is_vip = "【🔴 VIP 必须提炼】" if channel_name in VIP_CHANNELS else ""
                        raw_intelligence += f"\n\n--- 来源：{channel_name} {is_vip} ---\n" + channel_new_text
                        bookmarks[channel_name] = highest_id
                except Exception as e:
                    pass 

            save_bookmarks(bookmarks)
            
            if new_msg_count == 0:
                st.sidebar.success("今日暂无更新。")
            else:
                client = OpenAI(api_key=API_KEY, base_url="https://api.deepseek.com")
                system_prompt = """
                你是一位顶级的地缘政治与开源情报（OSINT）首席分析官。请分析我提供的多频道原始消息。
                任务：剔除闲聊，将核心价值浓缩成独立情报（VIP频道必须提取）。输出严格的简体中文。
                挑选出最具战略价值的前 10-15 条。
                
                分类代号：China Nexus / Espionage / Kremlin Core / RU Local Event / Global Macro
                评分标准：0-100分。
                
                输出合法 JSON：{"reports": [{"title": "","summary": "","category": "","score": 85,"source": ""}]}
                """
                ai_response = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": raw_intelligence}],
                    response_format={"type": "json_object"}, max_tokens=4000, stream=False
                )
                
                parsed_data = json.loads(ai_response.choices[0].message.content)
                reports = parsed_data.get("reports", [])
                
                # 🌟🌟🌟 核心进化：把 AI 吐出的数据，一条条刻进 Supabase 数据库！
                for rep in reports:
                    supabase.table("intelligence_db").insert({
                        "title": rep.get("title", "无标题"),
                        "summary": rep.get("summary", "无内容"),
                        "category": rep.get("category", "Global Macro"),
                        "score": rep.get("score", 0),
                        "source": rep.get("source", "未知渠道")
                    }).execute()
                
                st.sidebar.success(f"✅ 成功截获 {len(reports)} 条绝密情报并已永久归档至云端！")
                
        except Exception as e:
            st.error(f"任务故障：{e}")

# ==========================================
# 🌸 5. 右侧主屏幕：从数据库【读取】与实时交互
# ==========================================
st.title("🌸 战略情报指挥中心 (实时大屏)")

# 🌟 从 Supabase 数据库拉取所有情报（按 ID 倒序，最新的在前面）
try:
    db_response = supabase.table("intelligence_db").select("*").order("id", desc=True).execute()
    db_cards = db_response.data
except Exception as e:
    st.error(f"数据库连接异常，请检查网络或密钥：{e}")
    db_cards = []

if len(db_cards) > 0:
    total_reports = len(db_cards)
    high_risk_count = sum(1 for card in db_cards if card.get('score', 0) >= 80)
    china_nexus_count = sum(1 for card in db_cards if card.get('category') == 'China Nexus')
    
    col1, col2, col3 = st.columns(3)
    col1.metric("📄 数据库历史沉淀", f"{total_reports} 份")
    col2.metric("🔴 历史高危预警", f"{high_risk_count} 起", "需长官批示", delta_color="inverse")
    col3.metric("🇨🇳 涉华动向档案", f"{china_nexus_count} 起")
    st.markdown("---")

    # 经过漏斗过滤
    filtered_cards = []
    for card in db_cards:
        match_category = (filter_category == "全部领域") or (card.get('category') == filter_category)
        match_score = card.get('score', 0) >= filter_score
        match_assignee = (filter_assignee == "全部人员") or (card.get('assignee') == filter_assignee)
        
        if match_category and match_score and match_assignee:
            filtered_cards.append(card)
            
    if len(filtered_cards) == 0:
        st.info("💡 当前筛选条件下无匹配情报。")
    else:
        for card in filtered_cards:
            score = card.get('score', 0)
            if score >= 80: border_color = "🔴"
            elif score >= 60: border_color = "🟡"
            else: border_color = "🔵"
                
            with st.container(border=True):
                st.markdown(f"### {border_color} [{score}分] {card.get('category')} | {card.get('title')}")
                # 增加了时间戳展示
                time_str = card.get('created_at', '')[:10]
                st.caption(f"📡 来源：{card.get('source')} | 🕵️ 录入时间：{time_str} | 📌 当前负责人：**{card.get('assignee', '未分配')}**")
                st.write(card.get('summary'))
                
                st.markdown("---")
                c1, c2, c3 = st.columns([1, 1, 2])
                with c1:
                    # 🌟 真实数据库交互：修改状态
                    current_status = card.get('status', '待核实')
                    status_options = ["待核实", "跟进中", "已归档"]
                    new_status = st.selectbox("更新状态", status_options, index=status_options.index(current_status), key=f"status_{card['id']}", label_visibility="collapsed")
                    if new_status != current_status:
                        supabase.table("intelligence_db").update({"status": new_status}).eq("id", card['id']).execute()
                        st.toast(f"状态已更新为：{new_status}")
                        st.rerun()
                with c2:
                    # 🌟 真实数据库交互：分配任务给组员
                    current_assignee = card.get('assignee', '未分配')
                    team_members = ["未分配", "张三", "李四", "王五"]
                    new_assignee = st.selectbox("分配组员", team_members, index=team_members.index(current_assignee), key=f"assign_{card['id']}", label_visibility="collapsed")
                    if new_assignee != current_assignee:
                        supabase.table("intelligence_db").update({"assignee": new_assignee}).eq("id", card['id']).execute()
                        st.toast(f"任务已强制派发给：{new_assignee}")
                        st.rerun() # 立即刷新网页，你会看到负责人的名字变了！
                with c3:
                    st.write(f"🏷️ 当前追踪状态：`{current_status}`")
else:
    st.info("👈 报告长官，数据库目前为空。请在侧边栏点击启动按钮，执行第一次入库作业！")