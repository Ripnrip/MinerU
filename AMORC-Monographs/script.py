# Copyright (c) Opendatalab. All rights reserved.
import os
import glob

from magic_pdf.data.data_reader_writer import FileBasedDataWriter, FileBasedDataReader
from magic_pdf.data.dataset import PymuDocDataset
from magic_pdf.model.doc_analyze_by_custom_model import doc_analyze
from magic_pdf.config.enums import SupportedPdfParseMethod

def safe_run(task_name, func):
    try:
        func()
        print(f"✅ {task_name} succeeded.")
    except Exception as e:
        print(f"⚠️  {task_name} failed: {e}")

# Recursively find all .pdf files excluding the "output/" directory
pdf_files = [f for f in glob.glob("**/*.pdf", recursive=True) if not f.startswith("output/")]

for pdf_file_name in pdf_files:
    # Remove the .pdf extension
    name_without_suff = os.path.splitext(os.path.basename(pdf_file_name))[0]

    # Get the relative directory path for the file (excluding filename)
    relative_folder = os.path.dirname(pdf_file_name)

    # Mirror that structure in the output directory
    local_output_base = os.path.join("output", relative_folder)
    local_image_dir = os.path.join(local_output_base, name_without_suff, "images")
    local_md_dir = os.path.join(local_output_base, name_without_suff)
    image_dir = os.path.basename(local_image_dir)

    os.makedirs(local_image_dir, exist_ok=True)
    os.makedirs(local_md_dir, exist_ok=True)

    print(f"\n📄 Processing: {pdf_file_name}")

    try:
        image_writer = FileBasedDataWriter(local_image_dir)
        md_writer = FileBasedDataWriter(local_md_dir)

        reader1 = FileBasedDataReader("")
        pdf_bytes = reader1.read(pdf_file_name)

        ds = PymuDocDataset(pdf_bytes)

        if ds.classify() == SupportedPdfParseMethod.OCR:
            infer_result = ds.apply(doc_analyze, ocr=True)
            pipe_result = infer_result.pipe_ocr_mode(image_writer)
        else:
            infer_result = ds.apply(doc_analyze, ocr=False)
            pipe_result = infer_result.pipe_txt_mode(image_writer)

        # Safely perform output generation
        safe_run("draw_model", lambda: infer_result.draw_model(os.path.join(local_md_dir, f"{name_without_suff}_model.pdf")))
        safe_run("draw_layout", lambda: pipe_result.draw_layout(os.path.join(local_md_dir, f"{name_without_suff}_layout.pdf")))
        safe_run("draw_span", lambda: pipe_result.draw_span(os.path.join(local_md_dir, f"{name_without_suff}_spans.pdf")))
        safe_run("dump_md", lambda: pipe_result.dump_md(md_writer, f"{name_without_suff}.md", image_dir))
        safe_run("dump_content_list", lambda: pipe_result.dump_content_list(md_writer, f"{name_without_suff}_content_list.json", image_dir))
        safe_run("dump_middle_json", lambda: pipe_result.dump_middle_json(md_writer, f"{name_without_suff}_middle.json"))

    except Exception as e:
        print(f"❌ Failed to process {pdf_file_name}: {e}")
