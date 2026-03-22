import requests
import base64
import time
import json

# 测试配置
API_URL = 'http://localhost:8000/api/ocr'

# 读取测试图片并转换为base64
def image_to_base64(image_path):
    with open(image_path, 'rb') as f:
        return 'data:image/jpeg;base64,' + base64.b64encode(f.read()).decode('utf-8')

# 测试OCR功能
def test_ocr(image_path, vision_config):
    print(f"测试图片: {image_path}")
    
    # 准备请求数据
    image_data = image_to_base64(image_path)
    payload = {
        'image': image_data,
        'visionConfig': vision_config
    }
    
    # 记录开始时间
    start_time = time.time()
    
    # 发送请求
    response = requests.post(API_URL, json=payload)
    
    # 记录结束时间
    end_time = time.time()
    processing_time = end_time - start_time
    
    # 分析响应
    if response.status_code == 200:
        data = response.json()
        print(f"处理时间: {processing_time:.2f} 秒")
        print(f"OCR结果: {data.get('latex', '无结果')}")
        print(f"任务ID: {data.get('task_id', '无任务ID')}")
        
        # 检查处理时间是否符合要求
        if processing_time <= 10:
            print("✅ 处理时间符合要求 (<= 10秒)")
        else:
            print("❌ 处理时间不符合要求 (> 10秒)")
        
        return True, processing_time, data.get('latex', '')
    else:
        print(f"❌ 请求失败: {response.status_code}")
        print(f"错误信息: {response.json().get('error', '未知错误')}")
        return False, processing_time, ""

# 测试颜色检测功能
def test_color_detection(latex_result):
    print("\n测试颜色检测功能:")
    
    # 检查是否包含颜色命令
    color_commands = ['\\textcolor{red}', '\\textcolor{blue}', '\\textcolor{green}', '\\textcolor{orange}', '\\textcolor{purple}']
    detected_colors = []
    
    for color_cmd in color_commands:
        if color_cmd in latex_result:
            detected_colors.append(color_cmd.split('{')[1].split('}')[0])
    
    if detected_colors:
        print(f"✅ 检测到颜色: {', '.join(detected_colors)}")
    else:
        print("⚠️  未检测到颜色命令")
    
    return len(detected_colors) > 0

# 主测试函数
def main():
    # 读取API配置（假设已经在本地存储中）
    try:
        with open('settings.json', 'r') as f:
            settings = json.load(f)
        vision_config = settings.get('vision', {})
    except:
        print("请在settings.json中配置API密钥")
        return
    
    # 测试图片路径（根据实际情况修改）
    test_images = [
        'test_image1.jpg',  # 包含数学公式的图片
        'test_image2.jpg',  # 包含彩色手写的图片
        'test_image3.jpg'   # 包含复杂内容的图片
    ]
    
    # 执行测试
    results = []
    for image_path in test_images:
        print("\n" + "="*50)
        success, processing_time, latex_result = test_ocr(image_path, vision_config)
        if success:
            color_detected = test_color_detection(latex_result)
            results.append({
                'image': image_path,
                'success': success,
                'processing_time': processing_time,
                'color_detected': color_detected
            })
    
    # 生成测试报告
    print("\n" + "="*50)
    print("测试报告总结:")
    print("="*50)
    
    total_tests = len(results)
    successful_tests = sum(1 for r in results if r['success'])
    avg_processing_time = sum(r['processing_time'] for r in results) / total_tests if total_tests > 0 else 0
    color_detection_success = sum(1 for r in results if r['color_detected'])
    
    print(f"总测试数: {total_tests}")
    print(f"成功测试数: {successful_tests}")
    print(f"平均处理时间: {avg_processing_time:.2f} 秒")
    print(f"颜色检测成功数: {color_detection_success}")
    
    # 检查是否所有测试都通过
    if successful_tests == total_tests and avg_processing_time <= 10:
        print("\n🎉 所有测试通过！")
    else:
        print("\n⚠️  部分测试未通过，请检查")

if __name__ == "__main__":
    main()
