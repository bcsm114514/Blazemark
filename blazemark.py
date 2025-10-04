#!/usr/bin/env python3
"""
Blazemark - A blazing fast Python static blog generator
"""

import os, sys, time, json, hashlib, shutil, argparse, multiprocessing
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
import cmarkgfm
from jinja2 import Environment, FileSystemLoader
import yaml
import http.server
import socketserver
import webbrowser
from datetime import datetime, date
from dataclasses import dataclass
import re

# -------- 数据类 & 插件系统 --------
@dataclass
class Post:
    src: str
    slug: str
    title: str
    date: str
    content: str
    meta: dict
    url: str = ""

class Plugin:
    def on_after_render(self, post: Post, html: str):
        return html
    def on_sidebar_render(self, sidebar_html: str):
        return sidebar_html
    def on_build_finished(self, generator, data=None):
        pass

# -------- 工具函数 --------
def read_file(p: Path): return p.read_text(encoding='utf-8')
def write_file(p: Path, t: str):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(t, encoding='utf-8')
def compute_hash(s: str): return hashlib.sha1(s.encode()).hexdigest()
def safe_slug(path: Path): return path.stem

def parse_front_matter(text: str):
    """解析 Markdown 文件的 YAML Front Matter"""
    if text.startswith('---'):
        parts = text.split('---', 2)
        if len(parts) >= 3:
            try:
                meta = yaml.safe_load(parts[1]) or {}
            except Exception as e:
                print(f"[FrontMatter解析错误] {e}")
                meta = {}
            content = parts[2].lstrip('\n')
            return meta, content
    return {}, text

# -------- 配置 --------
ROOT = Path('.')
CONTENT_DIR = ROOT / 'content'
THEMES_DIR = ROOT / 'themes'
PLUGINS_DIR = ROOT / 'plugins'
OUTPUT_DIR = ROOT / 'public'
CACHE_FILE = ROOT / '.blazemark_cache.json'
DEFAULT_THEME = 'default'

def load_plugins():
    plugins = []
    if not PLUGINS_DIR.exists(): return plugins
    sys.path.insert(0, str(PLUGINS_DIR.resolve()))
    for p in PLUGINS_DIR.glob("*.py"):
        try:
            mod = __import__(p.stem)
            if hasattr(mod, "plugin"):
                plugins.append(mod.plugin)
        except Exception as e:
            print(f"[插件错误] {p}: {e}")
    return plugins

# -------- 并行渲染 --------
def render_post_worker(args):
    src, theme_dir, site_meta = args
    src_path = Path(src)
    text = src_path.read_text(encoding="utf-8")
    meta, body = parse_front_matter(text)

    slug = meta.get("slug") or src_path.stem
    title = meta.get("title", slug)
    html_body = cmarkgfm.github_flavored_markdown_to_html(body)

    html_body = re.sub(
        r'<pre lang="([a-zA-Z0-9]+)"><code>',
        r'<pre><code class="language-\1">',
        html_body
    )

    env = Environment(loader=FileSystemLoader(str(Path(theme_dir)/"templates")))
    tpl = env.get_template("post.html")
    out_html = tpl.render(
        post={"title": title, "content": html_body, "meta": meta},
        site=site_meta,
        page=meta
    )

    return {
        "src": str(src_path),
        "slug": slug,
        "html": out_html,
        "meta": {**meta, "content_raw": body},
        "url": f"/{slug}/index.html"
    }

# -------- 主生成器 --------
class Blazemark:
    def __init__(self, theme=None, workers=None):
        self.config = self.load_config()
        self.theme = theme or self.config.get("theme", DEFAULT_THEME)
        self.theme_dir = THEMES_DIR / self.theme
        self.cache = self._load_cache()
        self.plugins = load_plugins()
        self.workers = workers or self._optimal_workers()

    def load_config(self):
        cfg_file = ROOT / "config.yml"
        if cfg_file.exists():
            try:
                return yaml.safe_load(cfg_file.read_text(encoding="utf-8")) or {}
            except Exception as e:
                print(f"[配置错误] {e}")
                return {}
        return {}

    def _optimal_workers(self):
        cpu = multiprocessing.cpu_count()
        n_posts = len(list(CONTENT_DIR.glob("*.md")))
        return min(cpu, max(2, n_posts))

    def _load_cache(self):
        if CACHE_FILE.exists():
            try: return json.loads(read_file(CACHE_FILE))
            except: return {"posts": {}}
        return {"posts": {}}

    def _save_cache(self):
        write_file(CACHE_FILE, json.dumps(self.cache, indent=2))

    def discover_posts_and_pages(self):
        posts = sorted(CONTENT_DIR.glob("*.md"))
        pages_dir = CONTENT_DIR / "pages"
        pages = sorted(pages_dir.glob("*.md")) if pages_dir.exists() else []
        return posts, pages

    def clean(self):
        if OUTPUT_DIR.exists(): shutil.rmtree(OUTPUT_DIR)
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        if CACHE_FILE.exists(): CACHE_FILE.unlink()
        print("已清理输出目录和缓存。")

    def copy_static(self):
        src = self.theme_dir / "static"
        if src.exists():
            dst = OUTPUT_DIR / "static"
            dst.mkdir(parents=True, exist_ok=True)
            for item in src.iterdir():
                if item.is_file():
                    shutil.copy2(item, dst / item.name)
                elif item.is_dir():
                    shutil.copytree(item, dst / item.name, dirs_exist_ok=True)

    def build(self, force=False):
        t0 = time.time()
        site_meta = {
            "title": self.config.get("title", "Blazemark Blog"),
            "subtitle": self.config.get("subtitle", ""),
            "description": self.config.get("description", ""),
            "author": self.config.get("author", ""),
            "url": self.config.get("url", ""),
            "language": self.config.get("language", "en"),
            "year": datetime.now().year
        }

        posts_list, pages_list = self.discover_posts_and_pages()
        all_files = posts_list + pages_list

        tasks = []
        for f in all_files:
            text = read_file(f)
            meta, _ = parse_front_matter(text)
            if meta.get("draft", False) and not force:
                continue
            h = compute_hash(text)
            cached = self.cache.get("posts", {}).get(str(f))
            if force or not cached or cached["hash"] != h:
                tasks.append((str(f), str(self.theme_dir), site_meta))

        results = []
        if tasks:
            with ProcessPoolExecutor(max_workers=self.workers) as ex:
                futures = [ex.submit(render_post_worker, a) for a in tasks]
                for fut in as_completed(futures):
                    results.append(fut.result())

        # 插件处理 & 写入 public
        raw_post_list = []
        all_tags = set()
        all_categories = set()
        for res in results:
            slug = res["slug"]
            out_path = OUTPUT_DIR / slug / "index.html"

            for p in self.plugins:
                try:
                    res["html"] = p.on_after_render(
                        Post(res["src"], slug,
                            res["meta"].get("title", slug),
                            res["meta"].get("published", ""),
                            res["meta"]["content_raw"], res["meta"],
                            url=res["url"]),
                        res["html"]
                    )
                except Exception as e:
                    print(f"[插件错误] {p.__class__.__name__}.on_after_render: {e}")

            if not res["meta"].get("draft", False) or force:
                write_file(out_path, res["html"])
                src = res["src"]
                st = Path(src).stat()
                self.cache.setdefault("posts", {})[src] = {
                    "mtime": st.st_mtime,
                    "hash": compute_hash(read_file(Path(src))),
                    "output": str(out_path),
                }

                # 收集首页/标签/分类数据
                raw_post_list.append({
                    "meta": res["meta"],
                    "url": "/" + Path(out_path).relative_to(OUTPUT_DIR).as_posix()
                })
                tags = res["meta"].get("tags", [])
                if isinstance(tags, str):
                    tags = [tags]
                all_tags.update(tags)
                categories = res["meta"].get("category", [])
                if isinstance(categories, str):
                    categories = [categories]
                all_categories.update(categories)

        self.copy_static()

        env = Environment(loader=FileSystemLoader(str(self.theme_dir / "templates")))
        index_tpl = env.get_template("index.html")

        # 按日期降序排序
        post_list = sorted(
            raw_post_list,
            key=lambda p: p['meta'].get('date', datetime(1970, 1, 1)),
            reverse=True
        )


        # 渲染首页
        index_html = index_tpl.render(
            posts=post_list,
            site=site_meta,
            page={"title": site_meta["title"], "banner": None},
            all_tags=sorted(all_tags),
            all_categories=sorted(all_categories)
        )
        write_file(OUTPUT_DIR/"index.html", index_html)

        # ----------------- 渲染标签页面 -----------------
        tags_tpl = env.get_template("tags.html")
        for tag in all_tags:
            posts_for_tag = [p for p in raw_post_list if tag in p["meta"].get("tags", [])]
            out_path = OUTPUT_DIR / "tag" / tag / "index.html"
            out_path.parent.mkdir(parents=True, exist_ok=True)
            html = tags_tpl.render(
                tag=tag,
                posts=posts_for_tag,
                site=site_meta,
                page={"title": f"标签：{tag}"}
            )
            write_file(out_path, html)

        # 生成 /tag/index.html 标签索引页
        tags_index_path = OUTPUT_DIR / "tag" / "index.html"
        tags_index_path.parent.mkdir(parents=True, exist_ok=True)
        html = tags_tpl.render(
            tag=None,
            posts=[],
            site=site_meta,
            page={"title": "所有标签"},
            all_tags=sorted(all_tags)
        )
        write_file(tags_index_path, html)

        # ----------------- 渲染分类页面 -----------------
        cat_tpl = env.get_template("category.html")
        for cat in all_categories:
            posts_for_cat = [p for p in raw_post_list if cat in p["meta"].get("category", [])]
            out_path = OUTPUT_DIR / "category" / cat / "index.html"
            out_path.parent.mkdir(parents=True, exist_ok=True)
            html = cat_tpl.render(
                category=cat,
                posts=posts_for_cat,
                site=site_meta,
                page={"title": f"分类：{cat}"}
            )
            write_file(out_path, html)

        # 生成 /category/index.html 分类索引页
        cats_index_path = OUTPUT_DIR / "category" / "index.html"
        cats_index_path.parent.mkdir(parents=True, exist_ok=True)
        html = cat_tpl.render(
            category=None,
            posts=[],
            site=site_meta,
            page={"title": "所有分类"},
            all_categories=sorted(all_categories)
        )
        write_file(cats_index_path, html)

        # 保存缓存
        self._save_cache()
        print(f"构建完成，用时 {time.time()-t0:.2f}s, 输出目录: {OUTPUT_DIR}")

        # 调用插件
        for p in self.plugins:
            try:
                p.on_build_finished(self)
            except Exception as e:
                print(f"[插件错误] {p.__class__.__name__}.on_build_finished: {e}")


    # -------- 获取文章列表 --------
    def get_posts(self, include_drafts=False):
        posts = []
        for s, info in self.cache["posts"].items():
            meta, _ = parse_front_matter(read_file(Path(s)))
            if meta.get("draft", False) and not include_drafts:
                continue
            url = "/" + Path(info["output"]).relative_to(OUTPUT_DIR).as_posix()
            posts.append({
                "title": meta.get("title", ""),
                "date": meta.get("date", ""),
                "category": meta.get("category", ""),
                "tags": meta.get("tags", []),
                "url": url,
                "content": meta.get("content_raw", "")
            })
        return posts

# -------- 本地预览服务器 --------
def serve(port=8000):
    os.chdir(OUTPUT_DIR)
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", port), handler) as httpd:
        print(f"预览服务器已启动: http://127.0.0.1:{port}")
        print("按 Ctrl+C 停止服务器。")
        try: webbrowser.open(f"http://127.0.0.1:{port}")
        except: pass
        httpd.serve_forever()

# -------- CLI --------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("cmd", choices=["build","clean","init","serve"], nargs="?", default="build")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--port", type=int, default=8000, help="预览服务器端口")
    args = parser.parse_args()

    bm = Blazemark()

    if args.cmd=="clean":
        bm.clean()
        return
    if args.cmd=="init":
        CONTENT_DIR.mkdir(parents=True, exist_ok=True)
        f = CONTENT_DIR / "hello-world.md"
        if not f.exists():
            write_file(f, """---
title: Hello World
date: 2025-10-03
---
# 欢迎使用 Blazemark

这是你的第一篇文章！
""")
        print("已初始化示例文章和主题。")
        return
    if args.cmd=="build":
        bm.build(force=args.force)
        return
    if args.cmd=="serve":
        bm.build(force=args.force)
        serve(port=args.port)
        return

if __name__=="__main__": main()
