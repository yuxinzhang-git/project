# my-agent

`my-agent` is a FastAPI application with a layered browser automation module. The single local development server is:

```powershell
& .\agent\Scripts\python.exe agent_api.py
```

Open the web interface at `http://127.0.0.1:8000`. Do not start additional
Uvicorn instances on other ports when using the persistent browser profile.

Run `start.bat` in a console window to start the service. Press `Ctrl+C` or
close that window to stop the service and its project Browser session.

## Browser architecture

All Playwright imports and calls are inside `app/browser/`. Business code uses the `Browser` facade, site adapters, page objects, and semantic components. `Browser` owns the persistent Edge session, navigation, basic interaction, state inspection, and screenshots.

`PageContext` is rebuilt from the current browser URL and title whenever an operation runs. It contains `site`, `page_type`, `url`, `title`, `keyword`, `channel_id`, `user_id`, and `current_video_id`, so manual browser navigation does not leave stale site state in the service.

Generic component contracts live in `app/browser/components/`:

- `VideoList`: `list()`, `open(index)`, `play(index)`
- `Player`: `play()`, `pause()`
- `SearchBox`: `search(keyword)`

Site-specific selectors remain inside the site components and page objects. They are not used by the service layer.

## Structured intents

The rule parser keeps `category` and returns a structured plan:

```json
{"category":"page_action","target":"video","action":"play","index":3}
```

Relative playback uses:

```json
{"category":"page_action","target":"video","action":"play","relative":1}
```

Search uses:

```json
{"category":"navigation","target":"search","action":"open","keyword":"Python 教程"}
```

Existing Chinese commands such as `在哔哩哔哩搜索 Python 教程`, `打开第三个视频`, `播放下一个视频`, `打开淘宝`, `按销量排序`, and `返回搜索结果页` remain supported. No model API is used; parsing is deterministic.

## Sites

### Bilibili

Implemented under `app/browser/sites/bilibili/`: home, search, channel, favorites, back, video listing, opening and playing indexed videos, relative playback, and opening the current video. Compatibility methods such as `open_result()` and `play_result()` remain available.

### Taobao

Implemented under `app/browser/sites/taobao/`: home, keyword search, favorites navigation, back, product listing, opening an indexed product, sorting, and filtering. Taobao login pages, captcha/slider pages, and risk-control pages are detected and reported as explicit errors. The automation does not bypass verification.

Capabilities are available at `GET /api/smart/capabilities` and are backed by the adapters' actual methods.

## Verification

Run Python compilation checks with:

```powershell
& .\agent\Scripts\python.exe -m compileall -q app
```

Real website checks require network access and a usable Edge/Playwright session. A login or verification page is a valid test result and must remain visible as an explicit error.



## Runtime skills

`my-agent` explicitly loads local skills at application startup from `skills/*/SKILL.md`, but only as manifests. The loader reads each file's YAML-style frontmatter, builds the skill list, and defers the full instruction body until a skill is actually requested.

```text
GET  /api/skills
GET  /api/skills/{name}/manifest
GET  /api/skills/{name}
POST /api/skills/reload
```

`GET /api/skills/{name}` loads the full `SKILL.md` content on demand. `GET /api/skills/{name}/manifest` stays metadata-only. The status endpoint also includes the current skill summaries.
