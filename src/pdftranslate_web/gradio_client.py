import gradio as gr
import os
import tempfile
import time
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
import fitz  # PyMuPDF
import base64
from io import BytesIO
from PIL import Image

from pdftranslate_web.api_client import BabelDOCClient
import json

# 管理员密码配置
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "zhouqingYu666")

class GradioClient:
    def __init__(self, server_url: str = "http://localhost:8000"):
        self.client = BabelDOCClient(server_url)
        self.temp_dir = Path(tempfile.mkdtemp())
        self.current_task_id = None
        # 获取项目根目录路径
        self.project_root = Path(__file__).parent.parent.parent
        self.sample_file_path = self.project_root / "simaple" / "11.pdf"
        
        
    def check_server_status(self) -> Tuple[str, Dict]:
        """检查服务器状态和配置"""
        try:
            if not self.client.health_check():
                return "❌ 服务器离线", {}
            
            config = self.client.get_server_config()
            
            status_text = f"""✅ 服务器在线
            
**服务器配置:**
- 模型: {config['config']['openai_model']}
- 默认语言: {config['config']['default_lang_in']} → {config['config']['default_lang_out']}
- QPS限制: {config['config']['qps']}
"""
            return status_text, config['config']
        except Exception as e:
            return f"❌ 连接失败: {str(e)}", {}
    
    def pdf_to_images(self, pdf_path: str, max_pages: int = None) -> list:
        """将PDF转换为图片预览"""
        if not pdf_path or not os.path.exists(pdf_path):
            return []
        
        try:
            doc = fitz.open(pdf_path)
            images = []
            
            num_pages = len(doc) if max_pages is None else min(len(doc), max_pages)
            for page_num in range(num_pages):
                page = doc[page_num]
                # 设置缩放比例以获得合适的预览大小
                mat = fitz.Matrix(1.5, 1.5)
                pix = page.get_pixmap(matrix=mat)
                img_data = pix.tobytes("png")
                
                # 转换为PIL Image
                img = Image.open(BytesIO(img_data))
                images.append(img)
            
            doc.close()
            return images
        except Exception as e:
            print(f"PDF预览失败: {e}")
            return []
    
    def translate_pdf(
        self, 
        pdf_file, 
        lang_in: Optional[str] = None,
        lang_out: Optional[str] = None,
        file_type: str = "dual",
        progress=gr.Progress()
    ) -> Tuple[str, str, list, str, str]:
        """翻译PDF文件"""
        if pdf_file is None:
            return "❌ 请先上传PDF文件", "", [], "", ""
        
        try:
            # 记录开始时间
            start_time = time.time()
            start_time_str = time.strftime("%H:%M:%S", time.localtime(start_time))
            
            progress(0, desc="正在提交翻译任务...")
            
            # 保存上传的文件
            pdf_path = self.temp_dir / f"input_{int(time.time())}.pdf"
            with open(pdf_path, "wb") as f:
                f.write(pdf_file)
            
            # 提交翻译任务
            task_id = self.client.translate_pdf(
                pdf_path=str(pdf_path),
                lang_in=lang_in if lang_in else None,
                lang_out=lang_out if lang_out else None
            )
            self.current_task_id = task_id
            
            progress(0.1, desc=f"任务已创建: {task_id[:8]}...")
            
            # 监控翻译进度
            while time.time() - start_time < 3600:  # 1小时超时
                status = self.client.get_status(task_id)
                
                if status['status'] == 'completed':
                    progress(1.0, desc="翻译完成，正在下载结果...")
                    
                    # 记录结束时间
                    end_time = time.time()
                    end_time_str = time.strftime("%H:%M:%S", time.localtime(end_time))
                    duration = end_time - start_time
                    duration_str = f"{int(duration//60)}分{int(duration%60)}秒"
                    
                    timing_info = f"开始时间: {start_time_str} | 完成时间: {end_time_str} | 总耗时: {duration_str}"
                    
                    # 下载结果文件
                    output_dir = self.temp_dir / f"output_{task_id[:8]}"
                    output_dir.mkdir(exist_ok=True)
                    
                    downloaded_files = {}
                    for ftype in ['dual', 'mono']:
                        if ftype in status['result_files']:
                            output_file = output_dir / f"translated_{ftype}.pdf"
                            if self.client.download_result(task_id, ftype, str(output_file)):
                                downloaded_files[ftype] = str(output_file)
                    
                    # 返回指定类型的文件
                    if file_type in downloaded_files:
                        result_path = downloaded_files[file_type]
                        result_images = self.pdf_to_images(result_path)
                        
                        return (
                            f"✅ 翻译完成！共生成 {len(result_images)} 页内容",
                            result_path,
                            result_images,
                            f"任务ID: {task_id}",
                            timing_info
                        )
                    else:
                        return (
                            f"⚠️ 翻译完成但未找到 {file_type} 文件类型",
                            "",
                            [],
                            f"任务ID: {task_id}",
                            timing_info
                        )
                
                elif status['status'] == 'failed':
                    end_time = time.time()
                    end_time_str = time.strftime("%H:%M:%S", time.localtime(end_time))
                    duration = end_time - start_time
                    duration_str = f"{int(duration//60)}分{int(duration%60)}秒"
                    timing_info = f"开始时间: {start_time_str} | 失败时间: {end_time_str} | 耗时: {duration_str}"
                    
                    return (
                        f"❌ 翻译失败: {status['message']}",
                        "",
                        [],
                        f"任务ID: {task_id}",
                        timing_info
                    )
                
                # 更新进度
                progress_val = status['progress'] / 100.0
                progress(progress_val, desc=f"{status['message']}")
                time.sleep(2)
            
            # 超时情况
            end_time = time.time()
            end_time_str = time.strftime("%H:%M:%S", time.localtime(end_time))
            duration = end_time - start_time
            duration_str = f"{int(duration//60)}分{int(duration%60)}秒"
            timing_info = f"开始时间: {start_time_str} | 超时时间: {end_time_str} | 耗时: {duration_str}"
            
            return "❌ 翻译超时", "", [], f"任务ID: {task_id}", timing_info
            
        except Exception as e:
            return f"❌ 翻译出错: {str(e)}", "", [], "", ""
    
    def get_task_status(self, task_id: str) -> str:
        """获取任务状态"""
        if not task_id:
            return "请输入任务ID"
        
        try:
            status = self.client.get_status(task_id)
            return f"""
**任务状态:** {status['status']}
**进度:** {status['progress']:.1f}%
**消息:** {status['message']}
**结果文件:** {', '.join(status['result_files'].keys()) if status['result_files'] else '无'}
"""
        except Exception as e:
            return f"查询失败: {str(e)}"
    
    def load_sample_file(self) -> Tuple[bytes, list, str]:
        """加载示例PDF文件"""
        try:
            if not self.sample_file_path.exists():
                return None, [], "❌ 示例文件不存在"
            
            # 读取示例文件
            with open(self.sample_file_path, "rb") as f:
                file_data = f.read()
            
            # 生成预览图片
            images = self.pdf_to_images(str(self.sample_file_path))
            status = f"✅ 已加载示例文件，共 {len(images)} 页"
            
            return file_data, images, status
        except Exception as e:
            return None, [], f"❌ 加载示例文件失败: {str(e)}"

CUSTOM_CSS = """
.main-container { max-width: 1400px; margin: 0 auto; }
.preview-container { height: 600px; overflow-y: auto; }
.status-box { background-color: #f8f9fa; padding: 15px; border-radius: 8px; }

/* 隐藏Gradio底部标志 */
.footer { display: none !important; }
.gradio-container .footer { display: none !important; }
footer { display: none !important; }
.gradio-container footer { display: none !important; }
.gradio-container .gradio-footer { display: none !important; }
.gradio-footer { display: none !important; }
"""

def create_gradio_interface(server_url: str = "http://localhost:8000"):
    """创建Gradio界面"""
    gradio_client = GradioClient(server_url)

    with gr.Blocks(
        title="pdftranslate PDF翻译工具"
    ) as demo:
        
        gr.Markdown("""
        # 🌍 pdftranslate PDF翻译工具
        
        上传PDF文件，选择翻译选项，即可获得翻译后的PDF文件。支持双语对照和纯翻译两种模式。
        """)
        
        # 顶部状态和选项栏
        with gr.Row():
            with gr.Column(scale=1):
                server_status = gr.Markdown("检查服务器状态中...")
        
        # 主要界面区域，包含配置选项卡
        with gr.Tabs():
            with gr.TabItem("📄 PDF翻译"):
                # 翻译选项区域
                with gr.Row():
                    with gr.Column(scale=1):
                        gr.Markdown("**⚙️ 翻译选项**")
                        with gr.Row():
                            lang_in = gr.Textbox(
                                label="源语言",
                                placeholder="留空使用服务器默认 (en)",
                                scale=1,
                                container=False
                            )
                            lang_out = gr.Textbox(
                                label="目标语言", 
                                placeholder="留空使用服务器默认 (zh)",
                                scale=1,
                                container=False
                            )
                        
                        with gr.Row():
                            file_type = gr.Radio(
                                choices=["dual", "mono"],
                                value="dual",
                                label="输出类型",
                                info="dual: 双语对照, mono: 纯翻译",
                                container=False,
                                scale=1
                            )
                            
                            translate_btn = gr.Button(
                                "🚀 开始翻译",
                                variant="primary",
                                size="sm",
                                scale=1
                            )
                
                with gr.Row():
                    # 左侧：上传和控制面板
                    with gr.Column(scale=1):
                        gr.Markdown("### 📁 文件上传")
                        
                        # 示例文件加载
                        with gr.Row():
                            sample_btn = gr.Button(
                                "📋 加载示例文件 (11.pdf)",
                                variant="secondary",
                                size="sm",
                                scale=3
                            )
                            with gr.Column(scale=1, min_width=50):
                                gr.Markdown("*或*")
                        
                        pdf_input = gr.File(
                            label="拖放PDF文件至此或点击选择",
                            file_types=[".pdf"],
                            type="binary"
                        )
                        
                        # 原始PDF预览
                        gr.Markdown("### 📄 原始PDF预览")
                        original_preview = gr.Gallery(
                            label="原始PDF页面",
                            show_label=False,
                            elem_classes=["preview-container"],
                            columns=1,
                            rows=2,
                            height="400px",
                            interactive=False
                        )
                        
                    # 右侧：结果展示
                    with gr.Column(scale=1):
                        gr.Markdown("### 📊 翻译状态")
                        translation_status = gr.Markdown(
                            "等待上传文件...",
                            elem_classes=["status-box"]
                        )
                        
                        gr.Markdown("### 📑 翻译结果预览")
                        result_preview = gr.Gallery(
                            label="翻译后PDF页面",
                            show_label=False,
                            elem_classes=["preview-container"],
                            columns=1,
                            rows=2,
                            height="400px",
                            interactive=False
                        )
                        
                        # 下载按钮
                        download_btn = gr.File(
                            label="下载翻译结果",
                            visible=False
                        )
                        
                        # 任务信息
                        task_info = gr.Textbox(
                            label="任务信息",
                            interactive=False,
                            visible=False
                        )
                
                # 底部：任务状态查询
                with gr.Accordion("🔍 任务状态查询", open=False):
                    with gr.Row():
                        task_id_input = gr.Textbox(
                            label="任务ID",
                            placeholder="输入任务ID查询状态"
                        )
                        query_btn = gr.Button("查询", size="sm")
                    
                    task_status_output = gr.Markdown("输入任务ID进行查询")
                
                # 底部时间统计显示
                with gr.Row():
                    timing_display = gr.Markdown(
                        "⏱️ **处理时间统计**：等待开始翻译...",
                        elem_classes=["status-box"]
                    )

        
        def update_server_status():
            status_text, config = gradio_client.check_server_status()
            return status_text
        
        
        # 定期更新服务器状态
        demo.load(update_server_status, outputs=[server_status])
        
        # 事件处理
        def on_pdf_upload(pdf_file):
            """PDF文件上传时的预览"""
            if pdf_file is None:
                return [], "等待上传文件..."
            
            # 保存临时文件用于预览
            temp_path = gradio_client.temp_dir / f"preview_{int(time.time())}.pdf"
            with open(temp_path, "wb") as f:
                f.write(pdf_file)
            
            # 生成预览图片
            images = gradio_client.pdf_to_images(str(temp_path))
            status = f"✅ 已上传PDF文件，共 {len(images)} 页"
            
            return images, status
        
        def on_load_sample():
            """加载示例文件"""
            file_data, images, status = gradio_client.load_sample_file()
            if file_data:
                # 创建临时文件并返回其路径给gr.File组件
                temp_sample_path = gradio_client.temp_dir / f"sample_{int(time.time())}.pdf"
                with open(temp_sample_path, "wb") as f:
                    f.write(file_data)
                return str(temp_sample_path), images, status
            else:
                return None, [], status
        
        def on_translate(pdf_file, lang_in, lang_out, file_type, progress=gr.Progress()):
            """执行翻译"""
            status, result_path, result_images, task_id, timing_info = gradio_client.translate_pdf(
                pdf_file, lang_in, lang_out, file_type, progress
            )
            
            # 返回结果
            download_visible = bool(result_path and os.path.exists(result_path))
            task_visible = bool(task_id)
            
            # 格式化时间信息显示
            timing_display_text = f"⏱️ **处理时间统计**：{timing_info}" if timing_info else "⏱️ **处理时间统计**：处理异常"
            
            return (
                status,  # translation_status
                result_images,  # result_preview
                gr.File(value=result_path if result_path else None, visible=download_visible),  # download_btn
                gr.Textbox(value=task_id, visible=task_visible),  # task_info
                timing_display_text  # timing_display
            )
        
        # 绑定事件
        
        # 示例文件加载
        sample_btn.click(
            on_load_sample,
            outputs=[pdf_input, original_preview, translation_status]
        )
        
        pdf_input.change(
            on_pdf_upload,
            inputs=[pdf_input],
            outputs=[original_preview, translation_status]
        )
        
        translate_btn.click(
            on_translate,
            inputs=[pdf_input, lang_in, lang_out, file_type],
            outputs=[translation_status, result_preview, download_btn, task_info, timing_display]
        )
        
        query_btn.click(
            gradio_client.get_task_status,
            inputs=[task_id_input],
            outputs=[task_status_output]
        )
    
    return demo

def main():
    """启动Gradio客户端"""
    import argparse
    
    # 显示管理员密码信息
    print("---" * 10)
    print(f"INFO: 管理员密码已设置。请使用 '{ADMIN_PASSWORD}' 在参数设置页面解锁敏感信息。")
    print("---" * 10)
    
    parser = argparse.ArgumentParser(description="BabelDOC Gradio客户端")
    parser.add_argument("--server-url", default="http://localhost:8000", help="API服务器地址")
    parser.add_argument("--host", default="0.0.0.0", help="Gradio服务器主机")
    parser.add_argument("--port", type=int, default=7860, help="Gradio服务器端口")
    parser.add_argument("--share", action="store_true", help="创建公共链接")
    
    args = parser.parse_args()
    
    print(f"正在启动Gradio客户端...")
    print(f"API服务器: {args.server_url}")
    print(f"Gradio地址: http://{args.host}:{args.port}")
    
    demo = create_gradio_interface(args.server_url)
    demo.launch(
        server_name=args.host,
        server_port=args.port,
        share=args.share,
        show_error=True,
        theme=gr.themes.Soft(),
        css=CUSTOM_CSS
    )

if __name__ == "__main__":
    main()