"""Reads Wiktionary's own Lua data modules into Python (labels, tags: R6.6, R6.7).

The data is the dump's, loaded with `mw.loadData` inside a real `{{#invoke:}}` (some
data modules need a frame while loading), through a virtual module the worker's Wtp
serves from memory. Alias resolution therefore follows Wiktionary's data for this pin.
"""

from __future__ import annotations

import json
from typing import Any

from polwikt.expand.wtp import PolwiktWtp

MODULE = "Module:polwikt/export"
_SOURCE = r"""
local p = {}

local function flatten(value, depth)
  if type(value) ~= "table" then return value end
  if depth > 3 then return nil end
  local out = {}
  for k, v in pairs(value) do
    if type(k) == "string" or type(k) == "number" then
      out[tostring(k)] = flatten(v, depth + 1)
    end
  end
  return out
end

-- {{#invoke:polwikt/export|data|Module:a|Module:b}}: each module's table, as JSON.
function p.data(frame)
  local result = {}
  local i = 1
  while frame.args[i] do
    local name = frame.args[i]
    local ok, value = pcall(mw.loadData, name)
    if ok then
      result[name] = flatten(value, 0)
    else
      result[name] = {__error = tostring(value)}
    end
    i = i + 1
  end
  return mw.text.jsonEncode(result)
end

return p
"""


class LuaDataError(RuntimeError):
    """A data module failed to load: the expansion layer can't read Wiktionary data."""


def load_modules(wtp: PolwiktWtp, modules: list[str]) -> dict[str, dict[str, Any]]:
    """`mw.loadData` of each module, as nested dicts with string keys."""
    wtp.virtual_modules[MODULE] = _SOURCE
    title = wtp.title
    wtp.start_page("polwikt-export")
    try:
        call = "{{#invoke:polwikt/export|data|" + "|".join(modules) + "}}"
        text = wtp.expand(call)
    finally:
        if title is not None:
            wtp.start_page(title)
    try:
        data: dict[str, dict[str, Any]] = json.loads(text)
    except json.JSONDecodeError as e:
        raise LuaDataError(f"data module export failed: {text[:300]}") from e
    for name, value in data.items():
        if "__error" in value:
            raise LuaDataError(f"{name}: {value['__error']}")
    return data
