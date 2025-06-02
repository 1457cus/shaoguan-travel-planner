import pandas as pd
from pathlib import Path

def clean_food():
    # 设置路径 - 符合新目录结构
    base_dir = Path(__file__).parent.parent
    input_path = base_dir / "raw_data" / "sg_food.csv"
    output_path = base_dir / "cleaned_data" / "sg_food_cleaned.csv"
    
    # 确保输出目录存在
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        # 读取原始数据
        df = pd.read_csv(input_path, encoding="utf-8")
        
        # 清洗规则
        df['店名'] = df['店名'].str.replace(r'\(.*店\)', '', regex=True)  # 移除分店信息
        
        # 处理人均消费字段
        if '人均消费' in df.columns:
            df['人均消费'] = df['人均消费'].str.replace('¥', '').astype(int)
        elif '人均' in df.columns:
            df.rename(columns={'人均': '人均消费'}, inplace=True)
            df['人均消费'] = df['人均消费'].str.replace('¥', '').astype(int)
        
        # 处理特色菜字段
        if '特色菜' in df.columns:
            df['特色菜'] = df['特色菜'].str.replace(' ', '、')  # 空格替换为顿号
        elif '推荐菜' in df.columns:
            df.rename(columns={'推荐菜': '特色菜'}, inplace=True)
            df['特色菜'] = df['特色菜'].str.replace(' ', '、')
        
        # 生成价格区间 (规则：原价×0.8-原价×1.8)
        df['人均最低(元)'] = (df['人均消费'] * 0.8).round().astype(int)
        df['人均最高(元)'] = (df['人均消费'] * 1.8).round().astype(int)
        
        # 分类标记
        df['类型'] = df.apply(lambda x: 
            "火锅" if "火锅" in x['店名'] else
            "西餐" if "西餐" in x['店名'] or "牛排" in x['店名'] else
            "粤菜", axis=1)
        
        # 保存结果
        df.to_csv(output_path, index=False, encoding="utf-8-sig")
        print(f"✅ 美食数据清洗完成！生成文件：{output_path}")
        
    except Exception as e:
        print(f"❌ 清洗失败：{str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    clean_food()