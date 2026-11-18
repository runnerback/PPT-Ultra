# Release 发布手册

适用 PPT Ultra 1.2.2 起。推送版本 tag 后，GitHub Actions 在 GitHub 提供的 Ubuntu runner 上安装锁定依赖、验证、打包和发布；不使用你的本地 Ubuntu。

## 0. 发布前

1. 同步 `skills/ppt-ultra/SKILL.md`、`.claude-plugin/marketplace.json`、中英文 README 的版本号。
2. 在 `skills/ppt-ultra/NOTICE.md` 写修改记录，准备 `docs/releases/<版本>.md`（第一行是 Release 标题）。
3. 运行安全回归、引擎冒烟和上传包验证。完整命令及本次分支合并步骤见 [企业审核整改与合并教程](ENTERPRISE_REVIEW.md)。
4. 提交代码、合并到 main 后再打 tag。tag 必须指向包含本版代码及发布说明的提交。

## 1. 推 tag 自动发布（推荐）

以下由维护者执行；本次示例版本是 `1.2.2`，不要覆盖已发布的 `1.2.1`。

```bash
git switch main
git pull --ff-only origin main
# 确认整改分支已合入，且本地验证通过
git push origin main
git tag -a 1.2.2 -m "PPT Ultra 1.2.2: security review hardening"
git push origin 1.2.2
```

到 GitHub 仓库的 **Actions → release** 查看执行结果。成功后 **Releases → 1.2.2** 会出现附件。自动和手动触发都会检出指定 tag 的提交，避免用 main 的新代码覆盖旧版本产物。

网络等瞬时故障可在 Actions 重跑相同 tag；代码修复需要新提交和新版本 tag。手动 **Run workflow** 的 tag 输入必须已存在。

## 1a. 打附件（手动）

在指定 tag 的干净提交上运行，依赖需先装好：

```bash
bash tools/package-release.sh 1.2.2
```

脚本拒绝版本不一致、tag 不指向 HEAD、已跟踪文件未提交的状态。完整目录包使用受控文件清单，不会收进本地 `.env`、`.npmrc`、node_modules、缓存或输出。`dist/` 不进 Git。

| 附件 | 用途 |
|---|---|
| `ppt-ultra-1.2.2-upload.zip` | 公司技能上传入口；根目录直接有 SKILL.md，外层不超过 500 文件 / 100,000,000 字节 |
| `ppt-ultra-1.2.2.zip` | 完整目录安装，所有实现和素材直接可见 |
| `ppt-ultra-1.2.2-source-*.zip` | 独立可读的源码、配置、锁文件、文档和许可分卷；提供给审核者，不是安装包 |
| `ppt-ultra-1.2.2-source-manifest.json` | 源码分卷及文件 SHA-256、仓库地址、源提交、是否有未提交修改 |
| `SHA256SUMS` | 上述所有附件的 SHA-256 |

GitHub 自动提供的两个 **Source code** 附件是整个仓库快照，和技能安装包用途不同。

## 1b. 有文件数量限制的平台上传包

不需要 tag，也不用提交即可预览本地修改：

```bash
python3 tools/package-upload.py --output dist/ppt-ultra-upload.zip --audit-dir dist/review
python3 tools/test_upload_package.py --zip dist/ppt-ultra-upload.zip --smoke
```

1.2.2 保留全部引擎、模板、图标、字体与音效。完整运行时改放入多个独立 `runtime-*.tar.gz`；默认每卷及可见单文件最多 8,000,000 字节，也限制分卷的未压缩大小。源码审阅卷另外限制每卷最多 350 文件，解开一层 ZIP 即是实际代码，不含嵌套载荷。需要更低上限时传 `--max-part-bytes`，遇到单个源码文件超过上限会明确失败，不会截断源码。

`runtime-manifest.json` 为每个文件记录 SHA-256、大小、权限和所属卷。初始化先校验所有归档，再逐文件验证后原子恢复；损坏、缺卷、错卷、软链接和路径穿越均拒绝。外层 SKILL.md 与恢复后入口包含相同 P1–P4 安全边界。启动不联网，不安装依赖。

清单以 Git 跟踪文件为主，额外显式接纳本次新增的锁文件和整包许可证；其他新资源应由维护者审阅并加入 Git 后再打包。未提交试包的清单会标为 `dirty: true`，正式 tag 产物应为 false。

平台必须支持 Python、可写缓存和压缩资源。若审核器递归计数或采用更低单文件上限，仍需按平台规则调整；8 MB 是工程默认值，不能据此保证过审。源码审阅卷可作为辅助审核附件；若表单只接受一个技能包，请将 Release 中的源码清单和链接提供给审核者。

## 2. 手动发布备用

优先使用 Actions，避免遗漏校验。确需手动时，先用 `package-release.sh` 生成本版全部附件，再到 GitHub **Draft a new release** 选择已推送 tag，按 `docs/releases/1.2.2.md` 填标题和正文，附上上表文件。不要把仅供审阅的源码分卷当作技能安装包。
