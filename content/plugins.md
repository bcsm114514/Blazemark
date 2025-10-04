---
title: Blazemark 插件构建指南
date: 2025-10-02
tags: [Blazemark]
category: Blazemark
---
# 📦 Blazemark 插件构建指南

Blazemark 支持插件扩展功能，用户可以通过编写插件对生成流程进行修改，例如自动加标签、修改文章内容、添加额外字段等。

---

## 🔹 1. 插件基础结构

Blazemark 的插件基类是：

```python
class Plugin:
    def on_config(self, config: dict) -> dict:
        return config

    def on_post(self, post: "Post") -> "Post":
        return post

    def on_build(self, site: dict) -> dict:
        return site
```
三个可选的钩子方法：

- ```
  on_config(config)
  ```
  在加载配置后执行，可修改 config。

- ```
  on_post(post)
  ```
  在处理每篇文章时执行，可修改文章对象。

- ```
  on_build(site)
  ```
  在整个网站生成后执行，可修改 site 对象。

---
## 🔹 2. 数据结构
Post 对象
```python
@dataclass
class Post:
    src: str       # 源文件路径
    slug: str      # 文章 slug
    title: str     # 标题
    date: str      # 日期
    content: str   # HTML 内容
    meta: dict     # 元数据（从 Markdown frontmatter 读取）
    url: str = ""  # 最终生成的链接
```

Site 对象
```python
{
    "config": {...},   # 站点配置
    "posts": [Post],   # 全部文章
    "pages": [Post],   # 额外页面
}
```

---

## 🔹 3. 插件示例
示例 1：自动生成rss.xml与sitemap.xml
```python
import os
from pathlib import Path
from datetime import datetime
from xml.sax.saxutils import escape

from blazemark import Plugin
from urllib.parse import quote

class RSSAndSitemapAdvancedPlugin(Plugin):
    def on_build_finished(self, generator, data=None):
        output_dir = getattr(generator, "OUTPUT_DIR", Path("public"))
        site = generator.config
        site_url = site.get("url", "http://example.com").rstrip("/")

        posts = generator.get_posts(include_drafts=False)

        # -------- 生成 RSS.xml --------
        rss_items = []
        for post in posts:
            url = f"{site_url}{post['url']}"
            title = escape(post['title'])
            description = escape(post.get('description', post.get('content', '')[:200]))
            pub_date = post.get('date', datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0000"))
            categories = post.get('category', [])
            if isinstance(categories, str):
                categories = [categories]
            tags = post.get('tags', [])
            if isinstance(tags, str):
                tags = [tags]

            category_tags = "".join([f"<category>{escape(c)}</category>" for c in categories+tags])
            rss_items.append(f"""
    <item>
      <title>{title}</title>
      <link>{url}</link>
      <description>{description}</description>
      <pubDate>{pub_date}</pubDate>
      {category_tags}
      <guid>{url}</guid>
    </item>
            """.strip())

        rss_xml = f"""<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0">
<channel>
  <title>{escape(site.get('title', 'Blazemark Blog'))}</title>
  <link>{site_url}/</link>
  <description>{escape(site.get('description', ''))}</description>
  {''.join(rss_items)}
</channel>
</rss>
        """

        Path(output_dir).mkdir(parents=True, exist_ok=True)
        with open(Path(output_dir)/"rss.xml", "w", encoding="utf-8") as f:
            f.write(rss_xml)
        print("[插件] RSS.xml 已生成")

        # -------- 生成 Sitemap.xml --------
        urls = set()
        for post in posts:
            urls.add(post['url'])

        # 标签页面
        all_tags = set()
        all_categories = set()
        for post in posts:
            tags = post.get('tags', [])
            if isinstance(tags, str):
                tags = [tags]
            all_tags.update(tags)
            categories = post.get('category', [])
            if isinstance(categories, str):
                categories = [categories]
            all_categories.update(categories)

        for tag in all_tags:
            urls.add(f"/tag/{quote(tag)}/")
        for cat in all_categories:
            urls.add(f"/category/{quote(cat)}/")

        sitemap_items = []
        for url in urls:
            full_url = f"{site_url}{url}"
            lastmod = datetime.now().strftime("%Y-%m-%d")
            sitemap_items.append(f"""
  <url>
    <loc>{full_url}</loc>
    <lastmod>{lastmod}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.8</priority>
  </url>
            """.strip())

        sitemap_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{''.join(sitemap_items)}
</urlset>
        """

        with open(Path(output_dir)/"sitemap.xml", "w", encoding="utf-8") as f:
            f.write(sitemap_xml)
        print("[插件] Sitemap.xml 已生成")

# 实例化插件
plugin = RSSAndSitemapAdvancedPlugin()
```

示例 2：字数统计
```python
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
```

---

## 🔹 4. 插件开发注意事项

**保持纯函数式修改**：每个钩子应该返回修改后的对象，而不是直接操作全局变量。

**避免重名冲突**：插件类名保持唯一。

**调试建议**：在插件中可以 print() 输出调试信息。

**安全性**：插件可以修改所有数据，请避免执行危险操作。