# Browser 模块

`Browser` 是项目统一的网页操作接口。业务代码只能导入 `Browser`，不能直接导入 Playwright。

```python
from app.browser import Browser

browser = Browser()
browser.open("https://www.baidu.com")
browser.search("Python 自动化")
browser.click("button")
browser.type("input[name=q]", "Playwright")
print(browser.text("h1"))
browser.screenshot("data/browser/screenshots/example.png")
browser.close()
```

站点专属操作放在 `app/browser/sites/`，每个站点使用一个独立目录。例如 `app/browser/sites/bilibili/` 包含：

- `navigation.py`：页面导航，例如打开首页、搜索、打开频道和收藏夹。
- `actions.py`：当前页面操作，例如读取视频、打开第 N 个视频、播放上下一个视频。
- `adapter.py`：站点能力组合入口，并保留兼容调用方法。

适配器只能调用 `Browser`，不能直接导入 Playwright。

默认使用 Microsoft Edge 和项目专用持久化目录 `data/browser/profile/`。因此首次登录后的 Cookie 和会话数据会被后续 Browser 调用复用。不要把该目录提交到版本库。
