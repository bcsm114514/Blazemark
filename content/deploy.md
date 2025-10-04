---
title: 部署指南
date: 2025-10-02
tags: [Blazemark]
category: Blazemark
---
# Deploy部署指南

## 1️⃣ 准备工作

**1. 生成 SSH Key**
```bash
ssh-keygen -t ed25519 -C "github-actions-deploy" -f blazemark_deploy_key
```
会生成 blazemark_deploy_key 和 blazemark_deploy_key.pub

**2. 添加公钥到 GitHub 仓库**

- 打开你的 GitHub 仓库(username.github.io) → Settings → Deploy keys → Add deploy key

- Title 填：Blazemark Deploy Key

Paste 公钥内容 blazemark_deploy_key.pub

勾选 "Allow write access" ✅

**3. 添加私钥到 GitHub Secrets**

- 打开仓库 → Settings → Secrets and variables → Actions → New repository secret

- Name: DEPLOY_KEY

- Value: 复制私钥 blazemark_deploy_key 内容

---

## 2️⃣ GitHub 配置

**1. 复刻模板**
- 点击**Use this template**复刻[模板](https://github.com/bcsm114514/Blazemark)

**2. 编辑Actions**
- 打开```.github/workflows/deploy.yml```
```yaml
name: Deploy Blazemark Blog

on:
  push:
    branches:
      - main   # 当 main 分支有更新时触发

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest

    steps:
      # 1. 检出代码
      - name: Checkout repository
        uses: actions/checkout@v4

      # 2. 设置 Python
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.11"

      # 3. 安装依赖
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt || echo "No requirements.txt found"

      # 4. 构建 Blazemark 静态站点
      - name: Build site
        run: |
          python blazemark.py build --force

      # 5. 部署到 GitHub Pages
      - name: Deploy to Github Pages
        env:
          DEPLOY_KEY: ${{ secrets.DEPLOY_KEY }}
        run: |
          mkdir -p ~/.ssh
          echo "$DEPLOY_KEY" > ~/.ssh/id_ed25519
          chmod 600 ~/.ssh/id_ed25519
          ssh-keyscan github.com >> ~/.ssh/known_hosts
  
          cd public
          git init
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git branch -M main
          git remote add origin git@github.com:username/username.github.io.git
          git add .
          git commit -m "Deploy site via GitHub Actions"
          git push -f origin main
```
将文件中的username改成实际的用户名

### 🔹 说明

Build 过程：

```python blazemark.py build --force``` 会重新生成所有页面

SSH 部署：

使用 DEPLOY_KEY 私钥认证

强制推送 ```git push -f origin main```，保证覆盖远程仓库内容

分支：

远程仓库默认 ```main```，如果不是，请修改 ```deploy.yml``` 中 ```main``` 为目标分支

注意: 记得开启Pages仓库的GitHub Pages功能

---

## 3️⃣ 部署至其他平台
- 在其他平台选择最终静态文件仓库即可(可为私库)
- 使用其他支持Python的平台
- 手动上传