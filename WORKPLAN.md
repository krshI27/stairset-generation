# WORKPLAN — stairset-generation

**Status**: Local only. GitHub mirror exists. Streamlit Cloud deployment unblocked.
**Last changes**: UI params improved for usability, `render_png` headless rasterizer added, fisheye delegates to `vectorlab.fisheye_vertex` (2026-04-24)

---

## This sprint (Apr 24 – May 1)

- [ ] **STR-1** ~1hr: Deploy to Streamlit Cloud — connect `github.com/krshI27/stairset-generation`, test app loads + 3D mesh renders correctly
- [ ] **ZV1-3** ~1hr: Add `?preset=` URL loader — read `DEFAULTS`-shaped JSON from `st.query_params`, populate `st.session_state` before widget init; test one saved preset round-trip
- [ ] **STR-2** ~1hr: Evaluate stair renders as Prodigi print product — generate 3–4 strong outputs via `render_png`, check DPI requirements at A3 (300dpi min for Prodigi)

## Next sprint

- [ ] **STR-EXPORT** ~1hr: Fix `render_png` DPI — pass `dpi=300` to matplotlib figure; verify output is ≥3508×4961px for A3@300dpi; add `st.download_button` for PNG
- [ ] **STR-PRODIGI** ~1hr: Add "Order Print" button → `render_png(dpi=300)` → upload bytes to R2 public bucket → `POST https://api.prodigi.com/v4.0/orders` with `GLOBAL-FAP-16.5X11.7` (A3); use `PRODIGI_API_KEY` from `.streamlit/secrets.toml`
- [ ] **ZV1-preset-stair** ~30min: Create 2–3 Zine Vol.1 candidate presets — run render, save params as `presets/zine-vol1-*.json`
- [ ] **CRT-1** ~30min: Add stairset-generation to karoshirt.art `/create` gallery page
- [ ] **EXHIBIT-STR** ~1hr: Embed steganographic watermark in exported PNG — preset ID + timestamp in pixel LSBs (see Exhibition Concept note)

## Preset loader pattern (Streamlit)

```python
import json
import streamlit as st

_raw = st.query_params.get("preset")
if _raw:
    try:
        _p = json.loads(_raw)
        for k, v in _p.get("params", {}).items():
            st.session_state.setdefault(k, v)
    except (json.JSONDecodeError, KeyError):
        pass
# add key= to every widget matching the DEFAULTS key names
```

`DEFAULTS` dict is the preset schema as-is — just JSON-serialize it.

## Decisions needed

- `render_png` current DPI? Check matplotlib `fig.savefig(buf, dpi=...)` — set to 300 for print
- Preset hosting: start with repo-bundled `presets/` dir; switch to R2 fetch when hosting presets centrally

## Notes

- `fisheye_strength=0` → clean architectural; high → sculptural/abstract — both strong exhibition prints
- See `krshi27-scribe/WORKPLAN.md` for shared `upload_to_r2()` + `create_prodigi_order()` pattern
- Depends on `vectorlab` as editable sibling (`-e ../vectorlab` in environment.yml)
