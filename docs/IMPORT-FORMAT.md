# 私有导入协议 v1

操作前初始化独立目录：`python3 private_capture.py --root PRIVATE_DIR init`。维护者在明确用户选择来源后执行`select --url URL --account-scope SHA256_ACCOUNT`，返回session和key。account_scope是本地账号别名或已确认账号标识的SHA256；网页适配器使用当前账号邮箱的SHA256，身份无法确认则拒绝。

`import --file FILE.json`样例（用select返回的session替换占位符）：

```json
{
  "url": "https://gemini.google.com/app/synthetic",
  "account_scope": "64位小写sha256",
  "session": "select返回的临时令牌",
  "seq": 1,
  "streaming": false,
  "complete": false,
  "messages": [
    {"id": "turn01:user", "role": "user", "text": "示例提问"},
    {"id": "turn01:assistant", "role": "assistant", "text": "示例回答"}
  ]
}
```

令牌绑定账号、会话、精确URL，12小时有效；序号单调增长，乱序请求拒绝。暂停撤销所有令牌。重新select会替换旧令牌且恢复当前选择，不能作为自动重试步骤。原生桥接select/check/capture/pause/status使用同一协议。

消息ID必须是可信来源中的稳定轮次/消息ID，不能仅凭内容或标题猜测。网页目前用conversation-container的id加角色。局部抓取合并已知消息，不因页面缺失而删旧内容。新ID按已知相邻顺序插入，顺序冲突拒绝。每个版本记录可见片段引用，不能把合并结果误标为完整历史。

complete默认false；只有来源证明完整时才设true，保留last_complete独立引用。网页适配器不会自动设true。流式未完成、空内容、来源不匹配、暂停/删除、容量超限均不更新正文。

CLI是本地主人操作入口，不代表授予其他Agent私有资料权限；已有共享授权不自动包含私有原文。
