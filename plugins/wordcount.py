from blazemark import Plugin, Post
import re

class WordCountPlugin(Plugin):
    def count_words(self, text: str) -> int:
        """统计文本中的中文汉字 + 英文单词"""
        cn_count = len(re.findall(r'[\u4e00-\u9fff]', text))
        en_count = len(re.findall(r'\b[a-zA-Z0-9]+\b', text))
        return cn_count + en_count

    def on_after_render(self, post: Post, html_content: str):
        # 统计 Markdown 原文
        words = self.count_words(post.content)
        footer = f"<p><em>字数统计: {words} 字</em></p>"
        # 插入文章末尾
        html_content = html_content.replace("</article>", footer + "</article>")
        return html_content

plugin = WordCountPlugin()
