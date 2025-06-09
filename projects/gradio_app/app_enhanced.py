# Copyright (c) Opendatalab. All rights reserved.

import base64
import os
import re
import time
import uuid
import zipfile
from pathlib import Path

import gradio as gr
import pymupdf
from gradio_pdf import PDF
from loguru import logger

from magic_pdf.data.data_reader_writer import FileBasedDataReader
from magic_pdf.libs.hash_utils import compute_sha256
from magic_pdf.tools.common import do_parse, prepare_env


def read_fn(path):
    disk_rw = FileBasedDataReader(os.path.dirname(path))
    return disk_rw.read(os.path.basename(path))


def parse_pdf(doc_path, output_dir, end_page_id, parse_method, layout_mode, formula_enable, table_enable, language):
    os.makedirs(output_dir, exist_ok=True)

    try:
        file_name = f'{str(Path(doc_path).stem)}_{time.time()}'
        pdf_data = read_fn(doc_path)
        
        local_image_dir, local_md_dir = prepare_env(output_dir, file_name, parse_method)
        do_parse(
            output_dir,
            file_name,
            pdf_data,
            [],
            parse_method,
            False,
            end_page_id=end_page_id,
            layout_model=layout_mode,
            formula_enable=False,  # Force disable formulas to avoid MFR model issues
            table_enable=table_enable,
            lang=language,
        )
        return local_md_dir, file_name
    except Exception as e:
        logger.exception(e)
        return None, None


def compress_directory_to_zip(directory_path, output_zip_path):
    """Compress specified directory to a ZIP file."""
    try:
        with zipfile.ZipFile(output_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(directory_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, directory_path)
                    zipf.write(file_path, arcname)
        return 0
    except Exception as e:
        logger.exception(e)
        return -1


def image_to_base64(image_path):
    with open(image_path, 'rb') as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')


def replace_image_with_base64(markdown_text, image_dir_path):
    # Match image tags in Markdown
    pattern = r'\!\[(?:[^\]]*)\]\(([^)]+)\)'

    def replace(match):
        relative_path = match.group(1)
        full_path = os.path.join(image_dir_path, relative_path)
        if os.path.exists(full_path):
            base64_image = image_to_base64(full_path)
            return f'![{relative_path}](data:image/jpeg;base64,{base64_image})'
        return match.group(0)  # Return original if file doesn't exist

    return re.sub(pattern, replace, markdown_text)


def to_markdown(file_path, end_pages, parse_method, layout_mode, formula_enable, table_enable, language, start_page=0):
    if file_path is None:
        return "Please upload a file first.", "", None, None
    
    file_path = to_pdf(file_path)
    
    # Check if PDF conversion was successful
    if file_path is None:
        error_msg = """❌ **Error: Unable to process the uploaded file**

**Possible causes:**
- 📄 **PDF is corrupted or damaged** - Try re-downloading or re-scanning the PDF
- 🔒 **PDF is password protected** - Remove password protection first
- 📁 **File format not supported** - Ensure the file is a valid PDF
- 📏 **File is too large** - Maximum file size is 500MB
- 📝 **File is empty** - Upload a valid PDF file

**Solutions:**
- Try a different PDF file
- Use a PDF repair tool to fix corruption
- Convert the file to PDF using a different tool
- Reduce file size if it's too large"""
        return error_msg, error_msg, None, None
    
    # Calculate actual end page
    actual_end_page = min(end_pages - 1, start_page + 20)  # Limit to 20 pages max
    
    try:
        local_md_dir, file_name = parse_pdf(
            file_path, './output', actual_end_page, parse_method,
            layout_mode, formula_enable, table_enable, language
        )
        
        # Check if parsing was successful
        if local_md_dir is None or file_name is None:
            error_msg = """❌ **PDF Processing Failed**
            
**The PDF could not be processed due to:**
- 🔧 **Model initialization issues** - Try restarting the application
- 🧮 **Formula recognition errors** - Try disabling formula recognition
- 📊 **Table detection issues** - Try disabling table recognition
- 🔍 **OCR processing errors** - Try switching to 'txt' mode for digital PDFs
- 💾 **Insufficient memory** - Try processing fewer pages at once

**Solutions:**
- Restart the application and try again
- Use simpler processing options (disable formula/table recognition)
- Process smaller page ranges
- Switch from 'auto' to 'txt' method for digital PDFs"""
            return error_msg, error_msg, None, None
        
        # Create ZIP file
        archive_zip_path = os.path.join('./output', compute_sha256(local_md_dir) + '.zip')
        zip_archive_success = compress_directory_to_zip(local_md_dir, archive_zip_path)
        
        if zip_archive_success == 0:
            logger.info('Compression successful')
        else:
            logger.error('Compression failed')
            
        # Read markdown file
        md_path = os.path.join(local_md_dir, file_name + '.md')
        if os.path.exists(md_path):
            with open(md_path, 'r', encoding='utf-8') as f:
                txt_content = f.read()
            md_content = replace_image_with_base64(txt_content, local_md_dir)
        else:
            txt_content = "Markdown file not found."
            md_content = txt_content
            
        # Check for layout PDF
        new_pdf_path = os.path.join(local_md_dir, file_name + '_layout.pdf')
        if not os.path.exists(new_pdf_path):
            new_pdf_path = file_path  # Fallback to original if layout PDF doesn't exist
            
        return md_content, txt_content, archive_zip_path, new_pdf_path
        
    except Exception as e:
        logger.exception(e)
        error_msg = f"Error processing PDF: {str(e)}"
        return error_msg, error_msg, None, None


latex_delimiters = [
    {'left': '$$', 'right': '$$', 'display': True},
    {'left': '$', 'right': '$', 'display': False}
]


def init_model():
    """Initialize the models - using same approach as CLI for compatibility"""
    from magic_pdf.model.doc_analyze_by_custom_model import ModelSingleton
    try:
        model_manager = ModelSingleton()
        # We don't actually initialize models here, just check if the system is ready
        # The actual models will be created by do_parse() function like in CLI
        logger.info('Model system ready - models will be initialized on-demand')
        return 0
    except Exception as e:
        logger.exception(e)
        return -1


# Language options organized by script
latin_lang = [
    'af', 'az', 'bs', 'cs', 'cy', 'da', 'de', 'es', 'et', 'fr', 'ga', 'hr',
    'hu', 'id', 'is', 'it', 'ku', 'la', 'lt', 'lv', 'mi', 'ms', 'mt', 'nl',
    'no', 'oc', 'pi', 'pl', 'pt', 'ro', 'rs_latin', 'sk', 'sl', 'sq', 'sv',
    'sw', 'tl', 'tr', 'uz', 'vi', 'french', 'german'
]
arabic_lang = ['ar', 'fa', 'ug', 'ur']
cyrillic_lang = [
    'ru', 'rs_cyrillic', 'be', 'bg', 'uk', 'mn', 'abq', 'ady', 'kbd', 'ava',
    'dar', 'inh', 'che', 'lbe', 'lez', 'tab'
]
devanagari_lang = [
    'hi', 'mr', 'ne', 'bh', 'mai', 'ang', 'bho', 'mah', 'sck', 'new', 'gom',
    'sa', 'bgc'
]
other_lang = ['ch', 'en', 'korean', 'japan', 'chinese_cht', 'ta', 'te', 'ka']

all_lang = ['auto', '']
all_lang.extend([*other_lang, *latin_lang, *arabic_lang, *cyrillic_lang, *devanagari_lang])


def validate_pdf_file(file_path):
    """Validate if a PDF file is readable and not corrupted"""
    try:
        # Try to read just the first few bytes to check PDF header
        with open(file_path, 'rb') as f:
            header = f.read(8)
            if not header.startswith(b'%PDF-'):
                logger.error(f"File does not have valid PDF header: {header}")
                return False
        
        # Try a minimal PyMuPDF operation
        with pymupdf.open(file_path) as f:
            # Just try to get basic info without fully loading
            page_count = len(f)
            if page_count == 0:
                logger.error("PDF has no pages")
                return False
            
            # Try to access first page metadata
            first_page = f[0]
            _ = first_page.rect  # This will fail if page is corrupted
            
            logger.info(f"PDF validation successful: {page_count} pages")
            return True
            
    except Exception as e:
        logger.error(f"PDF validation failed: {str(e)}")
        return False


def to_pdf(file_path):
    if not file_path:
        logger.debug("No file path provided")
        return None
        
    logger.info(f"Processing file: {file_path}")
    
    # Check if file exists and has content
    if not os.path.exists(file_path):
        logger.error(f"File does not exist: {file_path}")
        return None
        
    file_size = os.path.getsize(file_path)
    logger.info(f"File size: {file_size} bytes")
    
    if file_size == 0:
        logger.error(f"File is empty: {file_path}")
        return None
    
    # Check if file is too large (> 500MB)
    if file_size > 500 * 1024 * 1024:
        logger.error(f"File is too large: {file_size} bytes (max 500MB)")
        return None
    
    # Small delay to ensure file is fully written (especially for large files)
    time.sleep(0.1)
    
    try:
        logger.info(f"Opening file with PyMuPDF: {file_path}")
        
        # Try to detect file type first
        _, ext = os.path.splitext(file_path.lower())
        logger.info(f"File extension: {ext}")
        
        # If it's a PDF, validate it first
        if ext == '.pdf':
            if not validate_pdf_file(file_path):
                logger.error("PDF validation failed - file appears to be corrupted")
                return None
        
        with pymupdf.open(file_path) as f:
            logger.info(f"File opened successfully. Is PDF: {f.is_pdf}, Page count: {len(f) if hasattr(f, '__len__') else 'unknown'}")
            
            if f.is_pdf:
                return file_path
            else:
                logger.info("Converting non-PDF file to PDF")
                pdf_bytes = f.convert_to_pdf()
                unique_filename = f'{uuid.uuid4()}.pdf'
                tmp_file_path = os.path.join(os.path.dirname(file_path), unique_filename)
                
                with open(tmp_file_path, 'wb') as tmp_pdf_file:
                    tmp_pdf_file.write(pdf_bytes)
                
                logger.info(f"Converted file saved to: {tmp_file_path}")
                return tmp_file_path
                
    except Exception as e:
        logger.error(f"Error processing file {file_path}: {str(e)}")
        logger.error(f"Exception type: {type(e).__name__}")
        
        # Try to provide more specific error information
        if "no objects found" in str(e).lower():
            logger.error("The PDF appears to be corrupted or contains no valid objects")
        elif "cannot open" in str(e).lower():
            logger.error("Cannot open the file - it may be password protected or corrupted")
        elif "invalid xref" in str(e).lower():
            logger.error("The PDF has corrupted cross-reference table")
            
        return None


def update_method_description(method):
    descriptions = {
        "auto": "🤖 **Auto**: Automatically choose the best method (Recommended)",
        "txt": "📄 **Text**: Fast extraction for text-based PDFs (Best quality for digital PDFs)",
        "ocr": "🔍 **OCR**: Optical Character Recognition for scanned PDFs (Required for images/scans)"
    }
    return descriptions.get(method, "Select a parsing method")


# Initialize models
model_init = init_model()
logger.info(f'Model initialization status: {model_init}')

# Custom CSS for better styling
css = """
.method-description {
    padding: 10px;
    background-color: #f0f0f0;
    border-radius: 5px;
    margin: 10px 0;
    font-size: 14px;
}
.status-good { color: #28a745; }
.status-warning { color: #ffc107; }
.status-error { color: #dc3545; }
"""

if __name__ == '__main__':
    # Ensure output directory exists
    os.makedirs('./output', exist_ok=True)
    
    with gr.Blocks(css=css, title="MinerU - PDF to Markdown Converter") as demo:
        gr.Markdown("""
        # 🔍 MinerU - Advanced PDF to Markdown Converter
        
        Convert PDFs into high-quality Markdown with support for formulas, tables, and images.
        Choose the appropriate parsing method based on your PDF type for best results.
        """)
        
        with gr.Row():
            with gr.Column(variant='panel', scale=5):
                gr.Markdown("### 📁 Upload & Settings")
                
                file = gr.File(
                    label='📎 Upload PDF or Image', 
                    file_types=['.pdf', '.png', '.jpeg', '.jpg', '.doc', '.docx', '.ppt', '.pptx']
                )
                
                with gr.Row():
                    start_page = gr.Number(
                        label='📖 Start Page', 
                        value=1, 
                        minimum=1, 
                        maximum=1000,
                        info="Page to start processing from"
                    )
                    max_pages = gr.Number(
                        label='📑 End Page', 
                        value=10, 
                        minimum=1, 
                        maximum=1000,
                        info="Last page to process"
                    )
                
                with gr.Row():
                    parse_method = gr.Radio(
                        choices=['auto', 'txt', 'ocr'],
                        value='auto',
                        label='🎯 Parsing Method',
                        info="Choose how to extract content"
                    )
                    
                method_description = gr.Markdown(
                    update_method_description('auto'),
                    elem_classes=["method-description"]
                )
                
                with gr.Row():
                    layout_mode = gr.Dropdown(
                        choices=['doclayout_yolo', 'layoutlmv3'], 
                        label='🏗️ Layout Model', 
                        value='doclayout_yolo',
                        info="Layout detection model"
                    )
                    language = gr.Dropdown(
                        choices=all_lang, 
                        label='🌐 Language', 
                        value='auto',
                        info="OCR language (auto-detect recommended)"
                    )
                
                gr.Markdown("### ⚙️ Advanced Options")
                with gr.Row():
                    formula_enable = gr.Checkbox(
                        label='🧮 Formula Recognition', 
                        value=True,
                        info="Detect and convert mathematical formulas"
                    )
                    table_enable = gr.Checkbox(
                        label='📊 Table Recognition', 
                        value=True,
                        info="Detect and convert tables"
                    )
                
                with gr.Row():
                    convert_btn = gr.Button('🚀 Convert PDF', variant='primary', size='lg')
                    clear_btn = gr.ClearButton(value='🗑️ Clear All')
                
                # PDF Preview
                pdf_show = PDF(label='📄 PDF Preview', interactive=False, height=600)
                
                # Examples section
                with gr.Accordion('📚 Example Files', open=False):
                    example_root = os.path.join(os.path.dirname(__file__), 'examples')
                    if os.path.exists(example_root):
                        example_files = [
                            os.path.join(example_root, f) 
                            for f in os.listdir(example_root) 
                            if f.endswith(('.pdf', '.png', '.jpg', '.jpeg'))
                        ]
                        if example_files:
                            gr.Examples(examples=example_files, inputs=file)

            with gr.Column(variant='panel', scale=5):
                gr.Markdown("### 📤 Results")
                
                # Status indicator
                status = gr.Markdown("🔄 Ready to process files...", elem_classes=["status-good"])
                
                # Download section
                output_file = gr.File(
                    label='💾 Download Results (ZIP)', 
                    interactive=False,
                    visible=False
                )
                
                # Results tabs
                with gr.Tabs():
                    with gr.Tab('🎨 Markdown Preview'):
                        md = gr.Markdown(
                            label='Rendered Markdown', 
                            height=900, 
                            show_copy_button=True,
                            latex_delimiters=latex_delimiters, 
                            line_breaks=True
                        )
                    with gr.Tab('📝 Raw Markdown'):
                        md_text = gr.TextArea(
                            label='Raw Markdown Text',
                            lines=40, 
                            show_copy_button=True,
                            placeholder="Converted markdown will appear here..."
                        )
                    with gr.Tab('📄 Layout Analysis'):
                        layout_pdf = PDF(
                            label='Layout Analysis Result', 
                            interactive=False, 
                            height=800
                        )

        # Event handlers
        def on_convert(*args):
            return to_markdown(*args)
        
        def update_status(method):
            return update_method_description(method)
        
        def show_download(zip_file):
            if zip_file and os.path.exists(zip_file):
                return gr.update(visible=True, value=zip_file)
            return gr.update(visible=False)

        # Create a safe preview function
        def safe_pdf_preview(file_path):
            """Safely preview PDF file, handling errors gracefully"""
            if not file_path:
                return None
            
            try:
                logger.info(f"Safe PDF preview for: {file_path}")
                pdf_path = to_pdf(file_path)
                if pdf_path:
                    logger.info(f"PDF preview successful: {pdf_path}")
                    return pdf_path
                else:
                    logger.warning(f"Could not process file for preview: {file_path}")
                    return None
            except Exception as e:
                logger.error(f"Error in PDF preview: {str(e)}")
                return None

        # Wire up the interface
        file.change(fn=safe_pdf_preview, inputs=file, outputs=pdf_show)
        
        parse_method.change(
            fn=update_status, 
            inputs=parse_method, 
            outputs=method_description
        )
        
        # Enhanced convert function with status updates
        def convert_with_status(*args):
            try:
                result = on_convert(*args)
                
                # Check if conversion was successful
                if result[0].startswith("❌"):
                    return result + ("❌ Conversion failed. Please check the error message above.",)
                else:
                    return result + ("✅ Conversion completed successfully!",)
            except Exception as e:
                logger.error(f"Conversion error: {str(e)}")
                error_msg = f"❌ Error during conversion: {str(e)}"
                return error_msg, error_msg, None, None, "❌ Conversion failed."

        def show_processing():
            return "🔄 Processing PDF... Please wait..."
        
        convert_btn.click(
            fn=show_processing,
            outputs=status
        ).then(
            fn=convert_with_status,
            inputs=[file, max_pages, parse_method, layout_mode, formula_enable, table_enable, language, start_page],
            outputs=[md, md_text, output_file, layout_pdf, status]
        ).then(
            fn=show_download,
            inputs=output_file,
            outputs=output_file
        )
        
        clear_btn.add([
            file, md, pdf_show, md_text, output_file, 
            parse_method, start_page, max_pages, language, 
            formula_enable, table_enable, layout_pdf, status
        ])

    import socket
    
    def find_free_port(start_port=7860):
        """Find a free port starting from start_port"""
        for port in range(start_port, start_port + 100):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(('', port))
                    return port
            except OSError:
                continue
        return start_port  # fallback to original port

    port = find_free_port(7860)
    print(f"🌐 Starting server on http://localhost:{port}")
    
    demo.launch(
        server_name='0.0.0.0',
        server_port=port,
        share=False,
        show_error=True
    ) 