# MOURO - 城市配送多目标路径优化系统

Multi-Objective Urban Route Optimization

考虑应急程度与客户需求的城市配送多目标路径优化系统，基于改进蚁群算法求解。

## 环境要求

- Python 3.10+
- Node.js 18+
- npm 9+

## 后端部署

```bash
cd backend

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境（Windows）
venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 启动服务（端口 5000）
python run.py
```

## 前端部署

```bash
cd frontend

# 安装依赖
npm install

# 开发模式启动（端口 5173）
npm run dev

# 生产构建
npm run build
```

## 默认账号

- 用户名：admin
- 密码：admin123
