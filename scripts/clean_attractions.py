import pandas as pd
from pathlib import Path

def clean_attractions():
    # 设置路径 - 符合新目录结构
    base_dir = Path(__file__).parent.parent
    input_path = base_dir / "raw_data" / "sg_attractions.csv"
    output_path = base_dir / "cleaned_data" / "sg_attractions_cleaned.csv"
    
    # 确保输出目录存在
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        # 读取CSV文件，处理特殊字符
        df = pd.read_csv(
            input_path,
            encoding="utf-8-sig",
            quotechar='"',
            escapechar='\\',
            on_bad_lines="warn"
        )

        # 处理字段中的特殊字符
        df["开放时间段"] = df["开放时间段"].str.replace(",", "，")
        df["景点特色说明"] = df["景点特色说明"].str.replace(",", "，").str.replace('"', "'")

        # 改进门票处理逻辑
        def parse_ticket_price(price_str):
            if pd.isna(price_str):
                return None, None
                
            price_str = str(price_str).strip()
            
            if "浮动" in price_str or "酒店" in price_str:
                return None, None
                
            if "免费" in price_str:
                return 0, 0
                
            if "-" in price_str:
                parts = price_str.split("-")
                try:
                    low = float(parts[0])
                    high = float(parts[1])
                    return low, high
                except ValueError:
                    return None, None
                    
            try:
                price = float(price_str)
                return price, price
            except ValueError:
                return None, None

        # 应用门票解析函数
        ticket_prices = df["门票(元)"].apply(parse_ticket_price)
        df["门票最低(元)"] = [p[0] for p in ticket_prices]
        df["门票最高(元)"] = [p[1] for p in ticket_prices]

        # 保存清洗结果
        df.to_csv(output_path, index=False, encoding="utf-8-sig")
        print(f"✅ 景点数据清洗完成！生成文件：{output_path}")

    except pd.errors.ParserError as e:
        print(f"❌ CSV 解析失败：{str(e)}")
        print("请检查文件中是否存在未转义的逗号或引号")
    except Exception as e:
        print(f"❌ 处理过程中发生错误：{str(e)}")

if __name__ == "__main__":
    clean_attractions()