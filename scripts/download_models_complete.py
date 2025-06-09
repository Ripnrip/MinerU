import json
import os

import requests
from huggingface_hub import snapshot_download


def download_json(url):
    # 下载JSON文件
    response = requests.get(url)
    response.raise_for_status()  # 检查请求是否成功
    return response.json()


def download_and_modify_json(url, local_filename, modifications):
    if os.path.exists(local_filename):
        data = json.load(open(local_filename))
        config_version = data.get('config_version', '0.0.0')
        if config_version < '1.1.1':
            data = download_json(url)
    else:
        data = download_json(url)

    # 修改内容
    for key, value in modifications.items():
        data[key] = value

    # 保存修改后的内容
    with open(local_filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


if __name__ == '__main__':
    print("🚀 Downloading complete MinerU model set including OCR...")
    
    # Complete model patterns including OCR
    mineru_patterns = [
        "models/Layout/LayoutLMv3/*",
        "models/Layout/YOLO/*", 
        "models/MFD/YOLO/*",
        "models/MFR/unimernet_small_2501/*",
        "models/TabRec/TableMaster/*",
        "models/TabRec/StructEqTable/*",
        "models/OCR/*",  # Include OCR models
    ]
    
    print("📦 Downloading PDF-Extract-Kit models...")
    model_dir = snapshot_download('opendatalab/PDF-Extract-Kit-1.0', allow_patterns=mineru_patterns)

    print("📦 Downloading LayoutReader models...")
    layoutreader_pattern = [
        "*.json",
        "*.safetensors",
    ]
    layoutreader_model_dir = snapshot_download('hantian/layoutreader', allow_patterns=layoutreader_pattern)

    model_dir = model_dir + '/models'
    print(f'✅ Model directory: {model_dir}')
    print(f'✅ LayoutReader directory: {layoutreader_model_dir}')

    print("📝 Updating configuration...")
    json_url = 'https://github.com/opendatalab/MinerU/raw/master/magic-pdf.template.json'
    config_file_name = 'magic-pdf.json'
    home_dir = os.path.expanduser('~')
    config_file = os.path.join(home_dir, config_file_name)

    json_mods = {
        'models-dir': model_dir,
        'layoutreader-model-dir': layoutreader_model_dir,
    }

    download_and_modify_json(json_url, config_file, json_mods)
    print(f'✅ Configuration updated: {config_file}')
    
    # Check what OCR models were downloaded
    ocr_dir = os.path.join(model_dir, 'OCR')
    if os.path.exists(ocr_dir):
        print(f"📁 OCR models found in: {ocr_dir}")
        for root, dirs, files in os.walk(ocr_dir):
            for file in files:
                if file.endswith('.pth'):
                    print(f"   📄 {os.path.relpath(os.path.join(root, file), ocr_dir)}")
    else:
        print("⚠️  No OCR models directory found")
    
    print("🎉 Complete model download finished!") 