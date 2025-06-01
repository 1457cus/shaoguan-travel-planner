import streamlit as st
import pandas as pd
import sys
import os
from pathlib import Path
import time
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import webbrowser
import re
import json
import random

# -------------------- 路径配置 --------------------
current_dir = Path(__file__).parent
data_dir = current_dir / "data"
attractions_path = data_dir / "sg_attractions_cleaned.csv"
food_path = data_dir / "sg_food_cleaned.csv"
culture_path = data_dir / "sg_culture_cleaned.csv"

# -------------------- 多语言支持 --------------------
LANGUAGE_PACKS = {
    "zh": {
        "title": "🚩 韶关个性化旅游攻略生成器",
        "days_label": "旅行天数",
        "budget_label": "预算（元）",
        "interest_label": "兴趣主题",
        "interest_options": ["历史", "自然", "美食", "亲子"],
        "special_needs": "特殊需求",
        "elderly": "包含老人",
        "children": "包含儿童",
        "cooling": "避暑需求",
        "generate_btn": "✨ 一键生成攻略",
        "footer": "韶关 AI 旅游助手 v1.6 | 技术支持: 旅游科技团队",
        "weather_error": "天气API暂时不可用，使用模拟数据",
        "no_special_weather": "无特殊天气提示",
        "download_btn": "📥 下载攻略",
        "generating": "AI 正在规划行程...",
        "success": "✅ 攻略生成成功！",
        "fail": "生成失败：",
        "check_api": "🌐 检查 DeepSeek 状态"
    },
    "en": {
        "title": "🚩 Shaoguan AI Travel Planner",
        "days_label": "Travel Days",
        "budget_label": "Budget (¥)",
        "interest_label": "Interest Theme",
        "interest_options": ["History", "Nature", "Food", "Family"],
        "special_needs": "Special Requirements",
        "elderly": "With Elderly",
        "children": "With Children",
        "cooling": "Cooling Needs",
        "generate_btn": "✨ Generate Itinerary",
        "footer": "Shaoguan AI Travel Assistant v1.6 | Tech Support: TravelTech Team",
        "weather_error": "Weather API unavailable, using simulated data",
        "no_special_weather": "No special weather advice",
        "download_btn": "📥 Download Itinerary",
        "generating": "AI is planning your trip...",
        "success": "✅ Itinerary generated successfully!",
        "fail": "Generation failed: ",
        "check_api": "🌐 Check DeepSeek Status"
    }
}

# -------------------- 高德天气API配置 --------------------
GAODE_API_KEY = st.secrets.get("GAODE_KEY", "your_gaode_api_key")  # 添加到Streamlit Secrets
GAODE_WEATHER_URL = "https://restapi.amap.com/v3/weather/weatherInfo"
SHAOGUAN_CITY_CODE = "440200"  # 韶关市行政区划代码

# -------------------- 页面配置 --------------------
st.set_page_config(page_title="韶关AI旅游助手", layout="wide")

# -------------------- 环境变量处理 --------------------
print("[DEBUG] 尝试获取 API 密钥...")
deepseek_api_key = st.secrets.get("DEEPSEEK_KEY", None)
if not deepseek_api_key:
    st.error("未找到 DeepSeek API 密钥，请检查 Streamlit Secrets 设置")
    st.stop()
else:
    print(f"[DEBUG] 从 Streamlit Secrets 获取密钥: {deepseek_api_key[:4]}...")

# -------------------- DeepSeek API 客户端 --------------------
DEEPSEEK_API_URL = "https://api.deepseek.com/v1"
MODEL_NAME = "deepseek-chat"

class DeepSeekClient:
    def __init__(self, api_key, base_url=DEEPSEEK_API_URL):
        self.api_key = api_key
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=20),
        retry=retry_if_exception_type((httpx.ConnectError, httpx.TimeoutException))
    )
    def chat_completions(self, model, messages, temperature=0.7, max_tokens=2000):
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        try:
            with httpx.Client(timeout=60.0) as client:
                response = client.post(url, headers=self.headers, json=payload)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            st.error(f"API 请求失败: HTTP {e.response.status_code}")
            st.json(e.response.json())
            raise
        except httpx.RequestError as e:
            st.error(f"网络连接错误: {str(e)}")
            raise

# 创建客户端实例
client = DeepSeekClient(api_key=deepseek_api_key)

# -------------------- 天气服务 --------------------
def get_gaode_weather(lang="zh"):
    """使用高德API获取天气预报"""
    try:
        params = {
            "key": GAODE_API_KEY,
            "city": SHAOGUAN_CITY_CODE,
            "extensions": "all",  # 获取预报天气
            "output": "JSON"
        }
        
        response = httpx.get(GAODE_WEATHER_URL, params=params, timeout=10)
        data = response.json()
        
        if data["status"] == "1" and data["forecasts"]:
            forecast = data["forecasts"][0]["casts"]
            weather_advice = []
            
            for i, day in enumerate(forecast):
                day_weather = day["dayweather"]
                night_weather = day["nightweather"]
                day_temp = int(day["daytemp"])
                
                # 判断是否有雨
                has_rain = "雨" in day_weather or "雨" in night_weather
                
                # 判断是否高温
                is_hot = day_temp > 30
                
                if has_rain:
                    advice = "建议室内景点优先" if lang == "zh" else "Suggest indoor attractions first"
                    weather_advice.append(f"第{i+1}天: {day_weather}→{night_weather} - {advice}")
                elif is_hot:
                    advice = "建议避暑景点和水上活动" if lang == "zh" else "Suggest cooling attractions and water activities"
                    weather_advice.append(f"第{i+1}天: 高温{day_temp}°C - {advice}")
            
            return "\n".join(weather_advice) if weather_advice else None
        else:
            print(f"高德API错误: {data.get('info', '未知错误')}")
            return None
            
    except Exception as e:
        print(f"高德API请求失败: {str(e)}")
        return None

def simulate_weather_forecast(lang="zh"):
    """天气API不可用时的模拟数据"""
    weather_types_zh = ["晴", "多云", "小雨", "中雨", "雷阵雨", "阴"]
    weather_types_en = ["Sunny", "Cloudy", "Light Rain", "Moderate Rain", "Thunderstorm", "Overcast"]
    
    weather_types = weather_types_zh if lang == "zh" else weather_types_en
    forecasts = []
    
    for i in range(3):
        weather = random.choice(weather_types)
        day_temp = random.randint(25, 35)
        has_rain = "雨" in weather or "Rain" in weather
        is_hot = day_temp > 30
        
        forecast = {
            "date": f"第{i+1}天" if lang == "zh" else f"Day {i+1}",
            "weather": weather,
            "temp": day_temp,
            "has_rain": has_rain,
            "is_hot": is_hot
        }
        forecasts.append(forecast)
    
    weather_advice = []
    for day in forecasts:
        if day["has_rain"]:
            advice = "建议室内景点优先" if lang == "zh" else "Suggest indoor attractions first"
            weather_advice.append(f"{day['date']}: {day['weather']} - {advice}")
        elif day["is_hot"]:
            advice = "建议避暑景点和水上活动" if lang == "zh" else "Suggest cooling attractions and water activities"
            weather_advice.append(f"{day['date']}: {day['weather']} ({day['temp']}°C) - {advice}")
    
    return "\n".join(weather_advice) if weather_advice else None

def get_weather_forecast(lang="zh"):
    """获取天气预报（优先高德API，失败时使用模拟数据）"""
    # 尝试高德API
    api_result = get_gaode_weather(lang)
    if api_result:
        return api_result
    
    # 高德API失败时使用模拟数据
    print(LANGUAGE_PACKS[lang]["weather_error"])
    return simulate_weather_forecast(lang)

# -------------------- 数据加载与预处理 --------------------
def clean_text(text):
    if isinstance(text, str):
        return text.encode('utf-8', 'ignore').decode('utf-8')
    return text

def load_and_preprocess_data():
    """加载并预处理景点、美食、文化数据"""
    try:
        # 景点数据
        attractions = pd.read_csv(attractions_path, encoding="utf-8-sig")
        attractions.columns = [clean_text(col) for col in attractions.columns]
        attractions = attractions.applymap(clean_text)
        attractions["景点特色说明"] = attractions["景点特色说明"].fillna("暂无特色说明").astype(str)
        
        # 添加避暑指数
        attractions["避暑指数"] = attractions["景点特色说明"].apply(
            lambda x: 5 if "水上" in x or "漂流" in x or "泳池" in x else
                     4 if "森林" in x or "峡谷" in x or "瀑布" in x else
                     3 if "湖泊" in x or "溪流" in x or "湿地" in x else
                     2 if "溶洞" in x or "地下" in x else 1
        )
        
        # 美食数据
        foods = pd.read_csv(food_path, encoding="utf-8-sig")
        foods.columns = [clean_text(col) for col in foods.columns]
        foods = foods.applymap(clean_text)
        foods["特色菜"] = foods["特色菜"].fillna("暂无推荐菜")
        
        # 文化数据
        culture = pd.read_csv(culture_path, encoding="utf-8-sig")
        culture.columns = [clean_text(col) for col in culture.columns]
        culture = culture.applymap(clean_text)
        
        return attractions, foods, culture

    except Exception as e:
        st.error(f"数据加载失败：{str(e)}")
        st.stop()

# 加载数据
attractions, foods, culture = load_and_preprocess_data()

# -------------------- Streamlit 界面 --------------------
# 在侧边栏添加语言选择
with st.sidebar:
    language = st.radio("Language/语言", ["中文", "English"], index=0, key="language_selector")
    lang_code = "en" if language == "English" else "zh"
    texts = LANGUAGE_PACKS[lang_code]

st.title(texts["title"])

# 在侧边栏添加参数设置
with st.sidebar:
    st.header("旅行参数")
    days = st.slider(texts["days_label"], 1, 7, 3, key="days_slider")
    budget = st.number_input(texts["budget_label"], 500, 10000, 1500, key="budget_input")
    interest = st.selectbox(texts["interest_label"], texts["interest_options"], key="interest_select")
    
    st.divider()
    st.header(texts["special_needs"])
    has_elderly = st.checkbox(texts["elderly"], key="elderly_check")
    has_children = st.checkbox(texts["children"], key="children_check")
    need_cooling = st.checkbox(texts["cooling"], key="cooling_check")
    
    st.divider()
    st.header("API设置")
    st.success(f"✅ API 密钥已通过 Streamlit Secrets 获取")
    st.info(f"当前模型: {MODEL_NAME}")
    
    if st.button(texts["check_api"], key="api_status_button"):
        webbrowser.open_new_tab("https://platform.deepseek.com/api")
        st.toast("已在浏览器中打开 DeepSeek API 文档")
        
    # 添加天气API状态显示
    weather_status = "可用" if GAODE_API_KEY != "your_gaode_api_key" else "未配置"
    st.info(f"天气API状态: {weather_status}")

# -------------------- 动态生成提示词 --------------------
def build_prompt(days, budget, interest, lang="zh"):
    """构建 DeepSeek 提示词模板"""
    try:
        # 根据语言选择模板
        template_file = "prompt_template_en.txt" if lang == "en" else "prompt_template.txt"
        template_path = current_dir / template_file
        
        with open(template_path, "r", encoding="utf-8") as f:
            template = f.read()

        # 特殊需求处理
        special_requirements = []
        if has_elderly:
            special_requirements.append("减少步行，增加休息点" if lang == "zh" else "Less walking, more rest points")
        if has_children:
            special_requirements.append("添加亲子项目，安全第一" if lang == "zh" else "Add family-friendly activities, safety first")
        if need_cooling:
            special_requirements.append("避暑景点优先，避开高温时段" if lang == "zh" else "Prioritize cooling attractions, avoid peak heat hours")
            # 过滤高避暑指数的景点
            attractions_filtered = attractions[attractions["避暑指数"] >= 4]
        else:
            attractions_filtered = attractions
        
        # 天气建议
        weather_advice = get_weather_forecast(lang) or texts["no_special_weather"]
        
        # 安全抽样景点
        sample_size = min(3, len(attractions_filtered))
        if len(attractions_filtered) > 0:
            sampled_attractions = attractions_filtered.sample(sample_size) if sample_size > 0 else attractions_filtered.head(3)
            attractions_info = [
                f"{row['名称']}（{row.get('景点特色说明', '暂无说明')}" 
                for _, row in sampled_attractions.iterrows()
            ]
        else:
            attractions_info = ["丹霞山", "南华寺", "乳源大峡谷"] if lang == "zh" else ["Danxia Mountain", "Nanhua Temple", "Ruyuan Grand Canyon"]
        
        # 安全抽样餐厅
        sample_size = min(2, len(foods))
        if len(foods) > 0:
            sampled_foods = foods.sample(sample_size) if sample_size > 0 else foods.head(2)
            food_info = [
                f"{row['店名']}（人均{row.get('人均消费', '?')}元）"
                for _, row in sampled_foods.iterrows()
            ]
        else:
            food_info = ["韶关农家菜", "南华寺素食"] if lang == "zh" else ["Shaoguan Farmhouse Cuisine", "Nanhua Temple Vegetarian"]
        
        # 文化体验
        if len(culture) > 0:
            cultural_activity = culture.sample(1).iloc[0]["名称"]
        else:
            cultural_activity = "自由探索当地文化" if lang == "zh" else "Free exploration of local culture"

        return template.format(
            days=days,
            budget=budget,
            interest=interest,
            attractions="、".join(attractions_info),
            food="、".join(food_info),
            culture=cultural_activity,
            special_needs="\n".join(special_requirements) if special_requirements else ("无" if lang == "zh" else "None"),
            weather_advice=weather_advice
        )

    except Exception as e:
        st.error(f"提示词生成失败：{str(e)}")
        st.stop()

# -------------------- 生成攻略逻辑 --------------------
def get_ai_response(prompt):
    try:
        response = client.chat_completions(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=4000
        )
        return response
    except Exception as e:
        print(f"[ERROR] API 调用失败: {str(e)}")
        raise

if st.button(texts["generate_btn"], key="generate_button"):
    with st.spinner(texts["generating"]):
        try:
            prompt = build_prompt(days, budget, interest, lang_code)
            
            # 显示提示词预览（调试用）
            if st.sidebar.checkbox("显示提示词预览", key="prompt_preview"):
                st.sidebar.text_area("提示词内容", prompt, height=300, key="prompt_content")
            
            start_time = time.time()
            response = get_ai_response(prompt)
            elapsed = time.time() - start_time
            print(f"[DEBUG] API 响应时间: {elapsed:.2f} 秒")
            
            if 'choices' in response and len(response['choices']) > 0:
                itinerary = response['choices'][0]['message']['content']
                st.success(texts["success"])
                st.markdown(itinerary)
                
                # 添加下载按钮
                filename = f"韶关{days}日{interest}主题旅游攻略.md" if lang_code == "zh" else f"Shaoguan_{days}Day_{interest}_Itinerary.md"
                
                st.download_button(
                    texts["download_btn"],
                    itinerary, 
                    file_name=filename,
                    mime="text/markdown",
                    key="download_button"
                )
            else:
                st.error("API 响应格式异常，无法获取攻略内容")
                st.json(response)  # 显示原始响应用于调试
            
        except Exception as e:
            st.error(texts["fail"] + str(e))
            
            if st.button(texts["check_api"], key="api_check_button", help="点击在浏览器中打开 DeepSeek API 文档"):
                webbrowser.open_new_tab("https://platform.deepseek.com/api")
                st.toast("已在浏览器中打开 DeepSeek API 文档")

# -------------------- 页脚 --------------------
st.divider()
st.markdown(f"""
    <div style="text-align: center; color: #666; margin-top: 30px;">
        <p>{texts['footer']}</p>
        <p>© 2025 智慧旅游项目 | 使用 DeepSeek API</p>
    </div>
""", unsafe_allow_html=True)

# -------------------- 调试信息 --------------------
if st.sidebar.checkbox("显示调试信息", key="debug_info"):
    st.sidebar.divider()
    st.sidebar.subheader("调试信息")
    st.sidebar.write(f"当前目录: {current_dir}")
    st.sidebar.write(f"数据目录: {data_dir}")
    st.sidebar.write(f"景点记录数: {len(attractions)}")
    st.sidebar.write(f"美食记录数: {len(foods)}")
    st.sidebar.write(f"文化记录数: {len(culture)}")
    st.sidebar.write(f"天气API状态: {'可用' if GAODE_API_KEY != 'your_gaode_api_key' else '未配置'}")
    
    # 显示避暑景点
    if need_cooling:
        cooling_spots = attractions[attractions["避暑指数"] >= 4]
        st.sidebar.write(f"高避暑指数景点: {len(cooling_spots)}个")
        if len(cooling_spots) > 0:
            st.sidebar.dataframe(cooling_spots[["名称", "避暑指数"]].head(5))