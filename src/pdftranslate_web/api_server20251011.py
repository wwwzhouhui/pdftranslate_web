import asyncio
import logging
import uuid
from pathlib import Path
from typing import Dict, Any, Optional
import tempfile
import shutil
from concurrent.futures import ThreadPoolExecutor
import os

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uvicorn
from dotenv import load_dotenv

import babeldoc.format.pdf.high_level
from babeldoc.format.pdf.translation_config import TranslationConfig, WatermarkOutputMode
from babeldoc.translator.translator import OpenAITranslator, set_translate_rate_limiter

logger = logging.getLogger(__name__)
load_dotenv()  # 自动加载同目录下的 .env 文件
# 从环境变量加载配置
def load_config():
    """从环境变量加载配置"""
    return {
        "openai": {
            "api_key": os.getenv("OPENAI_API_KEY", ""),
            "model": os.getenv("OPENAI_MODEL", "deepseek-ai/DeepSeek-V3"),
            "base_url": os.getenv("OPENAI_BASE_URL", "https://api.siliconflow.cn/v1")
        },
        "server": {
            "host": os.getenv("SERVER_HOST", "0.0.0.0"),
            "port": int(os.getenv("SERVER_PORT", "8000")),
            "qps": int(os.getenv("QPS", "4"))
        },
        "translation": {
            "default_lang_in": os.getenv("DEFAULT_LANG_IN", "en"),
            "default_lang_out": os.getenv("DEFAULT_LANG_OUT", "zh"),
            "watermark_output_mode": os.getenv("WATERMARK_OUTPUT_MODE", "no_watermark"),
            "no_dual": os.getenv("NO_DUAL", "false").lower() == "true",
            "no_mono": os.getenv("NO_MONO", "false").lower() == "true"
        }
    }

config = load_config()

# 验证OpenAI配置
if not config["openai"]["api_key"]:
    logger.error("未找到OpenAI API密钥！请通过环境变量OPENAI_API_KEY提供")
    raise ValueError("Missing OpenAI API key")

app = FastAPI(title="BabelDOC Translation API", version="0.4.16")

class TranslationRequest(BaseModel):
    lang_in: Optional[str] = None
    lang_out: Optional[str] = None
    qps: Optional[int] = None
    no_dual: Optional[bool] = None
    no_mono: Optional[bool] = None
    watermark_output_mode: Optional[str] = None

class TranslationStatus(BaseModel):
    task_id: str
    status: str  # pending, processing, completed, failed
    progress: float = 0.0
    message: str = ""
    result_files: Dict[str, str] = {}

translation_tasks: Dict[str, TranslationStatus] = {}
task_files: Dict[str, Dict[str, Path]] = {}

async def translate_document(
    task_id: str,
    pdf_file: Path,
    request: TranslationRequest,
    output_dir: Path
):
    try:
        translation_tasks[task_id].status = "processing"
        translation_tasks[task_id].message = "正在初始化翻译器..."
        
        # 使用配置文件中的OpenAI设置
        translator = OpenAITranslator(
            lang_in=request.lang_in or config["translation"]["default_lang_in"],
            lang_out=request.lang_out or config["translation"]["default_lang_out"],
            model=config["openai"]["model"],
            base_url=config["openai"]["base_url"],
            api_key=config["openai"]["api_key"],
            ignore_cache=False,
        )
        
        set_translate_rate_limiter(request.qps or config["server"]["qps"])
        
        from babeldoc.docvision.doclayout import DocLayoutModel
        doc_layout_model = DocLayoutModel.load_onnx()
        
        watermark_output_mode = request.watermark_output_mode or config["translation"]["watermark_output_mode"]
        watermark_mode = WatermarkOutputMode.Watermarked
        if watermark_output_mode == "no_watermark":
            watermark_mode = WatermarkOutputMode.NoWatermark
        elif watermark_output_mode == "both":
            watermark_mode = WatermarkOutputMode.Both
        
        config_obj = TranslationConfig(
            input_file=str(pdf_file),
            font=None,
            pages=None,
            output_dir=str(output_dir),
            translator=translator,
            debug=False,
            lang_in=request.lang_in or config["translation"]["default_lang_in"],
            lang_out=request.lang_out or config["translation"]["default_lang_out"],
            no_dual=request.no_dual if request.no_dual is not None else config["translation"]["no_dual"],
            no_mono=request.no_mono if request.no_mono is not None else config["translation"]["no_mono"],
            qps=request.qps or config["server"]["qps"],
            formular_font_pattern=None,
            formular_char_pattern=None,
            split_short_lines=False,
            short_line_split_factor=0.8,
            doc_layout_model=doc_layout_model,
            skip_clean=False,
            dual_translate_first=False,
            disable_rich_text_translate=False,
            enhance_compatibility=False,
            use_alternating_pages_dual=False,
            report_interval=0.1,
            min_text_length=5,
            watermark_output_mode=watermark_mode,
            split_strategy=None,
            table_model=None,
            show_char_box=False,
            skip_scanned_detection=False,
            ocr_workaround=False,
            custom_system_prompt=None,
            working_dir=None,
            add_formula_placehold_hint=False,
            glossaries=[],
            pool_max_workers=None,
            auto_extract_glossary=True,
            auto_enable_ocr_workaround=False,
            primary_font_family=None,
            only_include_translated_page=False,
            save_auto_extracted_glossary=False,
        )
        
        translation_tasks[task_id].message = "正在翻译文档..."
        
        async for event in babeldoc.format.pdf.high_level.async_translate(config_obj):
            if event["type"] == "progress_update":
                translation_tasks[task_id].progress = event.get("overall_progress", 0.0)
                translation_tasks[task_id].message = f"{event.get('stage', '处理中')} ({event.get('stage_current', 0)}/{event.get('stage_total', 100)})"
            elif event["type"] == "error":
                translation_tasks[task_id].status = "failed"
                translation_tasks[task_id].message = f"翻译失败: {event.get('error', '未知错误')}"
                logger.error(f"Translation failed for task {task_id}: {event.get('error')}")
                return
            elif event["type"] == "finish":
                result = event["translate_result"]
                translation_tasks[task_id].status = "completed"
                translation_tasks[task_id].progress = 100.0
                translation_tasks[task_id].message = "翻译完成"
                
                result_files = {}
                if result.dual_pdf_path and Path(result.dual_pdf_path).exists():
                    result_files["dual"] = str(result.dual_pdf_path)
                if result.mono_pdf_path and Path(result.mono_pdf_path).exists():
                    result_files["mono"] = str(result.mono_pdf_path)
                
                translation_tasks[task_id].result_files = result_files
                task_files[task_id] = {k: Path(v) for k, v in result_files.items()}
                
                logger.info(f"Translation completed for task {task_id}")
                break
                
    except Exception as e:
        translation_tasks[task_id].status = "failed"
        translation_tasks[task_id].message = f"翻译过程出错: {str(e)}"
        logger.error(f"Translation error for task {task_id}: {e}", exc_info=True)

@app.post("/translate", response_model=dict)
async def translate_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    lang_in: Optional[str] = Form(None),
    lang_out: Optional[str] = Form(None),
    qps: Optional[int] = Form(None),
    no_dual: Optional[bool] = Form(None),
    no_mono: Optional[bool] = Form(None),
    watermark_output_mode: Optional[str] = Form(None)
):
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="只支持PDF文件")
    
    task_id = str(uuid.uuid4())
    
    temp_dir = Path(tempfile.mkdtemp())
    pdf_path = temp_dir / file.filename
    output_dir = temp_dir / "output"
    output_dir.mkdir(exist_ok=True)
    
    with open(pdf_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    request = TranslationRequest(
        lang_in=lang_in,
        lang_out=lang_out,
        qps=qps,
        no_dual=no_dual,
        no_mono=no_mono,
        watermark_output_mode=watermark_output_mode
    )
    
    translation_tasks[task_id] = TranslationStatus(
        task_id=task_id,
        status="pending",
        message="任务已创建，等待处理..."
    )
    
    background_tasks.add_task(
        translate_document,
        task_id,
        pdf_path,
        request,
        output_dir
    )
    
    return {"task_id": task_id, "message": "翻译任务已创建"}

@app.get("/status/{task_id}", response_model=TranslationStatus)
async def get_translation_status(task_id: str):
    if task_id not in translation_tasks:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    return translation_tasks[task_id]

@app.get("/download/{task_id}/{file_type}")
async def download_result(task_id: str, file_type: str):
    if task_id not in translation_tasks:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    if translation_tasks[task_id].status != "completed":
        raise HTTPException(status_code=400, detail="翻译尚未完成")
    
    if task_id not in task_files or file_type not in task_files[task_id]:
        raise HTTPException(status_code=404, detail="文件不存在")
    
    file_path = task_files[task_id][file_type]
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")
    
    return FileResponse(
        path=file_path,
        filename=file_path.name,
        media_type='application/pdf'
    )

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "BabelDOC Translation API"}

@app.get("/")
async def root():
    return {
        "message": "BabelDOC Translation API",
        "version": "0.4.16",
        "config": {
            "openai_model": config["openai"]["model"],
            "default_lang_in": config["translation"]["default_lang_in"],
            "default_lang_out": config["translation"]["default_lang_out"],
            "qps": config["server"]["qps"]
        },
        "endpoints": {
            "translate": "POST /translate - 上传PDF文件进行翻译",
            "status": "GET /status/{task_id} - 查询翻译状态",
            "download": "GET /download/{task_id}/{file_type} - 下载翻译结果",
            "health": "GET /health - 健康检查"
        }
    }

def start_server(host: Optional[str] = None, port: Optional[int] = None):
    babeldoc.format.pdf.high_level.init()
    
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("httpx").setLevel("WARNING")
    logging.getLogger("openai").setLevel("WARNING")
    
    server_host = host or config["server"]["host"]
    server_port = port or config["server"]["port"]
    
    logger.info(f"Using OpenAI model: {config['openai']['model']}")
    logger.info(f"Default languages: {config['translation']['default_lang_in']} -> {config['translation']['default_lang_out']}")
    
    uvicorn.run(app, host=server_host, port=server_port)

if __name__ == "__main__":
    start_server()