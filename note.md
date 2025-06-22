
## 1. 准备环境

1. 创建并激活虚拟环境：

```bash
python3 -m venv venv
source venv/bin/activate
```

2. **安装依赖**

```bash
pip install Flask PyGithub python-dotenv
```

3. **环境变量**
    在项目根目录创建 `.env`：

```bash
GITHUB_TOKEN=...
WEBHOOK_SECRET=...
PORT=3000                      # 如果需要自定义端口
```

- **GITHUB_TOKEN**：创建 Personal Access Token，开启 `repo` 范围，确保可以读取 & 更新 `README.md`。
- **WEBHOOK_SECRET**：Webhook 验签用，GitHub 仓库设置时填同一串。

## 2. 编写 Webhook 服务（`app.py`）

## 3. 本地测试
### 1. 准备好环境

1. **激活虚拟环境**
    
    ```bash
    source venv/bin/activate
    ```
    
2. **确保依赖已装好**
    
    ```bash
    pip install Flask PyGithub python-dotenv
    ```
    
3. **检查 `.env`**
    
    ```
    GITHUB_TOKEN=ghp_…         # 你的 PAT，勾选 repo 权限
    WEBHOOK_SECRET=…            # 你刚刚生成的那个 64 字符十六进制串
    PORT=3000                   # 或你喜欢的端口
    ```
    

### 2. 本地启动 Flask 服务

在项目根目录下直接运行：

```bash
python app.py
```

如果一切配置正确，你应该会在控制台看到类似：

```
 * Running on http://0.0.0.0:3000/ (Press CTRL+C to quit)
```


### 3. 暴露本地服务到公网

GitHub Webhook 必须能够访问到你的服务地址，这里推荐两种做法：

#### 方案 A：使用 ngrok

1. **安装 ngrok**（如果你已装可跳过）
    
    ```bash
    brew install ngrok
    ```
    
2. **启动隧道**
    
    ```bash
    ngrok http 3000
    ```
    
3. **记下 Forwarding 地址**，形如 `https://abcd1234.ngrok.io`
    
#### 方案 B：使用 smee.io

1. **打开 smee.io**  
    访问 [https://smee.io](https://smee.io/) ，会自动为你分配一个随机的 channel URL，例如：
    
    ```
    https://smee.io/abc123xyz
    ```
    
2. **启动 smee-client**  
    在本地项目里安装并运行 smee-client，把外部请求转发到你的 Flask 服务。
    
    - **全局安装**（可选）：
        
        ```bash
        npm install -g smee-client
        ```
        
    - **或直接用 npx**（无需全局安装）：
        
        ```bash
npx smee-client \
  --url https://smee.io/Jhp69MIO10fKYur0 \
  --target http://localhost:3000/webhook

        ```
        
    这里：
    - `--url` 后面填你的 smee.io channel
    - `--target` 填本地服务地址（含 `/webhook` 路径）
    - `--log` 会把转发的请求打印到控制台，方便调试
        
3. **在 GitHub 仓库配置 Webhook**
    
    - **Payload URL**：改成你的 smee channel URL（不带 `/webhook`），例如
        
        ```
        https://smee.io/abc123xyz
        ```
        
    - **Content type**：`application/json`
        
    - **Secret**：填 `.env` 里的一样的 `WEBHOOK_SECRET`
        
    - **Events**：只选 **Pull requests**
        
4. **触发并观察**
    
    - 在本地同时分别运行你的 Flask 服务（`python app.py`）和 smee-client。
        
    - 打开或更新一个 PR，smee 会把 GitHub 发来的 POST 请求“桥接”到本地 `http://localhost:3000/webhook`。
        
    - 你能在 smee-client 终端和 Flask 终端都看到请求与处理日志，验证整个流程是否正常。
        

### 4. 在 GitHub 仓库里配置 Webhook

1. 进入 **Repository → Settings → Webhooks → Add webhook**
    
2. **Payload URL** 填写上一步得到的隧道地址，加上 `/webhook`，比如
    
    ```
    https://abcd1234.ngrok.io/webhook
    ```
    
3. **Content type** 选 `application/json`
    
4. **Secret** 填 `.env` 里的 `WEBHOOK_SECRET`
    
5. 选择 **Let me select individual events**，滚到 “P” 部分，勾选 **Pull requests**
    
6. 点击 **Add webhook**
    
### 5. 验证并测试

1. **创建一个新的分支** 并推到 GitHub：
    
    ```bash
    git checkout -b test-readme-update
    git push -u origin test-readme-update
    ```
    
2. **在仓库界面打开一个 PR**。此时 GitHub 会向你配置的 URL 发送 `pull_request` 事件。
    
3. **观察本地终端**，你会看到类似：
    
    ```
    ✅ README updated and submitted
    ```
    
4. **刷新 GitHub 仓库的 `README.md`**，你会发现多了一行：
    
    ```
    Last PR: 2025-06-21T12:34:56Z
    ```
    
5. 如果你 **在同一个 PR 上再推一个 commit**（触发 synchronize），或者重开 PR，也会再次更新那行时间戳。
    
#### 空提交触发：
    
```bash
git commit --allow-empty -m "trigger webhook"
git push
```  
