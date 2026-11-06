# Multiple-Agent-Memory-Exchage

Local Agent Memory

让多个本地 AI 编程工具接续同一项目：先按项目授权读取上下文，完成工作后保存少量进展。Markdown 留记录，Python 管入口，Git 可用于你自己的版本管理。

**v0.2.1-preview：面向愿意试用、反馈的 AI 爱好者。** 核心闭环是“授权→读取→工作→保存→换工具回读”。不是聊天记录全量同步，也不是抵御恶意 Agent 的安全沙箱。

## 你能得到什么

- 项目级 read/write/export 独立授权；默认不共享，独占项目只授权一个 actor。
- 一条入口返回规则与近期有效记录，不要求每轮手动提醒查存。
- 追加式记录、来源和 supersedes 修订关系，保留原记录。
- 本地状态页和运行证据，区分“已写入”和“另一端已读取”。
- 仅 Python 标准库，无账号、数据库、常驻服务或项目自建网络请求。

## 5 分钟试跑

环境：Python 3.10+，macOS 或 Linux（使用 fcntl 文件锁，不支持原生 Windows）。下面所有命令在下载并解压的代码目录执行。

```sh
python3 -m unittest discover -v
python3 demo.py
python3 demo_capture.py  # 完全离线，不安装扩展、不访问 Gemini
```

演示在临时目录创建无敏感示例，模拟 Codex 写入、Cursor 接续、Codex 回读，并检查未授权拒绝和导出关闭。它验证 CLI，不会启动任何 AI 客户端；结束自动清理临时目录。

创建自己的库：

```sh
python3 init_vault.py "$HOME/local-agent-memory-vault"
```

新库没有任何授权，现有目录会被拒绝覆盖。若只想试合成项目，可换一个新目录：

```sh
python3 init_vault.py "$HOME/local-agent-memory-demo" --demo
```

`--demo`仅为名为demo的示例项目授权codex/cursor/zcode/minimax读写，export不开放。不要将这份示例授权直接视为真实项目授权。

## 接入工具后，只用自然语言

初始化会生成 `ENTRY-codex.md`、`ENTRY-cursor.md`、`ENTRY-zcode.md`、`ENTRY-minimax.md`，其中路径已按你的电脑生成。将对应内容加入各客户端的默认规则，保留原有规则；重开会话验证规则被加载。详见 [客户端接入与使用验收](docs/CLIENTS.md)。

示例两轮任务：

1. 在 Codex 说：“在 demo 项目里做一个读书清单小工具，先确定三个必要功能。”
2. 换到 Cursor 或 MiniMax Code 说：“继续 demo 项目的读书清单，基于已有决定给出页面草图方案。”

验收时看工具轨迹：首个主库操作应为 `gateway.py begin`，结束自动 `save`；回到第一端能读到新的结果。仅回复“记住了”不算成功。模型可能不执行规则，首次必须检查。共享的是工作进展，不是模型隐式记忆。

## 真实项目授权

只有库的维护者根据用户决定编辑库内permissions.json。示例结构见 [权限说明](docs/PERMISSIONS.md)。新增项目默认拒绝；撤销权限后下一次入口操作重新校验。不要把维护者的个人权限清单上传到公开仓库。

```sh
python3 "$HOME/local-agent-memory-vault/gateway.py" begin --actor codex --project my-project
```

命令返回run_id。后续search/show/save/evidence均带`--run RUN_ID --actor codex --project my-project`；save用stdin传正文，并提供`--task TASK --status active --source SOURCE`。项目和任务ID仅支持1–80位英文、数字、下划线或连字符。正文支持中文，最多65536 UTF-8字节。保存更正时同一项目/任务使用`--supersedes RECORD_ID`。

运行库中的`python3 dashboard.py`可重建dashboard.html，用浏览器本地打开。gateway操作也会更新页面；页面需刷新，仅显示元数据。普通Agent不能将状态页作为跨项目读取入口。

## 已验证与尚未完成

|范围|状态|
|---|---|
|独立初始化、CLI双actor接力、权限拒绝、修订、并发写|本机自动化测试通过；见[验收记录](docs/VALIDATION.md)|
|真实自然语言接力|维护者环境曾观察Codex→MiniMax Code→Codex成功；不等于所有安装/模型都通过|
|Cursor、ZCode|提供入口模板；此发布包未在这些客户端重新做独立安装验收|
|Linux / 多Python版本|由GitHub Actions验证；以Release关联提交的CI结果为准|
|Gemini选定网页会话采集|已实现私有导入+本地原生通道，macOS短会话实测；见[使用说明](docs/GEMINI-CAPTURE.md)|
|ChatGPT采集、Gemini原生客户端直接采集|当前没有|
|语义检索、更多Agent、云同步|当前没有；更好检索与更多Agent保留为路线图|

[安全边界](SECURITY.md) · [路线图](docs/ROADMAP.md) · [贡献说明](CONTRIBUTING.md) · [MIT许可](LICENSE)

## Gemini 私有采集

新增独立私有导入器和Chrome选定会话自动增量采集；默认暂停，显式选择后启用，原文不会自动共享。安装与自然语言使用方式见[采集说明](docs/GEMINI-CAPTURE.md)。0.1核心预览包仍保留；0.2采集能力不代表全历史或所有账号已验收。

本版交付与剩余关口见 [发布清单](docs/RELEASE.md)。建议先离线试用；Gemini 在线验收保持暂停。
