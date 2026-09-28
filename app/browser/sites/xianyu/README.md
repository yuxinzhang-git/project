# 咸鱼网站适配器

## 已支持功能

- 打开咸鱼首页、按关键词打开搜索结果、返回上一页。
- 读取当前搜索结果中的商品列表，按序号打开第 N 个商品。
- 在当前搜索页点击“下一页”和“上一页”（页面真实提供控件时）。
- 从公开商品卡片读取标题、价格、成色和链接，并生成保守的价格区间估算。
- `PageContext` 识别 `home`、`search`、`item_detail`、`unknown`。
- Intent 仅使用 `navigation` 与 `page_action` 两类。

## 自然语言示例

```json
{"category":"navigation","target":"search","action":"open","site":"xianyu","keyword":"二手相机"}
{"category":"page_action","target":"item","action":"list","site":"xianyu"}
{"category":"page_action","target":"item","action":"open","site":"xianyu","index":3}
{"category":"page_action","target":"pagination","action":"next","site":"xianyu"}
```

也支持“打开咸鱼首页”“搜索咸鱼 二手相机”“读取商品列表”“打开第 1 个商品”“下一页”等命令。

## 登录和风控限制

不会绕过登录、滑块、验证码、安全验证或风控页面。登录问题抛出 `XianyuLoginRequiredError`，验证码或风控抛出 `XianyuRiskControlError`，选择器不匹配抛出 `XianyuPageStructureError`，Browser/Playwright/网络问题保留为浏览器层错误。

本适配器只读浏览和结果页操作，刻意不实现私信、聊天、下单、付款、发布、收藏、点赞或其他可能产生用户或交易副作用的操作。

## 尚未实现的功能

- 排序、筛选、滚动加载更多：暂未声明能力，待真实页面确认稳定控件和行为后实现。
- 估价结果只是当前公开样本的统计，不代表成交承诺；图片、成色、配件和交易风险仍需人工核验。
- 私信、聊天、购买、支付、发布商品及账户管理。
