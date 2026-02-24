import streamlit as st
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
import json
import os

# 1. 设置网页的标题和宽屏模式（这句必须放在最前面）
st.set_page_config(page_title="花魁 OSINT 系统", page_icon="🌸", layout="wide")

# ==========================================
# 🛡️ 新增：绝密大门（密码验证系统）
# ==========================================
# 检查备忘录里有没有登录状态，没有就默认为 False（未登录）
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

# 如果没有登录，就显示密码输入框
if not st.session_state.authenticated:
    st.title("🔒 绝密区域：请输入访问许可")
    st.markdown("---")
    
    # 输入框
    pwd = st.text_input("长官，请核验您的访问口令：", type="password")
    
    # 登录按钮
    if st.button("验证身份"):
        if pwd == st.secrets["APP_PASSWORD"]:
            st.session_state.authenticated = True
            st.success("✅ 身份核验通过！正在开启指挥中心...")
            st.rerun() # 刷新页面，进入系统
        else:
            st.error("🚨 警告：授权失败！口令错误！")
            
    # ⚠️ 极其关键的魔法指令：如果没登录，程序到此为止，绝对不往下执行！
    st.stop() 
# ==========================================
# 🌸 1. 核心配置区
# ==========================================
API_KEY = st.secrets["DEEPSEEK_API_KEY"] # ⚠️ 记得替换为你真实的 DeepSeek API Key

# 🎯 你的 42 个专属情报频道列阵（已修复语法格式）
channel_urls = [
    "https://t.me/s/ejdailyru",
    "https://t.me/s/Ateobreaking", 
    "https://t.me/s/theinsider", 
    "https://t.me/s/moscowtimes_ru",
    "https://t.me/s/economica",
    "https://t.me/s/rybar_africa",
    "https://t.me/s/zakupki_time",
    "https://t.me/s/truestorymedia",
    "https://t.me/s/AoMurmansk",
    "https://t.me/s/moscow_laundry",
    "https://t.me/s/svtvnews",
    "https://t.me/s/notes_veterans",
    "https://t.me/s/militarysummary",
    "https://t.me/s/Tolo_news",
    "https://t.me/s/kremlin_sekret",
    "https://t.me/s/dva_majors",
    "https://t.me/s/caucasar",
    "https://t.me/s/rybar",
    "https://t.me/s/olen_nn",
    "https://t.me/s/russicaRU",
    "https://t.me/s/topwar_official",
    "https://t.me/s/RusskajaIdea",
    "https://t.me/s/riakatysha",
    "https://t.me/s/rybar_latam",
    "https://t.me/s/zhivoff",
    "https://t.me/s/anserenko",
    "https://t.me/s/wolframiumZ",
    "https://t.me/s/vatnoeboloto",
    "https://t.me/s/romanromachev",
    "https://t.me/s/thehegemonist",
    "https://t.me/s/budni_manipulyatora",
    "https://t.me/s/ManoiloToday",
    "https://t.me/s/rtechnocom",
    "https://t.me/s/darpaandcia",
    "https://t.me/s/istories_media",
    "https://t.me/s/mediazona_exclusive",
    "https://t.me/s/Russian_OSINT",
    "https://t.me/s/alter_academy",
    "https://t.me/s/rybar_mena",
    "https://t.me/s/rybar_pacific",
    "https://t.me/s/mosnews",
    "https://t.me/s/brieflyru"
]

# 🎯 VIP 频道名单：只需要填频道链接最后面的字母即可。
# 我先帮你填了两个做示范，你可以随时修改或增加！
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

# ==========================================
# 🌸 2. 网页界面与抓取逻辑
# ==========================================
st.set_page_config(page_title="花魁 OSINT 系统", page_icon="🌸", layout="wide")
st.title("🌸 花魁 - 战略情报指挥中心")
st.markdown("---")

if 'intelligence_cards' not in st.session_state:
    st.session_state.intelligence_cards = []

if len(st.session_state.intelligence_cards) == 0:
    st.info(f"长官，花魁已锁定 {len(channel_urls)} 个高价值目标。防爆安全锁已开启，准备为您生成独立情报卡片。")
    
    if st.button("🚀 启动全网深度侦察", use_container_width=True):
        with st.spinner('花魁正在 42 个频道间穿梭，隐秘抓取并呼叫大脑进行深度解析，请稍候...'):
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
                        
                        # 🌟🌟🌟 防爆安全锁：如果是新频道，只看最近的 5 条消息 🌟🌟🌟
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
                            is_vip = "【🔴 绝对高优 VIP 频道，必须提炼】" if channel_name in VIP_CHANNELS else ""
                            raw_intelligence += f"\n\n--- 来源：{channel_name} {is_vip} ---\n" + channel_new_text
                            bookmarks[channel_name] = highest_id
                            
                    except Exception as e:
                        pass # 遇到打不开的频道默默跳过

                save_bookmarks(bookmarks)
                
                if new_msg_count == 0:
                    st.success("巡逻完毕，所有频道今日暂无更新。")
                else:
                    st.info(f"截获 {new_msg_count} 条新消息，正在交由 AI 大脑进行结构化提炼...")
                    client = OpenAI(api_key=API_KEY, base_url="https://api.deepseek.com")
                    
                    # 🎯 终极版提示词：强制中文输出 + 英文代号分类
                    system_prompt = """
                    你是一位顶级的地缘政治与开源情报（OSINT）首席分析官。
                    请分析我提供的多频道 Telegram 原始消息（可能包含大量俄语、英语等外语）。
                    
                    【你的核心任务】：
                    1. 剔除广告、无意义闲聊。
                    2. 将有价值的信息浓缩成一条条独立的情报。
                    3. 针对标有“【🔴 绝对高优 VIP 频道】”的内容，务必单独生成情报，绝不能遗漏。
                    4. ⚠️ 极其重要：无论原文是什么语言，你最终输出的标题和内容都必须是**专业、严谨的简体中文**！
                    
                    【数量严格限制】：
                    严格挑选出最重要、最具战略价值的前 15 到 20 条情报进行汇报。绝对不要超过 15 条！宁缺毋滥。
                    
                    【情报分类代号】（必须且只能归入以下一个英文代号）：
                    - China Nexus (与中国直接/间接相关的动向)
                    - Espionage (CIA/FSB/KGB/Mossad等情报机构动态)
                    - Kremlin Core (克宫决策、高层人事、俄联邦级战略)
                    - RU Local Event (莫斯科等地突发事件、后勤、抗议等地方异动)
                    - Global Macro (不属于以上类别的全球军事/政治/地缘动态)
                    
                    【打分标准】：为每条情报评估“战略影响指数”(0-100分)。90分以上为颠覆性事件，70分以上为重大推进。
                    
                    【极其重要的输出格式要求】：
                    你必须且只能输出合法的 JSON 格式。不要包含任何 Markdown 代码块标签（如 ```json）。
                    格式如下：
                    {
                        "reports": [
                            {
                                "title": "一句话精炼的中文标题",
                                "summary": "情报核心内容的详细中文概述（条理清晰，翻译信达雅）",
                                "category": "上述英文代号中的一项（例如：Kremlin Core）",
                                "score": 85,
                                "source": "频道名称"
                            }
                        ]
                    }
                    """
                    
                    # ⚠️ 注意这里增加了 max_tokens=4000，给了大模型充足的“换气”空间
                    ai_response = client.chat.completions.create(
                        model="deepseek-chat",
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": raw_intelligence}
                        ],
                        response_format={"type": "json_object"}, 
                        max_tokens=4000, 
                        stream=False
                    )
                    
                    ai_json_str = ai_response.choices[0].message.content
                    try:
                        parsed_data = json.loads(ai_json_str)
                        st.session_state.intelligence_cards = parsed_data.get("reports", [])
                        st.rerun()
                    except Exception as e:
                        st.error(f"解析 AI 数据失败。错误: {e}")
                        st.code(ai_json_str)

            except Exception as e:
                st.error(f"任务故障：{e}")

# ==========================================
# 🌸 3. 卡片式团队协作展示区
# ==========================================
if len(st.session_state.intelligence_cards) > 0:
    st.success(f"✅ 深度提炼完成！共生成 {len(st.session_state.intelligence_cards)} 份高价值独立简报。")
    
    # 根据分数排序
    sorted_cards = sorted(st.session_state.intelligence_cards, key=lambda x: x.get('score', 0), reverse=True)
    
    for index, card in enumerate(sorted_cards):
        score = card.get('score', 0)
        if score >= 80: border_color = "🔴"
        elif score >= 60: border_color = "🟡"
        else: border_color = "🔵"
            
        with st.container(border=True):
            st.markdown(f"### {border_color} [{score}分] {card.get('category')} | {card.get('title')}")
            st.caption(f"📡 来源渠道：{card.get('source')} | 🕵️ 整理者：花魁 AI")
            st.write(card.get('summary'))
            
            st.markdown("---")
            col1, col2, col3, col4 = st.columns([1, 1, 1, 2])
            with col1:
                if st.button("👍 确认价值", key=f"like_{index}"): st.toast(f"已赞：{card.get('title')}")
            with col2:
                if st.button("⭐ 归档", key=f"save_{index}"): st.toast("已入库")
            with col3:
                assignee = st.selectbox("分配核实任务", ["选择组员", "张三", "李四", "王五"], key=f"assign_{index}", label_visibility="collapsed")
                if assignee != "选择组员": st.toast(f"任务已指派给 {assignee}")
            with col4:
                st.text_input("快速批示：", placeholder="输入批示后回车...", key=f"comment_{index}", label_visibility="collapsed")