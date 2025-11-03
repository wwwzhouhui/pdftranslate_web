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
        # 配置缓存
        self.config_cache = {
            "openai_api_key": "",
            "openai_model": "",
            "openai_base_url": ""
        }
        
    def update_config(self, api_key: str = None, model: str = None, base_url: str = None) -> str:
        """更新配置缓存"""
        if api_key is not None:
            self.config_cache["openai_api_key"] = api_key
        if model is not None:
            self.config_cache["openai_model"] = model
        if base_url is not None:
            self.config_cache["openai_base_url"] = base_url
        return "✅ 配置已更新（下次翻译时生效）"
    
    def get_masked_api_key(self, api_key: str) -> str:
        """获取遮蔽的API密钥"""
        if not api_key or len(api_key) < 8:
            return api_key
        return api_key[:4] + "*" * (len(api_key) - 8) + api_key[-4:]
        
    def check_server_status(self) -> Tuple[str, Dict]:
        """检查服务器状态和配置"""
        try:
            if not self.client.health_check():
                return "❌ 服务器离线", {}
            
            config = self.client.get_server_config()
            
            # 更新配置缓存为服务器当前值
            if not self.config_cache["openai_api_key"]:
                self.config_cache["openai_api_key"] = "sk-****"  # 默认占位符
            if not self.config_cache["openai_model"]:
                self.config_cache["openai_model"] = config['config']['openai_model']
            if not self.config_cache["openai_base_url"]:
                self.config_cache["openai_base_url"] = ""  # 服务器不返回base_url
            
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

def create_gradio_interface(server_url: str = "http://localhost:8000"):
    """创建Gradio界面"""
    gradio_client = GradioClient(server_url)
    
    with gr.Blocks(
        title="pdftranslate PDF翻译工具",
        theme=gr.themes.Soft(),
        css="""
        .main-container { max-width: 1400px; margin: 0 auto; }
        .preview-container { height: 600px; overflow-y: auto; }
        .status-box { background-color: #f8f9fa; padding: 15px; border-radius: 8px; }
        
        /* 表格样式配置 */
        .config-table {
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            overflow: hidden;
            margin: 16px 0;
        }
        .config-header-row {
            background-color: #6366f1 !important;
            margin: 0 !important;
        }
        .config-header { 
            background-color: #6366f1; 
            color: white; 
            padding: 12px 16px; 
            margin: 0; 
            text-align: center;
            font-weight: bold;
            border-right: 1px solid #5b63d4;
        }
        .config-row { 
            border-bottom: 1px solid #e5e7eb; 
            padding: 12px 16px; 
            margin: 0 !important;
            background-color: white;
        }
        .config-row:hover { 
            background-color: #f8fafc; 
        }
        .config-row:last-child {
            border-bottom: none;
        }
        .config-actions {
            background-color: #f9fafb;
            padding: 16px;
            border-top: 1px solid #e5e7eb;
            margin: 0 !important;
        }
        .config-status {
            background-color: #f0f9ff;
            padding: 12px 16px;
            border-radius: 6px;
            border-left: 4px solid #3b82f6;
            margin: 16px 0;
        }
        """
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
                            show_download_button=False,
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
                            show_download_button=False,
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

            with gr.TabItem("⚙️ 参数设置"):
                gr.Markdown("### 🔧 核心API配置")
                gr.Markdown("在此修改OpenAI API配置，修改后立即生效于下次翻译任务。")
                
                # 用于跟踪当前会话是否已认证的内部状态
                session_authenticated = gr.State(False)
                
                # 管理员认证模块
                with gr.Group() as auth_group:
                    gr.Markdown("#### **管理员认证**")
                    admin_password_input = gr.Textbox(
                        label="请输入管理员密码以查看或修改敏感配置",
                        type="password",
                        placeholder=f"默认密码是 'admin123'，或通过环境变量 ADMIN_PASSWORD 进行设置"
                    )
                    unlock_button = gr.Button("🔓 解锁", variant="primary")
                
                # 将所有需要被锁定的组件收集到一个列表中
                interactive_settings_components = []
                
                # 表格样式的配置界面
                with gr.Group(elem_classes=["config-table"]):
                    # 表格头部
                    with gr.Row(elem_classes=["config-header-row"]):
                        with gr.Column(scale=1):
                            gr.HTML("<div class='config-header'>配置项</div>")
                        with gr.Column(scale=2):
                            gr.HTML("<div class='config-header'>当前值</div>")
                        with gr.Column(scale=1):
                            gr.HTML("<div class='config-header'>操作</div>")
                    
                    # API Key 行
                    with gr.Row(elem_classes=["config-row"]):
                        with gr.Column(scale=1):
                            gr.Markdown("**OpenAI API Key**")
                        with gr.Column(scale=2):
                            api_key_input = gr.Textbox(
                                placeholder="输入你的API密钥",
                                type="password",
                                container=False,
                                show_label=False,
                                interactive=False
                            )
                            interactive_settings_components.append(api_key_input)
                        with gr.Column(scale=1):
                            show_api_key_btn = gr.Button("👁 显示", size="sm", interactive=False)
                            interactive_settings_components.append(show_api_key_btn)
                    
                    # 模型名称行
                    with gr.Row(elem_classes=["config-row"]):
                        with gr.Column(scale=1):
                            gr.Markdown("**模型名称**")
                        with gr.Column(scale=2):
                            model_input = gr.Textbox(
                                placeholder="如: deepseek-ai/DeepSeek-V3",
                                container=False,
                                show_label=False,
                                interactive=False
                            )
                            interactive_settings_components.append(model_input)
                        with gr.Column(scale=1):
                            gr.HTML("<span></span>")  # 空占位符
                    
                    # Base URL 行
                    with gr.Row(elem_classes=["config-row"]):
                        with gr.Column(scale=1):
                            gr.Markdown("**Base URL**")
                        with gr.Column(scale=2):
                            base_url_input = gr.Textbox(
                                placeholder="如: https://api.siliconflow.cn/v1",
                                container=False,
                                show_label=False,
                                interactive=False
                            )
                            interactive_settings_components.append(base_url_input)
                        with gr.Column(scale=1):
                            gr.HTML("<span></span>")  # 空占位符
                    
                    # 操作按钮行
                    with gr.Row(elem_classes=["config-actions"]):
                        save_config_btn = gr.Button(
                            "💾 保存配置",
                            variant="primary",
                            size="sm",
                            interactive=False
                        )
                        interactive_settings_components.append(save_config_btn)
                        
                # 配置状态显示
                config_status = gr.Markdown("等待配置...", elem_classes=["config-status"])
                
                # 创建一个 State 来传递需要解锁的组件数量
                num_components = gr.State(len(interactive_settings_components))
        
        def update_server_status():
            status_text, config = gradio_client.check_server_status()
            return status_text
        
        def unlock_settings(password_attempt, num_components_to_unlock):
            """
            检查管理员密码。如果正确，解锁设置UI并隐藏认证模块。
            """
            if password_attempt == ADMIN_PASSWORD:
                gr.Info("认证成功！设置已解锁。")
                # 为每一个需要解锁的组件创建一个更新指令
                unlock_updates = [gr.update(interactive=True) for _ in range(num_components_to_unlock)]
                # 返回所有更新指令，以及对认证组和会话状态的更新
                # The * operator unpacks the list into individual arguments for the tuple
                return *unlock_updates, gr.update(visible=False), True
            else:
                # 密码错误时，通过 gr.Error 弹出提示，UI不会有任何变化
                raise gr.Error("管理员密码错误！")
        
        def toggle_api_key_visibility(api_key_value):
            """切换API密钥的显示/隐藏状态"""
            # 根据当前值判断是否为隐藏状态
            # 如果包含*号，则当前是遮蔽状态，需要显示原文
            if api_key_value and "*" in api_key_value:
                # 从缓存中获取原始值
                original_key = gradio_client.config_cache.get('openai_api_key', '')
                return gr.update(value=original_key, type="text")
            else:
                # 当前显示原文，需要遮蔽
                if api_key_value:
                    # 保存到缓存
                    gradio_client.config_cache['openai_api_key'] = api_key_value
                    masked_key = gradio_client.get_masked_api_key(api_key_value)
                    return gr.update(value=masked_key, type="password")
                else:
                    return gr.update(type="password")
        
        def save_config(api_key, model, base_url):
            """保存配置"""
            status = gradio_client.update_config(api_key=api_key, model=model, base_url=base_url)
            
            # 从配置缓存生成当前配置显示
            config_info = f"""**当前配置:**
- API Key: {gradio_client.get_masked_api_key(gradio_client.config_cache['openai_api_key'])}
- 模型: {gradio_client.config_cache['openai_model'] or '未设置'}
- Base URL: {gradio_client.config_cache['openai_base_url'] or '未设置'}
"""
            return status + "\n\n" + config_info
        
        def load_config_from_server():
            """从环境变量和服务器加载配置到输入框"""
            import os
            from dotenv import load_dotenv
            
            # 加载.env文件
            load_dotenv()
            
            # 从环境变量读取配置
            api_key = os.getenv("OPENAI_API_KEY", "")
            model = os.getenv("OPENAI_MODEL", "")
            base_url = os.getenv("OPENAI_BASE_URL", "")
            
            # 更新配置缓存
            gradio_client.config_cache.update({
                "openai_api_key": api_key,
                "openai_model": model,
                "openai_base_url": base_url
            })
            
            # 返回遮蔽后的API Key和其他配置
            masked_api_key = gradio_client.get_masked_api_key(api_key) if api_key else ""
            
            return masked_api_key, model, base_url
        
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
        # 管理员认证事件
        unlock_button.click(
            fn=unlock_settings,
            inputs=[admin_password_input, num_components],
            # outputs 列表现在包含所有被控制的组件、认证组和会话状态
            outputs=interactive_settings_components + [auth_group, session_authenticated]
        )
        
        # 配置相关事件
        show_api_key_btn.click(
            toggle_api_key_visibility,
            inputs=[api_key_input],
            outputs=[api_key_input]
        )
        
        save_config_btn.click(
            save_config,
            inputs=[api_key_input, model_input, base_url_input],
            outputs=[config_status]
        )
        
        # 页面加载时从服务器加载配置
        demo.load(
            load_config_from_server,
            outputs=[api_key_input, model_input, base_url_input]
        )
        
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
        show_error=True
    )

if __name__ == "__main__":
    main()