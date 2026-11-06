# 项目权限

新建库的permissions.json默认projects为空。维护者明确授权后才能使用；普通Agent不自动修改。

以下是两个虚构项目的示例，不是运行时默认权限：

```json
{
  "version": 1,
  "default": "deny",
  "projects": {
    "demo-shared": {
      "status": "approved",
      "approval_source": "Owner explicitly approved this demo",
      "access_mode": "shared",
      "grants": {"codex": ["read", "write"], "cursor": ["read", "write"]}
    },
    "demo-exclusive": {
      "status": "approved",
      "approval_source": "Owner explicitly approved this demo",
      "access_mode": "exclusive",
      "grants": {"zcode": ["read", "write"]}
    }
  }
}
```

不共享意味着仅原属Agent获准读写，其他actor不获授权；不是把原属Agent也关闭。access_mode是描述，实际执行以grants为准。删除某actor授权即可撤销其后续入口访问；撤销不删除记录，也无法收回已经复制的内容。

export独立，默认省略。显式授权export后，保存可能生成本地handoffs快照；不联网发送。工作入口暂不提供导出命令；维护者确需导出可用memory.py管理命令，并同时具备read+export。公开分享代码不需要导出个人项目数据。

库目录应与代码仓库分离；个人库不要推到本项目的GitHub远端。代码发布包仅包含通用代码、规则、合成测试和文档。
