import streamlit as st
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
import json
import os

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
# 🌸 2. 核心配置区
# ==========================================
API_KEY = st.secrets["sk-b48c2f524fe94c91a77becfb7922ff2a"]

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
BOOKMARK_FILE = "bookmark.json"

def load_bookmarks():
    if os.path.exists(BOOKMARK_FILE):
        with open(BOOKMARK_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_bookmarks(bookmarks):
    with open(BOOKMARK_FILE, "w", encoding="utf-8") as f:
        json.dump(bookmarks, f)

if 'intelligence_cards' not in st.session_state:
    st.session_state.intelligence_cards = []

# ==========================================
# 🌸 3. 左侧战术侧边栏 (Sidebar)
# ==========================================
with st.sidebar:
    st.title("⚙️ 战术控制台")
    st.caption("操作员：最高指挥官")
    st.markdown("---")
    
    # 抓取按钮移到了这里
    run_btn = st.button("🚀 启动全网深度侦察", use_container_width=True, type="primary")
    
    st.markdown("---")
    st.subheader("🎯 情报筛选器")
    # 添加过滤组件
    filter_category = st.selectbox("领域锁定：", ["全部领域", "China Nexus", "Espionage", "Kremlin Core", "RU Local Event", "Global Macro"])
    filter_score = st.slider("最低威胁分阀值：", 0, 100, 0)
    
    st.markdown("---")
    st.caption("🌸 花魁 OSINT v2.0 | Powered by DeepSeek & Streamlit")

# ==========================================
# 🌸 4. 抓取与大脑提炼逻辑 (仅当点击按钮时运行)
# ==========================================
if run_btn:
    with st.spinner('花魁正在隐秘抓取并呼叫大脑进行深度解析，请稍候...'):
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
                    
                    if last_read_id == 0:
                        message_blocks = message_blocks[-5:] 
                        
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
                st.sidebar.success("巡逻完毕，今日暂无更新。")
            else:
                client = OpenAI(api_key=API_KEY, base_url="https://api.deepseek.com")
                system_prompt = """
                你是一位顶级的地缘政治与开源情报（OSINT）首席分析官。
                请分析我提供的多频道 Telegram 原始消息。
                
                【你的核心任务】：
                1. 剔除广告、无意义闲聊。将有价值的信息浓缩成独立的情报。
                2. 针对标有“【🔴 VIP 必须提炼】”的内容，务必单独生成情报。
                3. ⚠️ 输出的标题和内容必须是**专业、严谨的简体中文**！
                
                严格挑选出最具战略价值的前 10 到 15 条情报进行汇报。
                
                【情报分类代号】：
                - China Nexus
                - Espionage
                - Kremlin Core
                - RU Local Event
                - Global Macro
                
                【打分标准】：评估“战略影响指数”(0-100分)。
                
                输出合法 JSON 格式，如下：
                {
                    "reports": [
                        {"title": "中文标题", "summary": "中文概述", "category": "英文代号", "score": 85, "source": "频道名称"}
                    ]
                }
                """
                ai_response = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": raw_intelligence}],
                    response_format={"type": "json_object"}, 
                    max_tokens=4000, 
                    stream=False
                )
                
                parsed_data = json.loads(ai_response.choices[0].message.content)
                st.session_state.intelligence_cards = parsed_data.get("reports", [])
                
        except Exception as e:
            st.error(f"任务故障：{e}")

# ==========================================
# 🌸 5. 右侧主屏幕：大盘数据与情报卡片
# ==========================================
st.title("🌸 战略情报指挥中心 (主屏幕)")

# 如果有情报，先显示顶部仪表板
if len(st.session_state.intelligence_cards) > 0:
    # 计算一些宏观数据
    total_reports = len(st.session_state.intelligence_cards)
    high_risk_count = sum(1 for card in st.session_state.intelligence_cards if card.get('score', 0) >= 80)
    china_nexus_count = sum(1 for card in st.session_state.intelligence_cards if card.get('category') == 'China Nexus')
    
    # 渲染顶部三个大数字仪表盘
    col1, col2, col3 = st.columns(3)
    col1.metric(label="📄 今日截获极密情报", value=f"{total_reports} 份")
    col2.metric(label="🔴 80分以上高危预警", value=f"{high_risk_count} 起", delta="需长官重点批示", delta_color="inverse")
    col3.metric(label="🇨🇳 涉华动向 (China Nexus)", value=f"{china_nexus_count} 起")
    
    st.markdown("---")

    # 根据侧边栏的“漏斗”过滤情报
    filtered_cards = []
    for card in st.session_state.intelligence_cards:
        match_category = (filter_category == "全部领域") or (card.get('category') == filter_category)
        match_score = card.get('score', 0) >= filter_score
        
        if match_category and match_score:
            filtered_cards.append(card)
            
    # 对过滤后的卡片排序
    sorted_cards = sorted(filtered_cards, key=lambda x: x.get('score', 0), reverse=True)
    
    # 循环渲染卡片
    if len(sorted_cards) == 0:
        st.info("💡 当前筛选条件下没有符合标准的情报。请尝试在左侧侧边栏放宽过滤条件。")
    else:
        for index, card in enumerate(sorted_cards):
            score = card.get('score', 0)
            if score >= 80: border_color = "🔴"
            elif score >= 60: border_color = "🟡"
            else: border_color = "🔵"
                
            with st.container(border=True):
                st.markdown(f"### {border_color} [{score}分] {card.get('category')} | {card.get('title')}")
                st.caption(f"📡 来源：{card.get('source')} | 🕵️ 整理者：花魁 AI")
                st.write(card.get('summary'))
                
                st.markdown("---")
                c1, c2, c3, c4 = st.columns([1, 1, 1, 2])
                with c1:
                    if st.button("👍 确认价值", key=f"like_{index}"): st.toast("已赞")
                with c2:
                    if st.button("⭐ 归档", key=f"save_{index}"): st.toast("已入库")
                with c3:
                    assignee = st.selectbox("分配任务", ["选择组员", "张三", "李四"], key=f"assign_{index}", label_visibility="collapsed")
                    if assignee != "选择组员": st.toast(f"已指派给 {assignee}")
                with c4:
                    st.text_input("批示：", placeholder="输入批示后回车...", key=f"comment_{index}", label_visibility="collapsed")
else:
    st.info("👈 长官，请在左侧【战术控制台】点击启动按钮，唤醒花魁为您进行全网侦察。")