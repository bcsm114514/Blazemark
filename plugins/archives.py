# plugins/archives.py
from jinja2 import Environment, FileSystemLoader
from pathlib import Path
from datetime import datetime
import yaml

def parse_front_matter(text: str):
    if text.startswith('---'):
        parts = text.split('---', 2)
        if len(parts) >= 3:
            try:
                meta = yaml.safe_load(parts[1]) or {}
            except:
                meta = {}
            return meta, parts[2].lstrip('\n')
    return {}, text

class ArchivesPlugin:
    def on_after_render(self, post, html):
        return html

    def on_build_finished(self, generator, data=None):
        output_dir = Path('public')
        theme_dir = generator.theme_dir

        # 获取文章列表
        posts = generator.get_posts(include_drafts=False)

        # 按年份+月份归档
        archives = {}
        for post in posts:
            d = post.get("date") or ""
            if isinstance(d, datetime):
                date_str = d.strftime("%Y-%m-%d")
            else:
                date_str = str(d)[:10]
            try:
                dt = datetime.strptime(date_str, "%Y-%m-%d")
            except:
                dt = datetime(1970, 1, 1)

            year = dt.year
            month = f"{dt.month:02d}"  # 格式化成两位数字 01, 02, ...

            archives.setdefault(year, {}).setdefault(month, []).append(post)

        # 渲染模板
        env = Environment(loader=FileSystemLoader(str(theme_dir / "templates")))
        try:
            tpl = env.get_template("archives.html")
        except:
            tpl_content = """
            <h1>文章归档</h1>
            {% for year, months in archives|dictsort(reverse=True) %}
              <h2>{{ year }}</h2>
              {% for month, posts in months|dictsort(reverse=True) %}
                <details>
                  <summary>{{ month }}月</summary>
                  <ul>
                    {% for p in posts %}
                      <li><a href="{{ p.url }}">{{ p.title }}</a> - {{ p.date }}</li>
                    {% endfor %}
                  </ul>
                </details>
              {% endfor %}
            {% endfor %}
            """
            tpl = env.from_string(tpl_content)

        html = tpl.render(
            site=getattr(generator, "config", {}),
            archives=archives,
            page={"title": "文章归档"},
            now=datetime.now
        )

        out_path = output_dir / "archives" / "index.html"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(html, encoding="utf-8")
        print(f"[Archives插件] 归档页生成: {out_path}")

plugin = ArchivesPlugin()
