---
title: Blazemark 主题构建指南
date: 2025-10-02
tags: [Blazemark]
category: Blazemark
---
# Blazemark 主题构建指南

Blazemark 使用 **Jinja2 模板** + **Markdown 文件渲染** 来生成静态博客页面。本指南将带你从零创建一个自定义主题。

---

## 1. 主题目录结构

建议的主题目录结构如下：
```yaml
themes/
└── your_theme/
├── templates/
│ ├── index.html # 首页模板
│ ├── post.html # 文章页模板
│ ├── page.html # 页面模板
│ └── _partials/
│ ├── header.html # 顶部导航
│ ├── footer.html # 页脚
│ └── sidebar.html # 侧边栏
└── static/ # 静态资源（CSS/JS/图片）
├── css/
├── js/
└── img/
```

---

## 2. 模板变量说明

Blazemark 渲染模板时，会提供以下主要变量：

- `site`：站点信息，来自 `config.yml`
  ```yaml
  site.title         # 网站标题
  site.subtitle      # 副标题
  site.description   # 网站描述
  site.author        # 作者
  site.url           # 网站网址
  site.language      # 语言
  site.year          # 当前年份
  ```
- posts：文章列表（首页模板）
```python
posts = [
    {
        "meta": { "title": "文章标题", "date": "2025-10-03", ... },
        "url": "/slug/index.html"
    },
    ...
]
```
- post：单篇文章内容（文章页模板）
```python
post.title
post.content   # HTML 内容
post.meta      # 原始 meta 字典
post.url
```

---

## 3. 首页模板示例 (index.html)
```html
<!DOCTYPE html>
<html lang="{{ site.language }}">
<head>
  <meta charset="UTF-8">
  <title>{{ site.title }}</title>
</head>
<body>
  <header>
    <h1>{{ site.title }}</h1>
    <p>{{ site.subtitle }}</p>
  </header>

  <main>
    {% for p in posts %}
    <article>
      <h2><a href="{{ p.url }}">{{ p.meta.title }}</a></h2>
      <p>{{ p.meta.date }}</p>
    </article>
    {% endfor %}
  </main>

  <footer>
    <p>&copy; {{ site.year }} {{ site.author }}</p>
  </footer>
</body>
</html>
```

---

## 4. 文章页模板示例 (post.html)
```html
<!DOCTYPE html>
<html lang="{{ site.language }}">
<head>
  <meta charset="UTF-8">
  <title>{{ post.title }} - {{ site.title }}</title>
</head>
<body>
  <header>
    <h1>{{ post.title }}</h1>
    <p>{{ post.meta.date }}</p>
  </header>

  <main>
    {{ post.content | safe }}
  </main>

  <footer>
    <p>&copy; {{ site.year }} {{ site.author }}</p>
  </footer>
</body>
</html>
```

---

## 5. 静态资源管理

### CSS/JS 文件放在 static/ 下。

### 模板中使用相对路径引用：
```html
<link rel="stylesheet" href="/static/css/style.css">
<script src="/static/js/main.js"></script>
```

---

## 6. 主题启用

将主题文件夹放入 themes/。

在 config.yml 中指定主题：

```yaml
theme: your_theme
```


运行构建：
```bash
python blazemark.py build
```

---

## 7. 高级技巧

- 使用 _partials/ 文件夹拆分可复用组件，如导航栏、页脚、侧边栏。

- 支持 Jinja2 语法，使用 {% for %} 循环渲染文章列表。

- 可以使用插件系统动态修改渲染 HTML。

---

## 8. 调试
构建完成后，使用预览服务器查看效果：
```bash
python blazemark.py serve
```

输出文件在 public/ 目录下。
