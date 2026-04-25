# WORKPLAN — stairset-generation

**Status**: DEPLOYED on Streamlit Cloud (2026-04-25). Preset loader done (ZV1-3). render_png rasterizer done.
**Last changes**: `?preset=` URL loader + preset URL generator added (ZV1-3 done 2026-04-25). UI params improved, `render_png` rasterizer added (2026-04-24).

---

## Active priorities (2026-04-25 — Path A: ready, just needs presets + DPI fix)

### Path A: Zine Vol.1 preset rollout

- [x] **ZV1-3** ~1hr: `?preset=` URL loader done (2026-04-25)
- [ ] **STR-EXPORT** ~1hr: Fix `render_png` DPI — pass `dpi=300` to matplotlib figure; verify output ≥3508×4961px for A3@300dpi; add `st.download_button` for PNG. Required before zine print proof.
- [ ] **ZV1-preset-stair** ~30min: Create 2–3 Zine Vol.1 candidate presets — run render, save params as `presets/zine-vol1-*.json`
- [ ] **STR-2** ~1hr: Evaluate stair renders as Prodigi print product — pick 3–4 strongest outputs at A3 300dpi

### Revenue path (deferred)

- [x] **STR-1**: Deployed to Streamlit Cloud (2026-04-25)
- [ ] **STR-PRODIGI** ~1hr: "Order Print" button → `render_png(dpi=300)` → upload bytes to R2 public bucket → `POST https://api.prodigi.com/v4.0/orders` with `GLOBAL-FAP-16.5X11.7` (A3); `PRODIGI_API_KEY` from `.streamlit/secrets.toml`
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
