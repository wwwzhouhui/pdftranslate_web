#!/usr/bin/env python3
"""
BabelDOC字体预下载脚本
在Docker构建时调用，确保所有字体都被预先下载
"""

import os
import sys
import asyncio
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def download_all_fonts():
    """下载所有BabelDOC字体"""
    try:
        from babeldoc.assets import assets

        logger.info("=== 开始下载BabelDOC字体 ===")

        # 方法1: 尝试download_all_fonts
        try:
            logger.info("方法1: 调用download_all_fonts()")
            await assets.download_all_fonts()
            logger.info("✅ 方法1成功：字体下载完成")
            return True
        except Exception as e1:
            logger.warning(f"⚠️  方法1失败: {e1}")

        # 方法2: 尝试warmup_font_cache
        try:
            logger.info("方法2: 调用warmup_font_cache()")
            await assets.warmup_font_cache()
            logger.info("✅ 方法2成功：字体warmup完成")
            return True
        except Exception as e2:
            logger.warning(f"⚠️  方法2失败: {e2}")

        # 方法3: 手动触发关键字体下载
        try:
            logger.info("方法3: 手动下载关键字体")

            # 完整字体列表 - 覆盖所有可能需要的字体
            key_fonts = [
                # Noto 基础字体
                "NotoSans-Regular.ttf",
                "NotoSans-Bold.ttf",
                "NotoSans-Italic.ttf",
                "NotoSans-BoldItalic.ttf",
                "NotoSerif-Regular.ttf",
                "NotoSerif-Bold.ttf",
                "NotoSerif-Italic.ttf",
                "NotoSerif-BoldItalic.ttf",
                # 中文简体
                "SourceHanSansCN-Regular.ttf",
                "SourceHanSansCN-Bold.ttf",
                "SourceHanSerifCN-Regular.ttf",
                "SourceHanSerifCN-Bold.ttf",
                # 中文繁体（台湾）
                "SourceHanSansTW-Regular.ttf",
                "SourceHanSansTW-Bold.ttf",
                "SourceHanSerifTW-Regular.ttf",
                "SourceHanSerifTW-Bold.ttf",
                # 中文繁体（香港）
                "SourceHanSansHK-Regular.ttf",
                "SourceHanSansHK-Bold.ttf",
                "SourceHanSerifHK-Regular.ttf",
                "SourceHanSerifHK-Bold.ttf",
                # 韩语
                "SourceHanSansKR-Regular.ttf",
                "SourceHanSansKR-Bold.ttf",
                "SourceHanSerifKR-Regular.ttf",
                "SourceHanSerifKR-Bold.ttf",
                # 日语
                "SourceHanSansJP-Regular.ttf",
                "SourceHanSansJP-Bold.ttf",
                "SourceHanSerifJP-Regular.ttf",
                "SourceHanSerifJP-Bold.ttf",
                # 其他常用字体
                "LXGWWenKaiGB-Regular.1.520.ttf",
                "LXGWWenKaiTC-Regular.1.520.ttf",
                "MaruBuri-Regular.ttf",
                "KleeOne-Regular.ttf",
                "GoNotoKurrent-Regular.ttf",
                "GoNotoKurrent-Bold.ttf",
            ]

            # 分批下载避免并发过高
            batch_size = 5
            total_batches = (len(key_fonts) + batch_size - 1) // batch_size

            for batch_idx in range(total_batches):
                start_idx = batch_idx * batch_size
                end_idx = min(start_idx + batch_size, len(key_fonts))
                batch = key_fonts[start_idx:end_idx]

                logger.info(f"  下载批次 {batch_idx + 1}/{total_batches} ({len(batch)} 个字体)")
                tasks = []
                for font in batch:
                    async def download_font(font_name):
                        try:
                            font_path, font_metadata = await assets.get_font_and_metadata_async(font_name)
                            return font_name, font_path is not None, None
                        except Exception as e:
                            return font_name, False, str(e)

                    tasks.append(download_font(font))

                results = await asyncio.gather(*tasks, return_exceptions=True)
                for result in results:
                    font_name, success, error = result if not isinstance(result, Exception) else (None, False, str(result))
                    if font_name:
                        if success:
                            logger.info(f"    ✅ {font_name} 下载成功")
                        else:
                            logger.warning(f"    ⚠️  {font_name} 下载失败: {error}")

            logger.info(f"✅ 方法3完成：关键字体下载完成，共 {len(key_fonts)} 个字体")
            return True
        except Exception as e3:
            logger.error(f"❌ 方法3失败: {e3}")
            return False

    except Exception as e:
        logger.error(f"❌ 所有字体下载方法都失败: {e}")
        return False

def check_font_cache():
    """检查字体缓存"""
    try:
        font_cache_dir = os.path.expanduser("~/.cache/babeldoc/fonts")

        logger.info(f"=== 检查字体缓存目录 ===")
        logger.info(f"路径: {font_cache_dir}")

        if not os.path.exists(font_cache_dir):
            logger.warning("⚠️  字体缓存目录不存在")
            return False

        font_files = [f for f in os.listdir(font_cache_dir) if f.endswith('.ttf')]
        logger.info(f"✅ 找到 {len(font_files)} 个字体文件")

        if len(font_files) > 0:
            logger.info("字体文件列表:")
            for f in font_files[:10]:  # 只显示前10个
                font_path = os.path.join(font_cache_dir, f)
                size = os.path.getsize(font_path) if os.path.exists(font_path) else 0
                logger.info(f"  - {f} ({size / 1024 / 1024:.2f} MB)")

            if len(font_files) > 10:
                logger.info(f"  ... 还有 {len(font_files) - 10} 个文件")

            # 30个字体文件已经足够覆盖所有语言
            return len(font_files) >= 30
        else:
            logger.warning("⚠️  字体缓存目录为空")
            return False

    except Exception as e:
        logger.error(f"❌ 检查字体缓存失败: {e}")
        return False

async def main():
    """主函数"""
    logger.info("🚀 BabelDOC字体预下载工具启动")
    logger.info("=" * 60)

    # 下载字体
    success = await download_all_fonts()

    # 检查缓存
    cache_ok = check_font_cache()

    logger.info("=" * 60)

    if success and cache_ok:
        logger.info("✅ 字体预下载成功完成！")
        logger.info("字体缓存已准备就绪，运行时不会下载字体。")
        return 0
    elif cache_ok:
        logger.info("⚠️  字体预下载部分成功，但缓存已存在")
        return 0
    else:
        logger.error("❌ 字体预下载失败")
        logger.error("运行时可能需要下载字体，请检查网络连接。")
        return 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("❌ 用户取消操作")
        sys.exit(130)
    except Exception as e:
        logger.error(f"❌ 未处理的错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
