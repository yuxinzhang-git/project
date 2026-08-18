# Bilibili 站点适配器

本目录包含 Bilibili 的导航、页面操作、页面对象和通用组件实现。业务层应通过 `BilibiliAdapter` 调用，不应直接操作 Playwright 或 CSS Selector。

## 已支持功能

### 页面导航

- 打开 Bilibili 首页：`open_home()`
- 搜索关键词：`search(keyword)`
- 打开 UP 主或频道：`open_channel(channel_id)`
- 打开用户收藏夹：`open_favorites(user_id)`
- 返回上一页：`back()`
- 打开历史记录：`open_history()`

### 视频列表操作

- 读取当前页面的视频列表：`list_results()` 或 `actions.list_videos()`
- 打开第 N 个视频：`open_result(index)`
- 播放第 N 个视频：`play_result(index)`
- 暂停当前视频：`pause_current()`
- 继续播放当前视频：`play_current()`
- 搜索结果下一页：`next_page()`
- 搜索结果上一页：`previous_page()`
- 跳转到指定搜索页：`goto_page(page)`

### 视频互动

- 点赞当前视频：`like()`
- 取消点赞：`unlike()`
- 投 1 个或 2 个币：`coin(1)`、`coin(2)`
- 收藏当前视频：`favorite()`
- 取消收藏：`unfavorite()`
- 打开当前视频：`open_current()`
- 播放上一个或下一个视频：`play_relative(-1)` 或 `play_relative(1)`

视频序号按照当前页面中普通视频卡片的顺序计算，广告卡片不会占用序号。页面排序变化后，以当次读取到的页面顺序为准。

## 自然语言示例

以下指令由规则解析器转换为结构化计划：

- `打开哔哩哔哩`
- `在 B 站搜索 Python 教程`
- `打开第三个视频`
- `播放第三个视频`
- `播放下一个视频`
- `播放上一个视频`
- `打开当前视频`
- `继续播放`
- `恢复播放`
- `下一页`
- `上一页`
- `跳转到第 3 页`
- `点赞`
- `取消点赞`
- `投 1 个币`、`投 2 个币`
- `收藏`
- `取消收藏`
- `打开历史记录`
- `打开收藏夹`
- `返回搜索结果页`

搜索后可以省略站点名称，系统会根据当前 `PageContext` 判断当前站点。

## 组件和文件

- `navigation.py`：页面导航
- `actions.py`：视频列表和播放器操作
- `pages/`：首页、搜索页、视频页、频道页和收藏夹页面对象
- `components/`：Bilibili 视频列表和播放器组件
- `capability.py`：当前站点能力声明
- `adapter.py`：对外的站点适配器入口

## 当前限制

- 播放器暂停已接入自然语言 Intent，可以在当前视频页输入 `暂停` 或 `pause`。
- 播放按钮选择器依赖 Bilibili 当前页面结构，页面改版后可能需要更新组件选择器。
- 收藏夹需要提供用户 ID，并且可能需要登录。
- 遇到登录、验证码或站点风控时不会绕过验证。
