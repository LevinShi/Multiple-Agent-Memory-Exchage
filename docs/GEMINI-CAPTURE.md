# Gemini 选定会话私有采集 · 0.2 preview

状态：私有导入器及Chrome选定会话增量采集已实现，本机短对话实测通过；长历史、不同账号真实切换、复杂回复仍待验证。采集只读取已加载页面文本，不发Gemini聊天请求、不遍历会话列表、不自动翻页。测试期间用户提示Gemini出现拒答，已停止线上测试并暂停；不能据此判断风控，也不承诺平台兼容永不变化。

## 安装（一次）

Python3.10+、macOS/Linux，Google Chrome。当前实际验证macOS；Linux尚待CI/用户验证。

1. 在chrome://extensions开启开发者模式，加载仓库的extension目录。扩展只申请activeTab、scripting和nativeMessaging，不申请全站访问，不读取浏览器Cookie。通过点击扩展才获得当前标签页临时权限。
2. 在代码目录运行（私有库必须在共享记忆库之外）：

```sh
python3 install_capture.py --root "$HOME/local-agent-memory-private" --extension-id jinafgfanhkallojckcmfinmmgoajpmd
```

首次创建的私有库默认暂停；已有不同原生host配置会拒绝覆盖。安装器将独立运行文件放到macOS的`~/Library/Application Support/LocalAgentMemory/runtime`或Linux的`~/.local/share/local-agent-memory/runtime`，并注册Chrome Native Messaging配置。不是常驻服务，没有HTTP端口或云端代理。移动源码目录不会影响已安装运行文件；升级需重新运行安装器并在Chrome重载扩展、刷新测试页面。

## 日常用法

打开自己要保存的Gemini会话，点工具栏扩展→“开始当前会话的自动增量采集”。之后照常聊天，页面角落显示本地落盘确认和已保存消息数。一次仅启用一个会话；选新会话会使旧会话的采集令牌失效。切换页面/账号、刷新页面或重启浏览器后要重新选择，避免后台默认全量采集。

点“暂停全部采集”立即使后续写入被本地端拒绝，不删除原文。重新选择时会读取当时已加载的历史，因此暂停期间的消息只有在你重新选择后才可能补入。默认不自动恢复采集。

会话正文始终标“历史完整性未确认”：网页可能只加载部分历史，插件不会冒充完整备份。附件不下载，图片/视频/Canvas不是当前采集范围。消息正文按当前可见文本提取，代码块作为文本保留，不保证完整Markdown格式。站点改版或缺消息标识/账号标识会停止，不能退化为整页抓取。

你也可以对维护Agent说：
- “暂停 Gemini 私有采集。”
- “看看私有采集保存了多少条、占多大空间。”
- “停止记录这条会话，保留原始记录，不要让它自动恢复。”
- “将这条会话的这段摘要共享到项目X。”（先明确摘要与项目；不会默认共享全量原文。）

## 本地导入与管理接口

```sh
python3 private_capture.py --root "$HOME/local-agent-memory-private" status
python3 private_capture.py --root "$HOME/local-agent-memory-private" pause
python3 private_capture.py --root "$HOME/local-agent-memory-private" delete --key CONVERSATION_KEY
```

`delete`是可恢复停采/隐藏：保留原文，写tombstone，刷新和重新选择均不能复活。确需恢复时执行restore再重新选择；本版没有自动物理清理功能。此删除不会删除Google上的会话或共享摘要。

导入JSON走同一引擎：先select明确URL/account_scope取得session，再用import --file。格式见[导入协议](IMPORT-FORMAT.md)。来源未选择、暂停、令牌过期或身份不匹配时不写入。浏览器桥接没有分享、执行shell、任意文件读取接口。

## 共享摘要是单独动作

`share_summary.py`要求明确选定私有会话、目标项目、摘要文件，并带`--confirm-share`；首先验证现有gateway run，再只将该摘要通过gateway save写入。无确认、项目无授权、来源被停采删除时拒绝。原始全文不会自动复制。例：

```sh
python3 share_summary.py --private-root "$HOME/local-agent-memory-private" \
  --key CONVERSATION_KEY --gateway /absolute/path/to/shared-vault/gateway.py \
  --actor codex --project PROJECT --run RUN_ID --task gemini-summary \
  --summary-file /absolute/path/to/approved-summary.txt --confirm-share
```

RUN_ID来自现有gateway begin；用户选定内容与项目后维护Agent执行上述命令。该确认参数记录操作意图，并不能认证用户身份；仍遵守合作型Agent工作流边界。共享不等于外发，现有export权限不会改变。

## 保存与磁盘

原文独立存于私有state.json，目录0700、正文文件0600；同一系统用户的进程仍能读取，不是强隔离。账号只保存SHA256标识，不保存邮箱明文；这是可关联标识，不是匿名化或加密。

相同消息内容按hash只存一份；版本只记引用。同一会话重复采集不新增版本。上限50MiB（control.json可调低），每会话5000个不同快照、每次输入2MiB、单消息64KiB；到上限停止/暂停，不自动删除。内存JSON适合个人试点，不承诺大库性能。读状态可见容量；配置缺失/损坏时拒绝写入。

技术依据：Chrome官方[Native Messaging](https://developer.chrome.com/docs/extensions/develop/concepts/native-messaging)与[activeTab](https://developer.chrome.com/docs/extensions/develop/concepts/activeTab)。本实现独立编写，没有复制ChatMemo未公开源码。
