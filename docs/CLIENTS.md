# 客户端接入与验收

初始化后使用库内生成的ENTRY文件，里面是本机绝对路径。不要照抄作者电脑路径。客户端需要允许执行本地Python命令；无需自动批准所有命令。

|工具|actor|规则放置位置（按当前版本UI核对）|
|---|---|---|
|Codex|codex|用户或项目AGENTS.md，追加对应ENTRY内容|
|Cursor|cursor|Settings/Customize中的User Rules，追加对应ENTRY内容|
|ZCode|zcode|用户AGENTS.md或该版本支持的项目默认指令入口|
|MiniMax Code|minimax|用户记忆/默认规则入口；维护者安装使用~/.minimax/memory/user.md，不是其他MiniMax产品|

本包不改写现有全局配置，不假定路径对所有版本都成立。如果客户端不加载该规则，将ENTRY加入它支持的项目规则，然后新建会话重测。普通网页ChatGPT不能直接执行本机脚本，不在这份自动接入名单内。

验收顺序：

1. 用demo授权，第一端自然语言完成一个小任务，不额外提醒查存。
2. 展开工具轨迹确认第一个涉及主库的动作是begin，不是先ls/rg/read。
3. 确认save结果含id；未授权export时handoff_skipped是预期。
4. 第二端只说“继续demo项目的上一项工作”，观察begin是否返回上一端记录并据此推进、save。
5. 第一端回读确认内容。不要仅依赖第二端“已完成”的自述。
6. 对unknown项目请求begin应非零退出、stdout无正文。不直接读文件验证绕过能力。
7. evidence返回not_assessed是设计行为；维护者将实际工具轨迹、入口日志与回读对照，判定此条路线。

失败报告应包含版本、操作系统、最小合成任务、错误类型与脱敏工具命令。不上传个人records、完整聊天或凭据。
