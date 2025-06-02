import pandas as pd
from pathlib import Path

def validate_data():
    """验证处理后的数据质量"""
    base_dir = Path(__file__).parent.parent
    processed_dir = base_dir / "processed_data"
    
    # 要验证的文件
    files_to_validate = [
        "attractions_with_id.csv",
        "food_with_id.csv",
        "culture_with_id.csv"
    ]
    
    validation_results = {}
    
    for file in files_to_validate:
        file_path = processed_dir / file
        data_type = file.split("_")[0]
        
        if not file_path.exists():
            validation_results[file] = {
                "status": "missing",
                "message": f"文件不存在: {file_path}"
            }
            continue
        
        try:
            df = pd.read_csv(file_path, encoding="utf-8-sig")
            issues = []
            
            # 检查唯一编码是否唯一
            if "唯一编码" in df.columns:
                unique_count = df["唯一编码"].nunique()
                total_count = len(df)
                
                if unique_count < total_count:
                    issues.append(f"唯一编码不唯一: {total_count - unique_count} 个重复值")
            
            # 检查关键字段是否缺失
            required_fields = {
                "attractions": ["名称", "主类型", "门票最低(元)"],
                "food": ["店名", "人均消费", "类型"],
                "culture": ["名称", "类别", "级别"]
            }
            
            for field in required_fields.get(data_type, []):
                if field not in df.columns:
                    issues.append(f"缺失必要字段: {field}")
                elif df[field].isnull().any():
                    null_count = df[field].isnull().sum()
                    issues.append(f"字段 {field} 有 {null_count} 个空值")
            
            if issues:
                validation_results[file] = {
                    "status": "issues",
                    "issues": issues
                }
            else:
                validation_results[file] = {
                    "status": "valid",
                    "message": "所有检查通过"
                }
                
        except Exception as e:
            validation_results[file] = {
                "status": "error",
                "message": str(e)
            }
    
    # 打印验证结果
    print("="*40)
    print("数据验证报告")
    print("="*40)
    
    for file, result in validation_results.items():
        print(f"\n📋 文件: {file}")
        if result["status"] == "valid":
            print(f"   ✅ {result['message']}")
        elif result["status"] == "missing":
            print(f"   ⛔ {result['message']}")
        elif result["status"] == "error":
            print(f"   ❌ 验证错误: {result['message']}")
        elif result["status"] == "issues":
            print("   ⚠️ 发现以下问题:")
            for issue in result["issues"]:
                print(f"      - {issue}")
    
    print("\n" + "="*40)
    
    return validation_results

if __name__ == "__main__":
    validate_data()