# 公开仓库隐私检查与发布说明

检查日期：2026-11-18。工作分支：`fix/public-data-sanitization`，准备版本：`1.2.3`。本报告不记录敏感原值或组织专有关键词。

## 结论与修复

本次范围内未检出有效 API Key、Token、Cookie 或私钥，未匹配用户指定组织的名称、域名或账户标识。发现并修改了可选个人联系邮箱、非必要的工作背景描述，以及主题示例中可能被误认为真实收件地址的域名。

- `.claude-plugin/marketplace.json`、两份 README、NOTICE：删除可选个人联系邮箱，保留作者名和开源归属。
- README、NOTICE、Spec Native README：将作者工作背景描述改为通用的公开功能说明。
- Themed theme10/theme11：示例联系域名改为 `.example`；对应元数据、合并元数据、预构建 JavaScript 同步修改，未删除版式或素材。
- `.gitignore`：补充私有环境文件、Cookie 文件、证书容器及本地配置忽略规则。已被 Git 跟踪的文件不会因 ignore 自动消失，另由检查器拦截。
- `tools/privacy-check.py`：检查跟踪文件和未忽略的新文件中的非示例联系邮箱、私人用户目录、私网端点、私钥、电话和凭据容器；可选组织匹配规则只放本地忽略文件。
- `.github/workflows/privacy.yml`：分支推送和 PR 执行隐私检查及 Gitleaks；扫描器版本和 SHA-256 固定。报告不输出秘密原值。
- 当前仓库的 Git 提交邮箱已改为从 GitHub 公开账户信息确定的 noreply 地址；全局 Git 配置不变，历史作者信息不变。

## 覆盖范围与证据

| 范围 | 方法与结果 |
|---|---|
| 当前已跟踪文件 | 初始 13,400 个文件；文本、路径、联系地址、端点和凭据模式检查；脱敏后的工作树 Gitleaks 无告警 |
| Git 历史 | 19 个可达提交，13,420 个唯一历史 blob；Gitleaks 默认规则产生两条告警，均为 PowerPoint 动画枚举而非密钥；精确豁免后无告警 |
| 发布源码 | 完整下载 1.2.2 的 7 个源码 ZIP 及来源清单，核验 GitHub 提供的 SHA-256；递归扫描代码卷无凭据告警 |
| Release 安装包 | 对 1.2.0、1.2.1、1.2.2 的 3 个完整 ZIP 和 2 个上传 ZIP，远程读取完整目录与入口/清单；完整包的文件集合、大小、CRC32 与对应 tag 一致；上传包逐文件 SHA-256 清单与 tag 内容一致，外层路径未发现额外私有文件；本地 1.2.0 完整包与公开附件 SHA-256 完全相同，并作递归凭据扫描 |
| 图片 | 检查 102 个 PNG/WebP 的元数据，并查看缩略图；8 个含 EXIF 的文件只有尺寸、方向、色彩/分辨率等信息，未见 GPS、作者、设备序列号等字段；视觉内容为样式示例、插图及品牌模板 |
| GitHub 状态 | 仓库公开；检查时没有 fork，公开 issues 数为 0；1.2.2 Release 工作流成功；main 仍指向 1.2.1 的提交 |

1.2.1/1.2.2 大安装包的远程核对使用 ZIP 目录的 CRC32/大小及逐文件清单，不等同于完整下载每个载荷并重新计算其 SHA-256；源码审阅卷及本地完全同哈希的 1.2.0 安装包已完整扫描。未审计 GitHub Actions 完整日志、私有配置、他人克隆/缓存及音频语义，未对图片做逐像素 OCR。这是有边界的泄露检查，不是“绝无敏感信息”的证明，也不能仅靠字符串扫描判断代码知识产权或业务保密属性。

本地详细扫描材料在被忽略的 `output/privacy-audit/`，不要把它们加入公开仓库。

## 脱敏版验证

5 项隐私规则测试、8 项安全回归、10 项归档初始化测试及原有引擎冒烟通过；主题风格元数据一致。使用合成假 Token 确认密钥规则仍会报警。1.2.3 上传包为 289 文件、51,269,856 字节，13,377 个运行时文件恢复后与当前源目录逐字节一致；7 个源码卷覆盖 713 个文件。新上传包（包括嵌套运行时卷）凭据扫描无告警。

## 你来提交、合并和发布

注意：推送 `main` 和 tag 并不会把当前分支自动合入 main。本次分支建立在 1.2.2 的整改提交上，合并它会同时带入安全整改与脱敏修改。

```bash
git switch fix/public-data-sanitization
git status --short
git diff --check
python3 tools/privacy-check.py
python3 tools/test_privacy.py
python3 tools/test_security.py
# 审阅列表后添加本次修改；确认没有其他工作夹带其中
git add -A
git diff --cached --stat
git commit -m "fix: sanitize public examples and add privacy checks"
git push -u origin fix/public-data-sanitization

git switch main
git pull --ff-only origin main
git merge --no-ff fix/public-data-sanitization -m "merge: public distribution privacy hardening"
python3 tools/privacy-check.py
python3 tools/test_security.py
# 使用已装锁定依赖的解释器复测，见 ENTERPRISE_REVIEW.md
git push origin main
git tag -a 1.2.3 -m "PPT Ultra 1.2.3: public privacy hardening"
git push origin 1.2.3
```

有分支保护时，通过 PR 合并后再拉取 main 并打 tag。不要覆盖 1.2.2 tag。查看 Actions 的 privacy / release，通过后使用 1.2.3 附件。

## 历史暴露仍然存在

这次没有改写 Git 历史、删除 Release 或推送任何远端变更。个人邮箱仍存在于旧提交的作者/提交者元数据、历史文件和旧 Release 中；之前的背景描述也仍可在历史版本找到。普通 merge 和新的 noreply 邮箱设置都不会追溯清除它们。

若需要把这类历史个人信息也移除，应单独安排一次历史迁移，而不是继续堆脱敏提交：

1. 冻结推送，保留受控的私有备份，在独立 mirror 克隆中用 `git-filter-repo` 重写作者/提交者邮箱和相关文件内容；保持合法上游署名。
2. 在该克隆中复跑所有分支/tag 的扫描并审阅变更清单。所有后续提交哈希及受影响 tag 都会变化，签名、PR 引用和 Actions 链接可能受影响。
3. 确认迁移范围后，由维护者协调强制推送重写后的分支/tag；协作者重新克隆，避免旧历史被再次合入。
4. 检查并删除或替换仍含旧信息的 Release 正文/附件、Actions 日志/产物；必要时按 GitHub 支持流程处理缓存引用。仅删除旧 Release 附件不会删除 tag 历史，设置 private 也无法收回已有副本。
5. 若未来发现有效凭据，先撤销/轮换，再清理历史；不要只修改文件。

依据：[GitHub 移除敏感数据说明](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository)。本次没有发现需要立即轮换的已提交凭据，因此未擅自进行有协作影响的历史重写。

## 日后检查

```bash
python3 tools/privacy-check.py
python3 tools/test_privacy.py
gitleaks git . --config .gitleaks.toml --log-opts="--all" --redact=100 --no-banner
```

组织域名、项目代号、员工标识等私有规则请写入被忽略的 `.privacy-local-patterns`（一行一个正则），执行 `python3 tools/privacy-check.py --patterns-file .privacy-local-patterns`。不要把这些模式或命中原文写进公开 CI 配置、issue 或 PR 描述。
