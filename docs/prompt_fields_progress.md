# Prompt 数据字段改造进度

| 功能项 | 状态 | 说明 |
| --- | --- | --- |
| 后端/DB：支持 `prompt_data_fields`、`rag_enabled`（schema、Context、Prompt 构建、FormatDataByConfig 开关） | 已完成 | 数据库新增字段并向后兼容；上下文携带字段/开关；按字段生成 User Prompt，支持 Fib/OTE/近期变动的独立开关 |
| 后端 API：创建/更新/查询交易员接口传递字段与 RAG 开关 | 已完成 | create/update 接收字段数组与开关，get 返回解析后的字段数组与开关 |
| 前端：交易员配置弹窗字段多选（中文展示，默认勾选）、RAG 开关 | 已完成 | 弹窗新增字段多选（默认勾选常用字段）、RAG 开关；保存时传递至后端 |
| 文档维护 | 进行中 | 功能完成后更新状态并随每次完成提交 |

