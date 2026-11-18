# 企业审核整改与分支合并教程

本次整改分支：`fix/enterprise-skill-review`；准备发布版本：`1.2.2`。通用安全修复经验证后合回 main；企业网关、凭据和浏览器由宿主配置，不在公开仓库固化内部地址或密钥。不需要长期维护一套企业专用引擎分叉。

## 审核项与实现

| 项目 | 修改 |
|---|---|
| Python 版本与哈希 | 19 项直接依赖及传递依赖精确锁在 requirements.lock；requirements.txt 强制 require-hashes / only-binary；Python 版本差异用环境标记选择固定版本 |
| npm 版本与锁文件 | 10 项直接依赖与现有 lock 精确对齐，传递依赖保留 integrity；启动器用 npm ci --ignore-scripts，避免生命周期脚本自动执行 |
| 安装来源与浏览器 | 默认官方 npm registry；移除 npmmirror 及自动浏览器下载；可通过 PPT_ULTRA_NPM_REGISTRY 配置管理员批准的 HTTPS 企业源 |
| P1–P4 | 两层 SKILL.md 一致声明素材/指令隔离、PPT 用途边界、注入识别及继续原任务、敏感数据不写日志或外发 |
| 日志 | Python 自动审计仅记时间、工具名、参数/输出数量，不复制参数值或输出正文；Themed 错误遥测仅记分类，省略错误正文 |
| 推广 | 赞助文件改为中性来源说明，移除返利和模型中转推广，保留上游署名与文件兼容性 |
| 许可证 | 整包声明 AGPL-3.0 并保留 MIT 组件许可，新增 LICENSE-AGPL-3.0；两个完整性入口继续校验许可与署名 |
| 可审计性与质量 | 原有引擎及素材全部保留；大载荷拆成小归档，额外生成明文源码审阅分卷、Git 来源和 SHA-256 清单 |

这是对已报告审核项的修复，不是企业平台通过证明。安全声明还需要宿主的网络白名单、统一网关、日志与凭据管理配合。没有全局代码级 DLP 沙箱；提供方调用只应接收经过脱敏的必要内容。已有本地日志不会被自动清除。

## 宿主安装

推荐 Python 3.12；锁文件按 Python >=3.10 解析并保留版本条件，但本次本地执行验证为 macOS / Python 3.12 / Node 22。Linux / Python 3.12 / Node 20 在 tag Actions 执行；Windows 启动器未在本地执行验证。

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install --require-hashes --only-binary=:all: --index-url https://pypi.org/simple -r skills/ppt-ultra/requirements.txt
npm ci --prefix skills/ppt-ultra/engines/html-themed/project --ignore-scripts --no-audit --no-fund --registry=https://registry.npmjs.org
```

企业不允许公网安装时，将源替换为批准的内部源，仍须保留哈希检查，镜像提供的包必须和锁定哈希一致；不要临时加 `--extra-index-url` 或去掉校验。Windows Python 路径为 `.venv\Scripts\python.exe`。

浏览器相关检查需要管理员预置 Chrome/Chromium，并在宿主中设置 `CHROME_PATH` 为实际可执行文件路径，或预置与锁定 Playwright 兼容的浏览器缓存。浏览器二进制的来源、版本与哈希校验由宿主镜像构建/软件分发流程完成，技能不下载它。可选 Python Playwright、语音对齐等插件也由宿主批准并固定版本后预装；没有自动补装的豁免。

## 你来提交与合并

先确认当前分支和差异。下面命令不会由助手代为执行。

```bash
git switch fix/enterprise-skill-review
git status --short
git diff --stat
git diff --check
# 安全及恢复测试不需要第三方 Python 包
python3 tools/test_security.py
python3 tools/test_upload_package.py
# 使用安装过锁定依赖的 Python
PYTHON=.venv/bin/python bash tools/smoke.sh
.venv/bin/python tools/package-upload.py --output dist/ppt-ultra-upload.zip --audit-dir dist/review
.venv/bin/python tools/test_upload_package.py --zip dist/ppt-ultra-upload.zip --smoke
```

确认变更列表只有本次整改后提交。`git add -A` 会加入所有未忽略变更，所以有其他修改时请改成逐文件添加。不要提交 dist、output、凭据或本地环境文件。

```bash
git add -A
git diff --cached --stat
git commit -m "fix: harden skill distribution for enterprise review"
# 可选：先备份整改分支到远端，也可用它创建 PR
git push -u origin fix/enterprise-skill-review

git switch main
git pull --ff-only origin main
git merge --no-ff fix/enterprise-skill-review -m "merge: enterprise skill security hardening"
```

若发生冲突，先运行 `git status` 定位，编辑冲突文件并检查最终内容，然后 `git add <已解决的文件>`、`git commit`。未解决前不要打 tag；需要撤销本次未完成合并可用 `git merge --abort`。若远端要求 PR 合并，请通过 GitHub 合并 PR，再 `git switch main && git pull --ff-only origin main`，跳过本地 merge/push main。

合并后重跑安全回归与冒烟。确定通过后推 main、创建新 tag：

```bash
python3 tools/test_security.py
PYTHON=.venv/bin/python bash tools/smoke.sh
git push origin main
git tag -a 1.2.2 -m "PPT Ultra 1.2.2: security review hardening"
git push origin 1.2.2
```

最后到 Actions 查看 release 成功，再下载 `ppt-ultra-1.2.2-upload.zip` 提交公司审核。将同版 `source-*.zip`、source-manifest.json、SHA256SUMS 或 Release 链接提供给审核者。公开 GitHub Release 不应带企业材料、Cookie、内部端点或审核报告原文。

## 本次本地验证结果

- 8 项安全回归、10 项初始化/归档恢复测试通过；原始及外层 SKILL.md 格式校验通过。
- 官方源哈希锁安装成功，19 项直接 Python 包导入通过；PDF / DOCX / XLSX 转 Markdown 的本地样本通过。
- SVG 质量门禁后生成原生可编辑 PPTX，通过文本形状检查；5 个 Spec 示例、宿主契约、页码和 Editorial 同步检查通过。
- npm ci（禁用生命周期脚本）成功，Themed 3 页 HTML 渲染通过。
- 上传包 289 文件，51,269,267 字节；恢复 13,377 文件，逐字节与当前源目录一致；恢复后再次跑引擎冒烟通过。
- 18 个运行时卷，最大 7,518,553 字节；7 个明文源码卷覆盖 713 个文件，源码覆盖、哈希与体积验证通过。
- 未执行 Windows、LibreOffice、外部图片/TTS/模型服务端到端测试。企业审核尚未重新提交；Linux 发布验证将在推 tag 后执行。

本地包及审阅清单标为 `dirty: true`，记录其尚未提交；正式发布会从 tag 的干净提交重新构建。数字为本次试包测量值，后续内容变更以打包输出为准。

## 日后更新依赖

只有维护者审阅并测试后才更新锁文件；运行时不自动追新。Python 直接固定版本的维护输入为 `tools/python-requirements.in`：

```bash
uv pip compile tools/python-requirements.in --python-version 3.10 --universal --generate-hashes --no-build --default-index https://pypi.org/simple -o skills/ppt-ultra/requirements.lock
```

npm 更新 package.json 时同时更新 package-lock.json，再用 npm ci 复现安装。更新后重复安全回归、引擎冒烟、上传包逐文件验证。哈希保证下载与已审阅锁一致，不代表上游包本身没有漏洞。
