# Source hunting

Where good evidence about a SaaS or enterprise app usually lives, and how to find it.
Swap `<App>`, `<Edition>`, `<module>` and `<screen>` in the queries.

## Tier 1: official vendor

| Source | Where | What it gives |
|---|---|---|
| Help center / docs portal | `help.<vendor>.com`, `docs.<vendor>.com`, `support.<vendor>.com`, `<vendor>.zendesk.com`, `community.<vendor>.com/s/article` | Menu paths, field definitions, step lists, screenshots |
| Admin / implementation / user guides | PDFs: `"<App> <Edition>" "user guide" filetype:pdf`, `"administrator guide"` | Full field lists, rules, permissions |
| Release notes | `"<App>" "release notes" <year>` | When a screen or field appeared or was renamed; current labels |
| API docs / OpenAPI | developer portal, `swagger`, `openapi.json`, GitHub repos with the vendor's spec | Real entity and field names, enums, paths |
| Vendor YouTube / webinars / academy | `site:youtube.com "<App>" <module>` | Workflow order, real UI in motion |
| Status page and trust docs | rarely useful for UI; skip unless asked | — |

Official help often hides behind a customer login. Log it as `unreachable: login required`
and look for mirrors in tiers 2 and 3. Don't try to get around the login.

## Tier 2: official training and certified partners

- Training catalogs and course outlines (Coursera, LinkedIn Learning, vendor academies).
  A course's table of contents is a good module map even when the videos are paid.
- Implementation partners' blogs and how-to articles: `"<App>" "<module>" "how to" partner`.
- Third-party product-adjacent vendors (benefits, payroll or tax partners) often publish
  "how to do X in <App>" guides with screenshots.

## Tier 3: customer help pages

Organisations that use the app publish staff guides. These are often the richest
step-by-step sources with screenshots:

```
"<App>" "<screen or action>" site:.edu
"<App>" "<screen or action>" site:.gov OR site:.org
"<App>" "quick reference guide" OR "job aid" OR "tip sheet" filetype:pdf
"how to" "<App>" "<action>" employee guide
```
Customers configure their own tenant. Labels, extra fields and hidden tabs may differ from
the default. When two unrelated customers show the same thing, treat it as default.

## Tier 4: community

- Vendor community forums: questions often reveal error messages, validation rules and
  edge states that the docs skip.
- Reddit (`r/<app>`, `r/sysadmin`, `r/humanresources`), Stack Overflow for APIs.
- Third-party YouTube walkthroughs: check the edition and the UI era (look for the
  date and the logo or theme).

## Edition check (do this for every source)

Look for: the product name in the page title or footer, the URL path (`/pro/`, `/ready/`),
the version string, the UI theme or logo in screenshots, and the publish date compared
with known redesigns. Record the verdict as `match`, `mismatch` or `unverified` with
the clue, for example "footer says Workforce Ready".

## Search hygiene

- Send several searches in one turn. Use quoted UI labels (`"Add Withholding Form"`): an
  exact label is the strongest query, because it finds pages that show that screen.
- When a label is found, search for its neighbours on the same screen to find more
  pages about that screen.
- Prefer the newest source when labels differ, and log the older label as `conflict`.
- Record unreachable sources (404, timeout, login, region block) with the reason. The
  next researcher shouldn't have to find that out again.
