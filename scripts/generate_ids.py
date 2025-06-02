""" 
韶关旅游数据唯一标识符生成脚本 - 增强版
生成规则：SG-[类型代码][子类代码]-[哈希特征码]-[序号]
"""

import pandas as pd
from hashlib import blake2b
from pathlib import Path
import os

# ====================== 配置区 ======================
# 路径配置 - 符合新目录结构
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "cleaned_data"  # 清洗后数据目录
OUTPUT_DIR = BASE_DIR / "processed_data"   # 输出目录
# ===================================================

ENCODING = "utf-8-sig"  # 处理含 BOM 头的 UTF-8 文件

# 类型映射配置 (统一定义)
TYPE_CONFIG = {
    "attractions": {
        "file": "sg_attractions_cleaned.csv",
        "type_code": "A",
        "subtype_field": "主类型",
        "subtype_map": {
            "自然": "N",
            "历史": "H",
            "亲子": "K",
            "自然/历史": "NH",
            "温泉": "S",  # 新增类型
            "工业": "I"   # 新增类型
        }
    },
    "food": {
        "file": "sg_food_cleaned.csv",
        "type_code": "F",
        "subtype_field": "类型",
        "subtype_map": {
            "农家菜": "N",
            "西餐": "W",
            "粤菜": "Y",
            "早茶": "Z",
            "茶餐厅": "C",
            "日式火锅": "R",
            "素食": "S",
            "炖品": "D",
            "火锅": "H",
            "烧烤": "B",
            "粥城": "M",  # 新增类型
            "点心": "X"    # 新增类型
        }
    },
    "culture": {
        "file": "sg_culture_cleaned.csv",
        "type_code": "C",
        "subtype_field": "类别",
        "subtype_map": {
            "民俗": "M",
            "传统戏剧": "X",
            "传统技艺": "J",
            "传统舞蹈": "W",
            "手工艺": "S",
            "非遗": "F"  # 新增类型
        }
    }
}
# ===================================================

# 全局计数器
counter = 0

def generate_id(row, data_type):
    """生成带分类结构的唯一标识符"""
    global counter
    config = TYPE_CONFIG[data_type]
    
    # 获取子类代码
    raw_subtype = str(row.get(config["subtype_field"], "未知")).strip()
    
    # 处理复合类型（如"自然/历史"）
    if "/" in raw_subtype:
        primary_subtype = raw_subtype.split("/")[0]
    else:
        primary_subtype = raw_subtype
        
    subtype = config["subtype_map"].get(primary_subtype, "O")  # O表示其他
    
    # 确定名称字段
    name_field = "店名" if data_type == "food" else "名称"
    name_value = str(row.get(name_field, "")).strip()
    
    # 生成特征哈希码（名称前10字符的BLAKE2哈希）
    name_part = name_value[:10] if name_value else "Unknown"
    hash_hex = blake2b(name_part.encode(), digest_size=2).hexdigest().upper()
    
    # 生成序号
    counter += 1
    return f"SG-{config['type_code']}{subtype}-{hash_hex}-{counter:04d}"

def process_data(data_type):
    """处理指定类型数据"""
    global counter
    
    config = TYPE_CONFIG[data_type]
    input_path = DATA_DIR / config["file"]
    output_path = OUTPUT_DIR / f"{data_type}_with_id.csv"
    
    # 确保输出目录存在
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # 文件存在性检查
    if not input_path.exists():
        print(f"⛔ 文件 {input_path} 未找到，请检查：")
        print(f"   - 文件路径: {input_path}")
        print(f"   - 是否执行过数据清洗")
        return
    
    try:
        # 读取数据
        df = pd.read_csv(input_path, encoding=ENCODING)
        
        # 检查必要字段是否存在
        required_fields = ["名称"] if data_type != "food" else ["店名"]
        required_fields.append(config["subtype_field"])
        
        missing_fields = [field for field in required_fields if field not in df.columns]
        if missing_fields:
            print(f"⛔ {data_type} 数据缺失必要字段: {', '.join(missing_fields)}")
            return
        
        # 生成唯一编码
        df["唯一编码"] = df.apply(lambda row: generate_id(row, data_type), axis=1)
        
        # 保存结果
        df.to_csv(output_path, index=False, encoding=ENCODING)
        print(f"✅ {data_type} 数据处理完成，生成 {len(df)} 条编码")
        print(f"   输出文件: {output_path}")
        
    except Exception as e:
        print(f"❌ {data_type} 数据处理失败：{str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # 确保数据目录存在
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    print("="*40)
    print("开始处理旅游数据标识符...")
    
    # 重置计数器
    counter = 0
    
    # 按顺序处理所有数据类型
    process_data("attractions")
    process_data("food")
    process_data("culture")
    
    print("="*40)
    print(f"处理完成！共生成 {counter} 个唯一标识符")