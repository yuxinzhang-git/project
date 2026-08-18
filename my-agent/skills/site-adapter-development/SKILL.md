---
name: site-adapter-development
description: Develop or extend website adapters in this project using the Browser facade, PageContext, structured intents, site navigation/actions, page objects, semantic components, capability declarations, and verification scripts. Use when adding a new site such as Xianyu, Taobao, JD, GitHub, Zhihu, or when adding site functionality that affects browser navigation or current-page actions.
---

# Site Adapter Development

Use this skill when implementing a website under `app/browser/sites/<site>/` or when extracting reusable browser components. Read the existing `app/browser/` code and the target site's README before editing. Preserve existing public adapter methods unless the user explicitly authorizes a breaking change.

## Non-Negotiable Rules

- Keep all Playwright imports and calls inside `app/browser/`. Business code must use `Browser`, adapters, page objects, or components.
- Keep `Browser` site-agnostic. It owns browser lifecycle, URL navigation, basic interaction, state, and screenshots; it must not contain website semantics.
- Keep site-specific code inside `app/browser/sites/<site>/`.
- Do not bypass login, CAPTCHA, slider verification, risk control, paywalls, or other security checks. Return a clear typed or classified error.
- Do not claim a capability unless executable logic exists and is verified.
- Treat posting, messaging, purchasing, payment, coin/reward actions, and account mutations as side effects. Follow the user's explicit scope and never invent a confirmation policy that contradicts the request.

## Site Layout

Create only the modules needed by the site:

```text
app/browser/sites/<site>/
├── navigation.py       # page-location changes
├── actions.py          # current-page operations and compatibility facade
├── adapter.py          # stable site entry point
├── capability.py       # executable capability declaration
├── verify.py           # focused real-browser verification script
├── pages/              # site page objects
├── components/         # site-specific semantic implementations
└── README.md           # Chinese user-facing site capability summary
```

`navigation.py` may implement home, search, back, channel/profile, history, favorites, or other page transitions. It must not perform video playback, product selection, likes, favorites, sorting, or other content actions.

`actions.py` and site components implement operations on the current page: list/open items, play or pause media, pagination, sorting, filtering, reactions, collection changes, and similar actions. They must not hard-code page transitions that belong to navigation.

`adapter.py` composes navigation, actions, page objects, and components. Keep compatibility aliases here when existing callers use older method names.

## Intent Contract

Keep exactly two categories:

- `navigation`: changes the current page location.
- `page_action`: operates on content or controls already on the current page.

Prefer structured plans over adding many top-level intent names:

```json
{"category":"navigation","target":"search","action":"open","keyword":"机械键盘"}
{"category":"page_action","target":"item","action":"open","index":3}
{"category":"page_action","target":"pagination","action":"next"}
{"category":"page_action","target":"content","action":"favorite","state":"add"}
```

Use stable fields such as `keyword`, `index`, `page`, `relative`, `mode`, `condition`, `state`, and `count`. Preserve natural-language compatibility, but dispatch from the structured plan.

## Component Decisions

Extract a component only when the concept is semantic and likely to recur. Start with the smallest useful interface:

- `VideoList` or an item-list implementation: `list()`, `open(index)`.
- `Player`: `play()`, `pause()`.
- `SearchBox`: `search(keyword)`.
- `Pagination`: `next()`, `previous()`, optional `goto(page)`.
- `ContentActions`: only when the site has current-content interactions such as like, favorite, or coin.
- `ContentCollection`: history, favorites, playlists, or other saved-item lists.

Do not force every site to inherit a large `ListPage`. Use optional capabilities such as pagination, sorting, and filtering. Keep selectors and DOM traversal inside the concrete site component.

## PageContext

Refresh `PageContext` from the current Browser state at operation time. It may identify site, page type, URL, title, query keyword, user/channel identity, and current item ID. Do not rely on stale service-level page caches after manual browser navigation.

Add a page type only when it changes dispatch behavior, such as `search`, `video`, `history`, `favorites`, or `product_detail`. Keep site parsing in the context model, not in `Browser`.

## Errors and Security

Distinguish at least:

- page structure or selector mismatch;
- login or account identity unavailable;
- CAPTCHA, slider, or site risk control;
- Browser, Playwright, configuration, or network failure.

For destructive or irreversible actions, use explicit structured state where possible, for example `favorite + state=add/remove`, rather than blind toggle clicks. If a site dialog requires a final submit button, automate that site step only when the user's requested action authorizes it; do not add an unrelated user-facing confirmation.

## Capability and Verification

Update `capability.py` together with the implementation. Keep navigation, page actions, and objects aligned with actual adapter methods.

Before finishing:

1. Compile the Python package with `python -m compileall -q app`.
2. Test structured parsing for navigation and page actions.
3. Test adapter imports and compatibility methods.
4. Run focused fake-Browser/component tests for selector sequences and state transitions.
5. Run real-browser checks for home, search, list, and open-item flows when network and login state permit.
6. Preserve real login, CAPTCHA, risk-control, and network errors in the report.
7. Update the target site's Chinese `README.md` with implemented features and limitations.

## New-Site Checklist

Before coding, identify the site's:

- home and search URLs;
- item/list page types and stable visible controls;
- pagination, sort, and filter behavior;
- account-dependent pages and login requirements;
- side-effect actions and their add/remove states;
- verification or risk-control states.

Then implement the smallest working adapter, add only justified shared components, expose truthful capabilities, and verify both direct adapter calls and natural-language plans.
