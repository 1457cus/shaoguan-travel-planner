import pandas as pd
from pathlib import Path

def clean_culture():
    # 设置路径 - 符合新目录结构
    base_dir = Path(__file__).parent.parent
    input_path = base_dir / "raw_data" / "sg_culture.csv"
    output_path = base_dir / "cleaned_data" / "sg_culture_cleaned.csv"
    
    # 确保输出目录存在
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        # 读取原始数据
        df = pd.read_csv(input_path, encoding="utf-8")
        
        # === 数据清洗规则 ===
        # 1. 去除隐藏字符
        if '传承地' in df.columns:
            df['传承地'] = df['传承地'].str.replace(r'[\t\"]', '', regex=True)
        
        # 2. 标准化类别
        if '类别' in df.columns:
            df['类别'] = df['类别'].str.strip().replace({
                ' 手工艺': '手工艺',
                '节庆民俗': '民俗',
                '民俗节庆': '民俗'
            })
        
        # 3. 统一级别格式
        if '级别' in df.columns:
            df['级别'] = df['级别'].str.replace('国家非遗', '国家级').replace('市非遗', '市级')
        
        # 4. 处理备注信息
        if '备注' in df.columns:
            df['备注'] = df['备注'].fillna('')  # 空值填充
        
        # 5. 名称去空格
        if '名称' in df.columns:
            df['名称'] = df['名称'].str.strip()
        
        # === 保存清洗结果 ===
        df.to_csv(output_path, index=False, encoding="utf-8-sig")
        print(f"✅ 文化数据清洗完成！生成文件：{output_path}")
        
    except Exception as e:
        print(f"❌ 清洗失败：{str(e)}")
        print("请检查：")
        print("1. 当前目录是否存在 sg_culture.csv")
        print("2. CSV文件是否用逗号分隔")
        print("3. 文件编码是否为UTF-8")

if __name__ == "__main__":
    clean_culture()