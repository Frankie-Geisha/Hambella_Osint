import os, json, requests, sys
from datetime import datetime, timedelta, timezone
from supabase import create_client, Client
import anthropic

# 🌟 V6.1 自动化内参编辑部：每日/每周简报生成引擎
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
FEISHU_WEBHOOK = os.environ.get("FEISHU_WEBHOOK")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
client_claude = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

def generate_briefing(period_type):
    now_utc = datetime.now(timezone.utc)
    
    # 1. 划定捞取数据的时间范围
    if period_type == "daily":
        start_time = now_utc - timedelta(days=1)
        title_header = f"🌅 花魁每日战略简报 ({now_utc.astimezone(timezone(timedelta(hours=8))).strftime('%Y-%m-%d')})"
    elif period_type == "weekly":
        start_time = now_utc - timedelta(days=7)
        title_header = f"🗓️ 花魁周度战略推演与预测 ({now_utc.astimezone(timezone(timedelta(hours=8))).strftime('%Y年第%W周')})"
    else:
        return

    # 2. 从情报库捞出这期间的所有情报（按分数从高到低排列）
    start_time_str = start_time.isoformat()
    res = supabase.table("intelligence_db").select("*").gte("created_at", start_time_str).order("score", desc=True).execute()
    records = res.data
    
    if not records:
        print(f"没有足够的原始数据生成 {period_type} 简报。")
        return

    # 3. 组装给 Claude 的原料 (为防超长，只取前 100 条最高价值或有特殊意义的信息)
    raw_text_for_ai = ""
    for r in records[:100]:
        raw_text_for_ai += f"【{r['score']}分】 标题：{r['title']} | 摘要：{r['summary']}\n"

    # 4. 针对日报和周报下达不同的 Claude 脑机接口指令
    if period_type == "daily":
        system_prompt = """
        你是一名顶尖的情报简报官。请将过去24小时截获的碎片化情报，融合成一份《每日战略简报》。
        要求：
        1. 抛弃流水账！把同一事件/领域的卡片有机结合，按“高危冲突”、“地缘博弈”、“宏观异动”分类。
        2. 即便是低分消息，如果能拼凑出某种微弱的趋势（比如某地区连续出现小规模暴乱），也要敏锐地提炼出来。
        3. 字数控制在1500字左右，必须是纯正的情报内参文风，拒绝AI废话。
        """
    else:
        system_prompt = """
        你是最高级别的地缘战略预测大师。请根据过去7天截获的全部情报，出具《周度战略推演与预测》。
        必须包含以下三个板块：
        【一、 本周核心暗流复盘】：不要简单罗列，指出这周发生了什么本质性的转折。
        【二、 关键博弈方底牌透视】：分析主要国家或势力的真实目的和受挫点。
        【三、 未来一周沙盘预测】：必须基于本周的低分或高分线索，给出3条关于下周极具前瞻性、科学合理且精准的“预警/预测”。
        """

    print(f"🧠 正在呼叫 Claude 撰写 {period_type} 简报...")
    response = client_claude.messages.create(
        model="claude-3-5-sonnet-20241022", max_tokens=3000,
        system=system_prompt, messages=[{"role": "user", "content": f"以下是原始情报数据：\n{raw_text_for_ai}"}]
    )
    final_content = response.content[0].text
    
    # 5. 存入 Supabase，供网页大厅展示
    full_report = f"# {title_header}\n\n{final_content}"
    supabase.table("briefings_db").insert({"period": period_type, "content": full_report}).execute()
    
    # 6. 直接同步推送到飞书！
    if FEISHU_WEBHOOK:
        payload = {
            "msg_type": "post",
            "content": {"post": {"zh_cn": {"title": title_header, "content": [[{"tag": "text", "text": final_content}]]}}}
        }
        requests.post(FEISHU_WEBHOOK, json=payload)
        print("📣 简报已成功推送到飞书！")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        generate_briefing(sys.argv[1])
