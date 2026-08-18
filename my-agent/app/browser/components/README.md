# 通用浏览器组件

本目录定义跨网站复用的语义组件接口。组件表达用户要做的事情，网站的 CSS Selector、按钮文本和页面结构放在对应站点目录中。

## VideoList

文件：`video_list.py`

- `list(limit)`：读取视频列表
- `open(index)`：打开第 N 个视频
- `play(index)`：打开并播放第 N 个视频

## Player

文件：`player.py`

- `play()`：播放或继续播放当前视频
- `pause()`：暂停当前视频

Bilibili 支持通过 `继续播放`、`恢复播放` 或 `resume` 触发当前播放器的 `play()`。

## SearchBox

文件：`search_box.py`

- `search(keyword)`：搜索关键词

当前 Bilibili 和淘宝主要通过站点导航组件实现搜索。未来可以在站点组件中实现输入搜索框并提交的流程。

## Pagination

文件：`pagination.py`

- `next()`：下一页
- `previous()`：上一页
- `goto(page)`：跳转到指定页

Bilibili 的搜索页由 `BilibiliPagination` 实现，负责处理 Bilibili 的分页按钮和 URL。

## ContentActions

文件：`content_actions.py`

- `like()` / `unlike()`：点赞和取消点赞
- `favorite()` / `unfavorite()`：收藏和取消收藏
- `coin(count)`：投币

Bilibili 当前支持投 1 个或 2 个币。组件会自动完成站点弹窗中的提交，不额外向用户发起确认；余额不足、未登录或风控时返回真实错误。

## ContentCollection

文件：`content_collection.py`

- `list(limit)`：读取历史记录、收藏夹或播放列表
- `open(index)`：打开集合中的第 N 项

Bilibili 使用该接口承载历史记录和收藏夹中的视频列表。

## 分层关系

```text
业务服务
  -> 站点 Adapter
    -> 站点 Page Object / Component
      -> 通用组件接口
        -> Browser
          -> Playwright
```

`Browser` 负责浏览器生命周期、导航和基础交互；组件表达业务动作；站点组件保存具体 Selector；业务服务不直接依赖 Playwright。
