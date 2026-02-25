import streamlit as st
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
import google.generativeai as genai
from docx import Document
from io import BytesIO
import json
import os
from supabase import create_client, Client

# ==========================================
# 🌸 1. 网页基础与【页面路由及身份系统】
# ==========================================
st.set_page_config(page_title="花魁 OSINT", page_icon="🌸", layout="wide", initial_sidebar_state="expanded")

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# 路由与状态管理
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.current_user = ""
if "page" not in st.session_state:
    st.session_state.page = "main" # 默认停留在主屏幕
if "current_report" not in st.session_state:
    st.session_state.current_report = None # 记录当前正在被挖掘的情报

if not st.session_state.authenticated:
    st.title("🔒 绝密区域：Agent身份核验")
    st.markdown("---")
    team_members = ['指挥官', '工程师', '梅潮风', '张可可', '丸子', '听风', '瑰夏', '阿拉比卡', '耶加雪非', '蓝山', '曼特宁']
    user_name = st.selectbox("请选择Agent代号：", team_members)
    pwd = st.text_input("请输入访问口令：", type="password")
    if st.button("登录指挥中心", type="primary"):
        auth_response = supabase.table("agents_db").select("*").eq("agent_name", user_name).eq("password", pwd).execute()
        if len(auth_response.data) > 0:
            st.session_state.authenticated = True
            st.session_state.current_user = user_name
            st.success(f"✅ 身份核验通过！欢迎Agent：{user_name}")
            st.rerun()
        else:
            st.error("🚨 警告：授权失败！口令错误或身份不符！")
    st.stop() 

# ==========================================
# 🌸 2. 核心配置与工具函数
# ==========================================
DEEPSEEK_API_KEY = st.secrets["DEEPSEEK_API_KEY"]
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=GEMINI_API_KEY) # 初始化 Gemini 引擎

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

def generate_word_doc(title, content):
    doc = Document()
    doc.add_heading(f"深度研判专报：{title}", 0)
    doc.add_paragraph(content)
    bio = BytesIO()
    doc.save(bio)
    return bio.getvalue()

# ==========================================
# 🌸 3. 页面分支：主大厅 (Main) vs 独立审讯室 (Deep Dive)
# ==========================================

if st.session_state.page == "main":
    # ---------------- 战术侧边栏 ----------------
    with st.sidebar:
        st.title("⚙️ 战术控制台")
        st.success(f"🟢 在线Agent: **{st.session_state.current_user}**")
        run_btn = st.button("🚀 启动常态挖掘 (DeepSeek)", use_container_width=True, type="primary")
        st.markdown("---")
        st.subheader("🎯 情报筛选器")
        filter_category = st.selectbox("领域锁定：", ["全部领域", "China Nexus", "Espionage", "Kremlin Core", "RU Local Event", "Global Macro"])
        filter_score = st.slider("最低威胁分阀值：", 0, 100, 0)
        st.markdown("---")
        st.caption("🌸 花魁 OSINT v4.0 | 双引擎架构")

    # ---------------- 抓取与 DeepSeek 分析 ----------------
    if run_btn:
        with st.spinner('调用 DeepSeek 引擎执行广度侦察与翻译...'):
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
                    except: pass 
                save_bookmarks(bookmarks)
                
                if new_msg_count == 0:
                    st.sidebar.success("暂无更新。")
                else:
                    client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
                    system_prompt = """
                    你是一位顶级的地缘政治与开源情报（OSINT）首席分析官。
                    请分析我提供的多频道原始消息（包含大量俄语、英语等外文生肉）。
                    
                    【你的核心任务】：
                    1. 剔除广告、无意义闲聊。将有价值的信息浓缩成独立的情报。
                    2. 针对标有“【🔴 VIP 必须提炼】”的内容，务必单独生成情报，绝不能遗漏。
                    3. ⚠️ 极其重要（最高指令）：无论原文是什么语言，你最终输出的标题和内容都必须彻底翻译为**专业、严谨的简体中文**！绝对不允许在输出的 JSON 内容中出现未翻译的外文生肉！
                    
                    【数量限制】：严格挑选出最具战略价值的前 10 到 15 条情报。
                    
                    【情报分类代号】：
                    - China Nexus
                    - Espionage
                    - Kremlin Core
                    - RU Local Event
                    - Global Macro
                    
                    【打分标准】：评估“战略影响指数”(0-100分)。
                    
                    【输出格式要求】：必须且只能输出合法的 JSON 格式：
                    {
                        "reports": [
                            {
                                "title": "一句话精炼的中文标题",
                                "summary": "情报核心内容的详细中文概述（条理清晰，翻译信达雅）",
                                "category": "上述英文代号之一",
                                "score": 85,
                                "source": "频道名称"
                            }
                        ]
                    }
                    """
                    
                    # 修复了这里的缩进对齐问题
                    ai_response = client.chat.completions.create(
                        model="deepseek-chat", 
                        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": raw_intelligence}],
                        response_format={"type": "json_object"}, 
                        max_tokens=4000
                    )
                    reports = json.loads(ai_response.choices[0].message.content).get("reports", [])
                    for rep in reports:
                        supabase.table("intelligence_db").insert({
                            "title": rep.get("title", "无标题"), "summary": rep.get("summary", "无内容"),
                            "category": rep.get("category", "Global Macro"), "score": rep.get("score", 0), "source": rep.get("source", "未知")
                        }).execute()
                    st.sidebar.success(f"✅ 截获 {len(reports)} 条中文情报！")
            except Exception as e: st.error(f"故障：{e}")

    # ---------------- 实时情报卡片流 ----------------
    st.title("🌸 OSINT指挥大厅")
    try:
        db_response = supabase.table("intelligence_db").select("*").order("id", desc=True).execute()
        db_cards = db_response.data
    except: db_cards = []

    if len(db_cards) > 0:
        filtered_cards = [c for c in db_cards if (filter_category == "全部领域" or c.get('category') == filter_category) and c.get('score', 0) >= filter_score]
        
        for card in filtered_cards:
            score = card.get('score', 0)
            border_color = "🔴" if score >= 80 else "🟡" if score >= 60 else "🔵"
                
            with st.container(border=True):
                st.markdown(f"### {border_color} [{score}分] {card.get('category')} | {card.get('title')}")
                st.caption(f"📡 来源：{card.get('source')} | 🕵️ 录入：{card.get('created_at', '')[:10]}")
                st.write(card.get('summary'))
                
                # 留言展示区
                comments_res = supabase.table("comments_db").select("*").eq("report_id", card['id']).order("created_at").execute()
                if len(comments_res.data) > 0:
                    st.markdown("---")
                    for c in comments_res.data:
                        st.markdown(f"**🕵️ {c['agent_name']}** : {c['content']}")
                st.markdown("---")
                
                # 交互按钮区
                c1, c2, c3 = st.columns([2, 1, 1])
                with c1:
                    comment_text = st.text_input("📝 添加批示...", key=f"in_{card['id']}", label_visibility="collapsed")
                with c2:
                    if st.button("💬 提交批示", key=f"btn_c_{card['id']}", use_container_width=True) and comment_text:
                        supabase.table("comments_db").insert({"report_id": card['id'], "agent_name": st.session_state.current_user, "content": comment_text}).execute()
                        st.rerun()
                with c3:
                    if st.button("🔍 深度挖掘", key=f"btn_d_{card['id']}", use_container_width=True, type="secondary"):
                        st.session_state.current_report = card
                        st.session_state.page = "deep_dive" 
                        st.rerun() 

elif st.session_state.page == "deep_dive":
    # ==========================================
    # 🌸 4. 独立审讯室：Gemini Pro 深度挖掘档案库
    # ==========================================
    card = st.session_state.current_report
    
    st.title("👁️ 深渊凝视：独立战术研判室")
    if st.button("⬅️ 返回战略情报大厅", type="primary"):
        st.session_state.page = "main"
        st.rerun()
        
    st.markdown("---")
    st.markdown(f"#### 【原始情报目标】\n**{card['title']}**\n> {card['summary']}")
    
    # 🌟 核心防败家机制：先查云端档案柜！
    deep_res = supabase.table("deep_dives_db").select("*").eq("report_id", card['id']).execute()
    
    if len(deep_res.data) > 0:
        st.success(f"💾 历史档案调取成功！本报告由特工 **{deep_res.data[0]['agent_name']}** 耗费 AI 算力挖掘，现为您免费呈现。")
        final_content = deep_res.data[0]['content']
        st.markdown(final_content)
        
    else:
        with st.spinner("🧠 正在呼叫 Gemini Pro 引擎，进行全网深层推理与 HUMINT 画像..."):
            try:
                gemini_prompt = f"""
                你是一位隶属于顶尖情报机构的高级 HUMINT（人力情报）与 OSINT 联合分析专家。
                请基于以下截获的开源情报，调动你强大的网络搜索能力，补充完善情报素材，并进行深度推理，输出《深度研判专报》。
                
                【原始线索】：
                - 标题：{card['title']}
                - 摘要：{card['summary']}
                - 来源频道：{card['source']}
                
                【输出强制要求】必须包含以下 5 个模块（使用 Markdown 排版，语气极其冷峻客观，使用情报简报的文字风格）：
                1. 🌍 事件背景全貌：该事件的客观的全要素情报全貌，深层政治或经济背景。
                2. 💰 潜在利益链推演：事件各相关方的内部深层考量。可以广泛搜索并参考各类网络情报来源，也可以站在事件相关方的利益角度，开展严谨的分析研判。
                3. 👤 对策建议：站在中国的国家利益角度，提出该事件对中国的影响及应对措施的相关对策建议
                4. 🤝 HUMINT 接触突破口 (绝密操作指引)：如果要派特工在线上或线下了解更深层次的情报，应该如何找到并接近该信息源并建立合作，建议采取什么伪装身份（Cover）？切入点是什么？
                5. 🔗 交叉验证建议：为了核实真伪，特工应去查阅哪些具体的开源数据库（列出方向）？
                """
                
                model = genai.GenerativeModel('gemini-2.5-pro-latest')
                response = model.generate_content(gemini_prompt)
                final_content = response.text
                
                supabase.table("deep_dives_db").insert({
                    "report_id": card['id'],
                    "agent_name": st.session_state.current_user,
                    "content": final_content
                }).execute()
                
                st.success(f"🔥 Gemini Pro 挖掘完毕！已将此情报永久刻录至团队档案库。")
                st.markdown(final_content)
                
            except Exception as e:
                st.error(f"Gemini 引擎故障：{e}")
                final_content = ""

    # 🌟 自动生成 Word 导出文件
    if final_content:
        st.markdown("---")
        docx_data = generate_word_doc(card['title'], final_content)
        st.download_button(
            label="📥 将此报告导出为 Word 文档 (.docx)",
            data=docx_data,
            file_name=f"HUMINT专报_{card['id']}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            type="primary"
        )