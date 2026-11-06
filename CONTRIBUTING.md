# 贡献与反馈

先运行 `python3 -m unittest discover -v` 和 `python3 demo.py`。测试只使用临时合成资料。

提交PR请说明问题、行为变化和验证；权限相关改动必须包含拒绝路径测试。不要提交真实permissions.json、records、handoffs、runs、activity或生成的dashboard。

试用反馈格式：操作系统/Python版本；客户端与版本；规则放置位置；合成自然语言任务；预期与实际结果；首个主库命令；save是否成功；另一端是否回读。分清CLI测试和真实客户端行为。
