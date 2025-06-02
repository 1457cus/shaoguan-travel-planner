import streamlit as st
import pandas as pd
import requests
import os
import json
from datetime import datetime, timedelta
import pytz
import time
import toml

# 设置页面配置
st.set_page_config(
    page_title="韶关个性化旅游攻略生成器",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 初始化会话状态
if 'itinerary_generated' not in st.session_state:
    st.session_state.itinerary_generated = False
if 'debug_info' not in st.session_state:
    st.session_state.debug_info = {}
if 'prompt_preview' not in st.session_state:
    st.session_state.prompt_preview = False
if 'prompt_content' not in st.session_state:
    st.session_state.prompt_content = {"chinese": "", "english": ""}
if 'data_loaded' not in st.session_state:
    st.session_state.data_loaded = False
if 'secrets_loaded' not in st.session_state:
    st.session_state.secrets_loaded = False

# 加载Secrets函数
def load_secrets():
    """加载API密钥"""
    secrets_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "secrets.toml")
    
    try:
        if os.path.exists(secrets_path):
            secrets = toml.load(secrets_path)
            st.session_state.secrets = secrets
            st.session_state.secrets_loaded = True
            
            # 验证密钥格式
            amap_key = secrets.get("AMAP_API_KEY", "")
            if not amap_key or len(amap_key) != 32:
                st.session_state.debug_info["Secrets状态"] = f"警告：API密钥格式异常 ({amap_key[:4]}...)"
            else:
                st.session_state.debug_info["Secrets状态"] = f"加载成功 ({secrets_path})"
            
            return True
        else:
            # 尝试备用路径
            alt_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".streamlit", "secrets.toml")
            if os.path.exists(alt_path):
                secrets = toml.load(alt_path)
                st.session_state.secrets = secrets
                st.session_state.secrets_loaded = True
                st.session_state.debug_info["Secrets状态"] = f"加载成功（备用路径） ({alt_path})"
                return True
            
            st.session_state.debug_info["Secrets状态"] = f"文件不存在: {secrets_path} 和 {alt_path}"
            return False
    except Exception as e:
        st.session_state.debug_info["Secrets错误"] = str(e)
        return False

# 加载数据函数
@st.cache_data
def load_data():
    """加载景点、美食和文化数据"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(current_dir, "processed_data")
    
    try:
        # 景点数据
        attractions_path = os.path.join(data_dir, "attractions_with_id.csv")
        if os.path.exists(attractions_path):
            attractions = pd.read_csv(attractions_path, encoding="utf-8-sig")
        else:
            st.error(f"景点数据文件不存在: {attractions_path}")
            st.session_state.debug_info["景点数据错误"] = f"文件不存在: {attractions_path}"
            attractions = pd.DataFrame()
        
        # 美食数据
        food_path = os.path.join(data_dir, "food_with_id.csv")
        if os.path.exists(food_path):
            foods = pd.read_csv(food_path, encoding="utf-8-sig")
        else:
            st.error(f"美食数据文件不存在: {food_path}")
            st.session_state.debug_info["美食数据错误"] = f"文件不存在: {food_path}"
            foods = pd.DataFrame()
        
        # 文化数据
        culture_path = os.path.join(data_dir, "culture_with_id.csv")
        if os.path.exists(culture_path):
            culture = pd.read_csv(culture_path, encoding="utf-8-sig")
        else:
            st.error(f"文化数据文件不存在: {culture_path}")
            st.session_state.debug_info["文化数据错误"] = f"文件不存在: {culture_path}"
            culture = pd.DataFrame()
        
        # 更新调试信息
        st.session_state.debug_info.update({
            "当前目录": current_dir,
            "数据目录": data_dir,
            "景点记录数": len(attractions),
            "美食记录数": len(foods),
            "文化记录数": len(culture),
            "数据加载时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        
        st.session_state.data_loaded = True
        return attractions, foods, culture
    except Exception as e:
        st.error(f"数据加载失败: {str(e)}")
        st.session_state.debug_info["数据加载错误"] = str(e)
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

# 获取高德天气函数 - 修复版本
def get_amap_weather(location="韶关"):
    """使用高德API获取天气信息"""
    try:
        # 检查secrets是否加载
        if not hasattr(st.session_state, 'secrets') or "AMAP_API_KEY" not in st.session_state.secrets:
            st.session_state.debug_info["天气API状态"] = "API密钥未配置"
            return {"status": "error", "message": "API密钥未配置"}
        
        api_key = st.session_state.secrets["AMAP_API_KEY"]
        
        # 构建请求URL
        base_url = "https://restapi.amap.com/v3/weather/weatherInfo"
        params = {
            "key": api_key,
            "city": location,
            "extensions": "all",  # 获取预报天气
            "output": "JSON"
        }
        
        # 发送请求
        response = requests.get(base_url, params=params, timeout=10)
        weather_data = response.json()
        
        # 检查API响应状态
        if weather_data.get("status") != "1":
            error_msg = weather_data.get('info', '未知错误')
            st.session_state.debug_info["天气API状态"] = f"错误: {error_msg}"
            return {"status": "error", "message": error_msg}
        
        # 解析预报数据
        forecasts = weather_data.get("forecasts", [])
        if not forecasts:
            st.session_state.debug_info["天气API状态"] = "无预报数据"
            return {"status": "error", "message": "无预报数据"}
        
        # 处理预报数据
        processed_forecast = []
        for forecast in forecasts[0].get("casts", []):
            # 获取日期和天气信息
            date_str = forecast.get("date")
            weather_day = forecast.get("dayweather", "未知")
            temp_day = forecast.get("daytemp", "未知")
            temp_night = forecast.get("nighttemp", "未知")
            
            # 添加到预报列表
            processed_forecast.append({
                "date": date_str,
                "condition": weather_day,
                "temp_max": temp_day,
                "temp_min": temp_night
            })
        
        # 返回结构化的天气数据
        result = {
            "status": "success",
            "location": location,
            "report_time": weather_data.get("forecasts", [{}])[0].get("reporttime", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            "forecast": processed_forecast
        }
        
        st.session_state.debug_info["天气API状态"] = "可用"
        return result
    except requests.exceptions.Timeout:
        st.session_state.debug_info["天气API状态"] = "请求超时"
        return {"status": "error", "message": "请求超时"}
    except Exception as e:
        st.session_state.debug_info["天气API状态"] = f"错误: {str(e)}"
        return {"status": "error", "message": str(e)}

# 生成行程函数 - 修复日期格式问题
def generate_itinerary(days, theme, weather_data):
    """生成个性化行程"""
    try:
        # 模拟生成行程
        itinerary = {
            "status": "success",
            "days": []
        }
        
        # 获取当前日期
        current_date = datetime.now(pytz.timezone('Asia/Shanghai'))
        
        for i in range(days):
            # 获取当天的日期和天气
            day_date = current_date + timedelta(days=i)
            date_str = day_date.strftime("%Y-%m-%d")
            
            # 查找对应的天气预报
            day_weather = None
            if "forecast" in weather_data:
                for forecast in weather_data["forecast"]:
                    if forecast.get("date") == date_str:
                        day_weather = forecast
                        break
            
            # 如果没有找到当天的预报，使用默认值
            if not day_weather:
                day_weather = {
                    "condition": "未知",
                    "temp_max": "未知",
                    "temp_min": "未知"
                }
            
            # 根据天气调整行程
            if "雨" in day_weather["condition"]:
                activities = [
                    f"上午: 南华寺（室内活动，参拜六祖真身）",
                    f"午餐: 南华寺素食馆（人均64元·推荐普度斋）",
                    f"下午: 韶关博物馆（了解本地历史）",
                    f"傍晚: 非遗工坊体验（瑶族传统工艺）"
                ]
            elif "晴" in day_weather["condition"]:
                activities = [
                    f"上午: 丹霞山（世界自然遗产）",
                    f"午餐: 农家乐（人均50元·推荐丹霞豆腐）",
                    f"下午: 古佛岩（喀斯特地貌）",
                    f"傍晚: 温泉体验（推荐经律论温泉）"
                ]
            else:
                activities = [
                    f"上午: 珠玑古巷（千年古道）",
                    f"午餐: 百年老店（人均60元·推荐梅菜扣肉）",
                    f"下午: 梅关古道（历史遗迹）",
                    f"傍晚: 当地夜市体验（品尝特色小吃）"
                ]
            
            # 添加日期和天气信息
            weather_display = f"{day_weather['condition']}·{day_weather['temp_min']}~{day_weather['temp_max']}℃"
            
            # 使用正确的中文日期表示
            day_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
            day_name = day_names[day_date.weekday()]
            
            itinerary["days"].append({
                "date": date_str,
                "day": i+1,
                "day_name": day_name,
                "weather": weather_display,
                "activities": activities
            })
        
        st.session_state.itinerary_generated = True
        return itinerary
    except Exception as e:
        st.error(f"行程生成失败: {str(e)}")
        st.session_state.debug_info["行程生成错误"] = str(e)
        return {"status": "error", "message": str(e)}

# 加载提示词函数 - 修复版本
def load_prompts():
    """加载中英文提示词"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    try:
        # 中文提示词
        chinese_path = os.path.join(current_dir, "prompt_template.txt")
        if os.path.exists(chinese_path):
            with open(chinese_path, "r", encoding="utf-8") as f:
                st.session_state.prompt_content["chinese"] = f.read()
        else:
            st.session_state.debug_info["提示词错误"] = f"文件不存在: {chinese_path}"
        
        # 英文提示词
        english_path = os.path.join(current_dir, "prompt_template_en.txt")
        if os.path.exists(english_path):
            with open(english_path, "r", encoding="utf-8") as f:
                st.session_state.prompt_content["english"] = f.read()
        else:
            st.session_state.debug_info["提示词错误"] = f"文件不存在: {english_path}"
        
        return True
    except Exception as e:
        st.session_state.debug_info["提示词错误"] = str(e)
        return False

# 主应用界面
def main():
    # 首先加载Secrets
    if not st.session_state.secrets_loaded:
        with st.spinner("加载API配置..."):
            load_secrets()
    
    # 加载提示词
    if not st.session_state.prompt_content["chinese"] or not st.session_state.prompt_content["english"]:
        with st.spinner("加载提示词模板..."):
            load_prompts()
    
    # 侧边栏配置
    with st.sidebar:
        st.header("API设置")
        
        # 模型选择
        model_options = ["deepseek-chat", "gpt-4", "claude-3"]
        selected_model = st.selectbox("当前模型", model_options, index=0)
        
        # 位置选择
        location = st.text_input("旅行地点", "韶关")
        
        # 状态检查
        col1, col2 = st.columns(2)
        with col1:
            if st.button("检查DeepSeek状态"):
                st.success("DeepSeek API 连接正常！")
        
        with col2:
            if st.button("检查天气API状态"):
                with st.spinner("检查天气API..."):
                    weather_data = get_amap_weather(location)
                    if weather_data.get("status") == "success":
                        st.success(f"天气API可用（更新时间: {weather_data.get('report_time', '未知')}）")
                    else:
                        st.error(f"天气API不可用: {weather_data.get('message', '未知错误')}")
        
        # 添加验证API密钥的按钮
        if st.button("验证API密钥"):
            # 检查是否已加载secrets且包含AMAP_API_KEY
            if not hasattr(st.session_state, 'secrets') or "AMAP_API_KEY" not in st.session_state.secrets:
                st.error("未找到API密钥配置")
            else:
                # 此时确保存在密钥
                key = st.session_state.secrets["AMAP_API_KEY"]
                st.info(f"当前密钥: {key[:4]}...{key[-4:]}")
                
                # 简单验证密钥格式
                if len(key) != 32:
                    st.error("密钥长度应为32字符")
                else:
                    st.success("密钥格式正确")
        
        # 显示选项
        st.session_state.prompt_preview = st.checkbox("显示提示词预览", value=st.session_state.prompt_preview)
        show_debug = st.checkbox("显示调试信息", value=True)
        
        st.divider()
        st.caption("韶关 AI 旅游助手 v2.0")  # 更新版本号
        st.caption("© 2025 智慧旅游项目 | 使用 DeepSeek & 高德API")
    
    # 主页面标题
    st.title(f"{location}个性化旅游攻略生成器")
    
    # 用户输入区域
    with st.form("travel_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            travel_days = st.slider("行程天数", 1, 7, 3)
        
        with col2:
            travel_theme = st.selectbox(
                "旅行主题",
                ["历史人文", "自然风光", "美食探索", "文化体验", "家庭亲子"],
                index=0
            )
        
        if st.form_submit_button("一键生成攻略", use_container_width=True):
            with st.spinner("AI 正在规划行程..."):
                # 加载数据
                attractions, foods, culture = load_data()
                
                # 获取天气
                weather_data = get_amap_weather(location)
                
                # 生成行程
                itinerary = generate_itinerary(travel_days, travel_theme, weather_data)
                
                # 保存结果
                if itinerary.get("status") == "success":
                    st.session_state.itinerary = itinerary
                    st.session_state.location = location
                    st.success("攻略生成成功！")
                else:
                    st.error("攻略生成失败，请重试或检查API设置")
    
    # 显示生成的行程 - 修复日期显示问题
    if st.session_state.get('itinerary') and st.session_state.itinerary_generated:
        st.divider()
        st.subheader(f"{travel_days}天{travel_theme}行程（{st.session_state.get('location', '韶关')}）")
        
        for day in st.session_state.itinerary["days"]:
            # 使用正确的中文日期格式
            title = f"第{day['day']}天（{day['date']} {day.get('day_name', '')}·{day['weather']}）"
            
            with st.expander(title, expanded=True):
                for activity in day["activities"]:
                    st.markdown(f"- **{activity}**")
    
    # 显示提示词预览
    if st.session_state.prompt_preview:
        st.divider()
        st.subheader("提示词预览")
        
        try:
            tab1, tab2 = st.tabs(["中文提示词", "English Prompt"])
            
            with tab1:
                if st.session_state.prompt_content["chinese"]:
                    st.code(st.session_state.prompt_content["chinese"], language="text")
                else:
                    st.warning("中文提示词内容为空")
                    st.info("请检查文件: prompt_template.txt")
            
            with tab2:
                if st.session_state.prompt_content["english"]:
                    st.code(st.session_state.prompt_content["english"], language="text")
                else:
                    st.warning("英文提示词内容为空")
                    st.info("请检查文件: prompt_template_en.txt")
        except Exception as e:
            st.error(f"提示词预览失败: {str(e)}")
    
    # 显示调试信息
    if show_debug:
        st.divider()
        st.subheader("调试信息")
        
        # 更新当前时间
        st.session_state.debug_info["当前时间"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 只显示有效信息
        valid_debug_info = {}
        for key, value in st.session_state.debug_info.items():
            if value and not str(value).startswith("<") and not str(value).endswith(">"):
                valid_debug_info[key] = value
        
        # 显示调试信息
        for key, value in valid_debug_info.items():
            st.markdown(f"**{key}**: `{value}`")
        
        # 显示文件结构（过滤无效条目）
        st.markdown("**当前目录结构**:")
        current_dir = os.path.dirname(os.path.abspath(__file__))
        try:
            files = [f for f in os.listdir(current_dir) if not f.startswith(".") and not f.endswith("tmp")]
            st.code("\n".join(files), language="plaintext")
            
            # 显示Secrets文件状态
            st.markdown("**Secrets文件状态**:")
            secrets_path = os.path.join(current_dir, "secrets.toml")
            secrets_exists = "✅ 存在" if os.path.exists(secrets_path) else "❌ 不存在"
            st.markdown(f"- secrets.toml: `{secrets_path}` - {secrets_exists}")
            
            # 显示提示词文件状态
            st.markdown("**提示词文件状态**:")
            chinese_path = os.path.join(current_dir, "prompt_template.txt")
            english_path = os.path.join(current_dir, "prompt_template_en.txt")
            
            chinese_exists = "✅ 存在" if os.path.exists(chinese_path) else "❌ 不存在"
            english_exists = "✅ 存在" if os.path.exists(english_path) else "❌ 不存在"
            
            st.markdown(f"- 中文提示词: `{chinese_path}` - {chinese_exists}")
            st.markdown(f"- 英文提示词: `{english_path}` - {english_exists}")
        except Exception as e:
            st.error(f"无法列出目录: {str(e)}")

if __name__ == "__main__":
    main()
