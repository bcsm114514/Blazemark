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
