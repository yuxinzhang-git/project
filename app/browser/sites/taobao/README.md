# 淘宝站点适配器

本目录包含淘宝的页面导航、商品列表、排序、筛选和错误处理实现。业务层应通过 `TaobaoAdapter` 调用，不应直接操作 Playwright 或 CSS Selector。

## 已支持功能

### 页面导航

- 打开淘宝首页：`open_home()`
- 搜索商品关键词：`search(keyword)`
- 打开我的淘宝或收藏夹入口：`open_favorites()`
- 返回上一页：`back()`

### 商品页面操作

- 读取当前商品列表：`list_products()`
- 打开第 N 个商品：`open_product(index)`
- 排序商品：`sort_products(mode)`
- 按条件筛选商品：`filter_products(condition)`

当前排序模式主要包括：`sales`（销量）、`price`（价格）和 `default`（综合）。筛选条件会按照当前页面可见的筛选控件执行。

## 自然语言示例

- `打开淘宝`
- `在淘宝搜索机械键盘`
- `读取当前商品列表`
- `打开第三个商品`
- `按销量排序`
- `按价格排序`
- `筛选黑色`
- `返回搜索结果页`

搜索后可以省略站点名称，系统会根据当前 `PageContext` 判断当前站点。

## 组件和文件

- `navigation.py`：淘宝首页、搜索、收藏夹和返回导航
- `components/product_list.py`：商品列表、打开商品、排序和筛选
- `adapter.py`：对外的淘宝站点适配器入口
- `capability.py`：当前站点能力声明
- `errors.py`：淘宝专用错误类型

## 错误处理和安全限制

淘宝可能要求登录，或显示滑块、验证码和风控页面。适配器会区分并返回以下错误：

- `TaobaoLoginRequiredError`：需要登录
- `TaobaoRiskControlError`：遇到验证码、滑块或风控
- `TaobaoPageStructureError`：商品列表或页面控件无法识别
- `TaobaoBrowserError`：浏览器配置或自动化层问题

系统不会尝试绕过登录、验证码、滑块或淘宝风控。

## 当前限制

- 商品选择器依赖淘宝当前页面结构，页面改版后可能需要更新组件。
- 收藏夹需要有效登录状态；无法识别身份时应返回登录错误。
- 实际商品列表、排序和筛选结果取决于网络、登录状态、地区和淘宝风控策略。
