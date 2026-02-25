import streamlit as st
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
import anthropic 
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

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.current_user = ""
if "page" not in st.session_state:
    st.session_state.page = "main"
if "current_report" not in st.session_state:
    st.session_state.current_report = None
# 🌟 V5.0 新增：用于记录在“专注模式”下，特工当前正在批阅第几张卡片
if "focus_index" not in st.session_state:
    st.session_state.focus_index = 0

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
ANTHROPIC_API_KEY = st.secrets["ANTHROPIC_API_KEY"]

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
# 🌸 3. 全局左侧战术侧边栏 (多页面导航)
# ==========================================
with st.sidebar:
    st.title("⚙️ 战术控制台")
    st.success(f"🟢 在线Agent: **{st.session_state.current_user}**")
    
    st.markdown("---")
    st.subheader("🧭 导航中心")
    if st.button("🏠 主力指挥大厅", use_container_width=True, type="primary" if st.session_state.page == "main" else "secondary"):
        st.session_state.page = "main"
        st.rerun()
    if st.button("🗂️ 情报归档库", use_container_width=True, type="primary" if st.session_state.page == "archives" else "secondary"):
        st.session_state.page = "archives"
        st.rerun()
    if st.button("👁️ 深渊挖掘档案室", use_container_width=True, type="primary" if st.session_state.page == "deep_dive_list" else "secondary"):
        st.session_state.page = "deep_dive_list"
        st.rerun()
    
    st.markdown("---")
    st.caption("🌸 花魁 OSINT v4.1 | 协同归档版")

# ==========================================
# 🌸 4. 页面 1：主力指挥大厅 (抓取与展示)
# ==========================================
if st.session_state.page == "main":
    with st.sidebar:
        st.markdown("---")
        run_btn = st.button("🚀 启动常态挖掘 (DeepSeek)", use_container_width=True, type="primary")
        st.subheader("🎯 实时大厅筛选器")
        filter_category = st.selectbox("领域锁定：", ["全部领域", "China Nexus", "Espionage", "Kremlin Core", "RU Local Event", "Global Macro"])
        filter_score = st.slider("最低威胁分阀值：", 0, 100, 0)

    if run_btn:
        with st.spinner('调用 DeepSeek 引擎执行广度侦察（含时间轴穿透）...'):
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
                            
                            # 🌟 新增：提取真实发布时间
                            time_tag = block.find('time')
                            msg_time = time_tag.get('datetime', '')[:16].replace('T', ' ') if time_tag else "未知时间"
                            
                            if post_id_str and text_div:
                                msg_id = int(post_id_str.split('/')[-1])
                                if msg_id > last_read_id:
                                    # 把真实时间喂给 AI
                                    channel_new_text += f"[发帖时间: {msg_time}] " + text_div.text + "\n"
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
                    你是一位顶级的地缘政治与 OSINT 分析官。
                    请分析原始消息，浓缩成独立情报，必须彻底翻译为简体中文！
                    
                    ⚠️ 极其重要指令 1：原始文本中带有 [发帖时间: ...]。如果有多个来源讲述同一件事，请提取出其中最早的那个时间，格式为 YYYY-MM-DD HH:MM。
                    ⚠️ 极其重要指令 2：如果该条信息的来源带有 "【🔴 VIP 必须提炼】" 的标记，你必须在输出的 "summary" 字段的最后，换行加上 "【💎 VIP 原文全译】："，并附上该条消息一字不落的、完整的中文翻译！如果是普通来源，则不需要附带全文。
                    
                    【🎯 核心战术打分量表 (score: 0-100)】：
                    - 90-100分 (极高危/战略级)：将改变地缘格局、重大高层清洗/人事突变、涉华重大负面/核心利益链异动、核潜艇/战略武器调动。
                    - 70-89分 (高价值线索)：中等规模突发冲突、关键供应链/能源网异动、暴露出值得特工后续追踪的 HUMINT 切入点。
                    - 40-69分 (一般情报)：常规战况播报、例行外交辞令、宏观经济数据的一般波动。
                    - 0-39分 (信息噪点)：无意义的政治宣传、未经证实的边缘八卦、日常琐事。（请尽量将此类信息剔除，不要输出）。
                    
                    【输出合法 JSON】：
                    {
                        "reports": [
                            {"title": "中文标题", "summary": "中文概述（若为VIP则追加全文翻译）", "category": "China Nexus 等代号", "score": 85, "source": "频道", "publish_time": "最早发布时间(YYYY-MM-DD HH:MM)"}
                        ]
                    }
                    """
                    ai_response = client.chat.completions.create(
                        model="deepseek-chat", messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": raw_intelligence}],
                        response_format={"type": "json_object"}, max_tokens=4000
                    )
                    reports = json.loads(ai_response.choices[0].message.content).get("reports", [])
                    for rep in reports:
                        supabase.table("intelligence_db").insert({
                            "title": rep.get("title", "无标题"), "summary": rep.get("summary", "无内容"),
                            "category": rep.get("category", "Global Macro"), "score": rep.get("score", 0), "source": rep.get("source", "未知"),
                            "publish_time": rep.get("publish_time", "未知时间")
                        }).execute()
                    st.sidebar.success(f"✅ 截获 {len(reports)} 条中文情报！")
            except Exception as e: st.error(f"故障：{e}")

    st.title("🌸 OSINT 指挥大厅 (实时截获)")
    
    # 🌟 V5.0 核心大招：UI 模式无缝切换开关
    ui_mode = st.radio("👁️ 战术视觉模式切换：", ["初始模式 (经典列表)", "信息瀑布模式 (全局视野)", "专注模式 (沉浸审批)"], horizontal=True)
    st.markdown("---")
    
    try:
        db_response = supabase.table("intelligence_db").select("*").order("id", desc=True).execute()
        db_cards = db_response.data
    except: db_cards = []

    if len(db_cards) > 0:
        filtered_cards = [c for c in db_cards if (filter_category == "全部领域" or c.get('category') == filter_category) and c.get('score', 0) >= filter_score]
        
        if len(filtered_cards) == 0:
            st.info("💡 当前筛选条件下无匹配情报。")
        else:
            # ==========================================
            # 模式 1：初始模式 (经典单列列表，原汁原味)
            # ==========================================
            if ui_mode == "初始模式 (经典列表)":
                for card in filtered_cards:
                    score = card.get('score', 0)
                    border_color = "🔴" if score >= 80 else "🟡" if score >= 60 else "🔵"
                    with st.container(border=True):
                        st.markdown(f"### {border_color} [{score}分] {card.get('category')} | {card.get('title')}")
                        st.caption(f"📡 来源：{card.get('source')} | 🕰️ 真实发布时间：**{card.get('publish_time', '未获取')}**")
                        st.write(card.get('summary'))
                        
                        comments_res = supabase.table("comments_db").select("*").eq("report_id", card['id']).order("created_at").execute()
                        if len(comments_res.data) > 0:
                            st.markdown("---")
                            for c in comments_res.data:
                                st.markdown(f"**🕵️ {c['agent_name']}** : {c['content']}")
                        st.markdown("---")
                        
                        c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
                        with c1:
                            comment_text = st.text_input("📝 批示...", key=f"in_{card['id']}", label_visibility="collapsed")
                        with c2:
                            if st.button("💬 提交批示", key=f"btn_c_{card['id']}", use_container_width=True) and comment_text:
                                supabase.table("comments_db").insert({"report_id": card['id'], "agent_name": st.session_state.current_user, "content": comment_text}).execute()
                                st.rerun()
                        with c3:
                            if st.button("🔍 深度挖掘", key=f"btn_d_{card['id']}", use_container_width=True, type="secondary"):
                                st.session_state.current_report = card
                                st.session_state.page = "deep_dive" 
                                st.rerun()
                        with c4:
                            if st.button("⭐ 归档入库", key=f"btn_arc_{card['id']}", use_container_width=True):
                                try:
                                    supabase.table("archives_db").insert({"report_id": card['id'], "agent_name": st.session_state.current_user}).execute()
                                    st.toast("✅ 成功存入您的私人归档库！")
                                except:
                                    st.toast("⚠️ 这条情报您之前已经归档过了！")
            
            # ==========================================
            # 模式 2：信息瀑布模式 (三列高低错落排布)
            # ==========================================
            elif ui_mode == "信息瀑布模式 (全局视野)":
                cols = st.columns(3) # 创建 3 列
                for i, card in enumerate(filtered_cards):
                    col = cols[i % 3] # 轮流把卡片塞进 3 列里
                    with col.container(border=True):
                        score = card.get('score', 0)
                        border_color = "🔴" if score >= 80 else "🟡" if score >= 60 else "🔵"
                        
                        st.markdown(f"#### {border_color} [{score}分] {card.get('category')}")
                        st.markdown(f"**{card.get('title')}**")
                        st.caption(f"📡 {card.get('source')} | 🕰️ {card.get('publish_time', '未知')}")
                        
                        with st.expander("展开核心摘要与原文"):
                            st.write(card.get('summary'))
                        
                        c_left, c_right = st.columns(2)
                        with c_left:
                            if st.button("🔍 研判", key=f"wf_d_{card['id']}", use_container_width=True):
                                st.session_state.current_report = card
                                st.session_state.page = "deep_dive" 
                                st.rerun()
                        with c_right:
                            if st.button("⭐ 归档", key=f"wf_arc_{card['id']}", use_container_width=True):
                                try:
                                    supabase.table("archives_db").insert({"report_id": card['id'], "agent_name": st.session_state.current_user}).execute()
                                    st.toast("✅ 存入私人归档库！")
                                except: st.toast("⚠️ 已归档过！")

            # ==========================================
            # 模式 3：专注模式 (单卡片沉浸审批)
            # ==========================================
            elif ui_mode == "专注模式 (沉浸审批)":
                if st.session_state.focus_index >= len(filtered_cards):
                    st.session_state.focus_index = 0
                
                card = filtered_cards[st.session_state.focus_index]
                score = card.get('score', 0)
                border_color = "🔴" if score >= 80 else "🟡" if score >= 60 else "🔵"
                
                spacer1, center_col, spacer2 = st.columns([1, 2, 1]) # 使用空列挤压，让卡片居中独占
                
                with center_col.container(border=True):
                    st.markdown(f"## {border_color} [{score}分] {card.get('category')}")
                    st.markdown(f"### {card.get('title')}")
                    st.caption(f"📡 来源：{card.get('source')} | 🕰️ 真实发布时间：**{card.get('publish_time', '未获取')}**")
                    st.markdown("---")
                    st.write(card.get('summary'))
                    st.markdown("---")
                    
                    comments_res = supabase.table("comments_db").select("*").eq("report_id", card['id']).order("created_at").execute()
                    if len(comments_res.data) > 0:
                        st.caption("💬 **战术批示区：**")
                        for c in comments_res.data:
                            st.markdown(f"**🕵️ {c['agent_name']}** : {c['content']}")
                        st.markdown("---")
                    
                    comment_text = st.text_input("📝 添加批示...", key=f"foc_in_{card['id']}", label_visibility="collapsed")
                    if st.button("💬 提交批示并留在本页", key=f"foc_btn_c_{card['id']}", use_container_width=True) and comment_text:
                        supabase.table("comments_db").insert({"report_id": card['id'], "agent_name": st.session_state.current_user, "content": comment_text}).execute()
                        st.rerun()
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    
                    t1, t2 = st.columns(2)
                    with t1:
                        if st.button("❌ 忽略 / 划走", key=f"foc_pass_{card['id']}", use_container_width=True, type="secondary"):
                            st.session_state.focus_index += 1
                            st.rerun()
                    with t2:
                        if st.button("⭐ 归档入库", key=f"foc_arc_{card['id']}", use_container_width=True, type="primary"):
                            try:
                                supabase.table("archives_db").insert({"report_id": card['id'], "agent_name": st.session_state.current_user}).execute()
                                st.toast("✅ 归档成功！")
                            except: pass
                            st.session_state.focus_index += 1
                            st.rerun()
                            
                    if st.button("🔍 呼叫 Claude 启动深渊研判", key=f"foc_d_{card['id']}", use_container_width=True):
                        st.session_state.current_report = card
                        st.session_state.page = "deep_dive" 
                        st.rerun()
                        
                st.markdown(f"<p style='text-align: center; color: gray;'>👉 审批进度：( {st.session_state.focus_index + 1} / {len(filtered_cards)} )</p>", unsafe_allow_html=True)
    else:
        st.info("👈 报告长官，数据库目前为空。请启动侦察！")

# ==========================================
# 🌸 5. 页面 2：个人与团队情报归档库
# ==========================================
elif st.session_state.page == "archives":
    st.title("🗂️ 战略归档库")
    
    # 顶部选择器：看自己的，还是看全队的？
    view_mode = st.radio("视角切换：", ["👨‍💻 我的私人珍藏", "🌐 团队全员归档公开板"], horizontal=True)
    st.markdown("---")
    
    try:
        # 获取归档关系
        if view_mode == "👨‍💻 我的私人珍藏":
            arch_res = supabase.table("archives_db").select("*").eq("agent_name", st.session_state.current_user).execute()
        else:
            arch_res = supabase.table("archives_db").select("*").execute()
            
        archived_items = arch_res.data
        if len(archived_items) == 0:
            st.info("📦 归档库空空如也，快去指挥大厅淘宝吧！")
        else:
            # 提取所有被归档的 report_id
            report_ids = list(set([item['report_id'] for item in archived_items]))
            
            # 获取情报卡片本体
            db_res = supabase.table("intelligence_db").select("*").in_("id", report_ids).order("id", desc=True).execute()
            
            for card in db_res.data:
                # 找出是谁归档了这张卡（用于全员视角展示）
                archived_by = [a['agent_name'] for a in archived_items if a['report_id'] == card['id']]
                
                with st.container(border=True):
                    st.markdown(f"### [{card.get('score',0)}分] {card.get('title')}")
                    st.caption(f"📡 来源：{card.get('source')} | 🕰️ 真实发布：{card.get('publish_time', '未知')} | 🌟 归档者：`{', '.join(set(archived_by))}`")
                    st.write(card.get('summary'))
                    
                    if st.button("🔍 再次唤醒深度挖掘", key=f"arc_d_{card['id']}"):
                        st.session_state.current_report = card
                        st.session_state.page = "deep_dive"
                        st.rerun()

    except Exception as e:
        st.error(f"读取归档失败: {e}")

# ==========================================
# 🌸 6. 页面 3：深渊挖掘档案室 (已挖掘汇总)
# ==========================================
elif st.session_state.page == "deep_dive_list":
    st.title("👁️ 深渊档案室 (知识资产沉淀)")
    st.caption("这里存放着团队花费重金让大模型运算过的所有《深度研判专报》，全员均可免费查阅。")
    st.markdown("---")
    
    try:
        deep_res = supabase.table("deep_dives_db").select("*").order("created_at", desc=True).execute()
        dives = deep_res.data
        
        if len(dives) == 0:
            st.info("尚无深渊档案。去大厅点击【深度挖掘】生成您的第一份报告！")
        else:
            # 批量获取关联的情报标题
            report_ids = [d['report_id'] for d in dives]
            intel_res = supabase.table("intelligence_db").select("id, title, summary, source").in_("id", report_ids).execute()
            intel_dict = {item['id']: item for item in intel_res.data}
            
            for d in dives:
                origin_card = intel_dict.get(d['report_id'], {})
                with st.expander(f"📁 绝密研判专报：{origin_card.get('title', '未知情报')} (发起特工: {d['agent_name']})"):
                    st.caption(f"提取时间：{d['created_at'][:16].replace('T', ' ')}")
                    st.markdown(d['content'])
                    
                    # 也可以在这里直接下载 Word
                    docx_data = generate_word_doc(origin_card.get('title', ''), d['content'])
                    st.download_button(
                        label="📥 导出此专报 (Word)",
                        data=docx_data,
                        file_name=f"HUMINT_Archive_{d['report_id']}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        key=f"dl_{d['id']}"
                    )
    except Exception as e:
        st.error(f"读取深渊档案库失败: {e}")

# ==========================================
# 🌸 7. 独立审讯室：Claude 深度研判行动执行
# ==========================================
elif st.session_state.page == "deep_dive":
    card = st.session_state.current_report
    st.title("👁️ 独立战术研判室")
    if st.button("⬅️ 返回刚才的页面", type="primary"):
        st.session_state.page = "main" # 默认退回主页，也可自行修改
        st.rerun()
        
    st.markdown("---")
    st.markdown(f"#### 【原始情报目标】\n**{card['title']}**\n> {card['summary']}")
    
    deep_res = supabase.table("deep_dives_db").select("*").eq("report_id", card['id']).execute()
    
    if len(deep_res.data) > 0:
        st.success(f"💾 历史档案调取成功！本报告由Agent **{deep_res.data[0]['agent_name']}** 耗费 AI 算力挖掘，现为您免费呈现。")
        final_content = deep_res.data[0]['content']
        st.markdown(final_content)
        
    else:
        with st.spinner("🧠 正在呼叫 Claude 大脑，执行深层推演与 HUMINT 破局分析..."):
            try:
                # 依然保持你最强效的 Claude Prompt 不变
                claude_system_prompt = """
                你是一位隶属于顶尖情报机构的高级 HUMINT（人力情报）与 OSINT 联合分析专家。
                你的任务是基于截获的开源情报，调动强大的逻辑推理能力，补充完善情报素材，输出《深度研判专报》。
                【输出强制要求】必须包含以下 5 个模块（使用 Markdown 排版，语气极其冷峻客观，使用情报简报的文字风格）：
                1. 🌍 事件背景全貌：该事件的客观全要素情报全貌，深层政治或经济背景。
                2. 💰 潜在利益链推演：事件各相关方的内部深层考量。请站在事件相关方的利益角度，开展严谨的分析研判。
                3. 👤 对策建议：站在宏观战略和国家利益角度，提出该事件的潜在影响及应对措施的相关对策建议。
                4. 🤝 HUMINT 接触突破口 (绝密操作指引)：如果要派特工在线上或线下了解更深层次的情报，应该如何找到并接近该信息源并建立合作，建议采取什么伪装身份（Cover）？切入点是什么？
                5. 🔗 交叉验证建议：为了核实真伪，特工应去查阅哪些具体的开源数据库（列出方向）？
                """
                claude_user_message = f"""
                【原始线索】：
                - 标题：{card['title']}
                - 摘要：{card['summary']}
                - 来源频道：{card['source']}
                请开始撰写《深度研判专报》。
                """
                client_claude = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
                response = client_claude.messages.create(
                    model="claude-opus-4-6", # 或者最新的 claude-3-5-sonnet-latest
                    max_tokens=4096,
                    system=claude_system_prompt,
                    messages=[{"role": "user", "content": claude_user_message}]
                )
                final_content = response.content[0].text
                
                supabase.table("deep_dives_db").insert({
                    "report_id": card['id'], "agent_name": st.session_state.current_user, "content": final_content
                }).execute()
                
                st.success(f"🔥 Claude 引擎挖掘完毕！已将此情报永久刻录至团队档案库。")
                st.markdown(final_content)
            except Exception as e:
                st.error(f"Claude 引擎故障：{e}")
                final_content = ""

    if final_content:
        st.markdown("---")
        docx_data = generate_word_doc(card['title'], final_content)
        st.download_button(
            label="📥 导出为 Word 文档 (.docx)", data=docx_data, file_name=f"HUMINT专报_{card['id']}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", type="primary"
        )