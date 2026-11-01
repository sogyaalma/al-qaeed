#!/usr/bin/env python3
"""A bounded subset of Liquid, used only to render the pinned release's own
template and example sources as static showcase pages.

  from liquid_subset import Renderer
  html, unresolved = Renderer(data_dir).render(text, page={...})

The pinned tag ships its page templates and examples as Jekyll sources
(`templates/*.md`, `examples/*.md`). This project builds with the standard
library only and never runs Jekyll, so the showcase renders them with exactly the
constructs those files use — measured, not guessed:

  tags     for (+ limit), if / elsif / else, unless, assign, capture, include,
           comment
  lookups  dotted paths, ["bracketed"] keys, string / number / boolean literals,
           forloop.index, forloop.index0, forloop.first, forloop.last
  filters  relative_url, default, append, split, size, remove, upcase, downcase

Anything outside that set is not approximated: it is replaced with an HTML comment
and reported through `unresolved`, so a page is never silently wrong and the
generator can flag the row `partial` in docs/NDS-SHOWCASE.md.
"""
from __future__ import annotations

import pathlib
import re

TAG = re.compile(r"\{%-?(.*?)-?%\}|\{\{-?(.*?)-?\}\}", re.S)
BLOCKS = {"for": "endfor", "if": "endif", "unless": "endunless", "capture": "endcapture"}
TRUTHY_EMPTY = {"nil", "null", "none"}


class Renderer:
    def __init__(self, data_dir: pathlib.Path, asset_root: pathlib.Path, placeholder: str):
        self.data_dir = data_dir
        self.asset_root = asset_root
        self.placeholder = placeholder
        self._data: dict[str, object] = {}
        self.unresolved: list[str] = []

    # ── public ───────────────────────────────────────────────────────────────
    def render(self, text: str, *, page: dict | None = None, site: dict | None = None) -> str:
        self.unresolved = []
        context = {
            "site": {
                "title": "Al-Qaeed",
                "time": "2026-10-22",
                "data": {"content": self},  # `site.data.content.x` resolves lazily
                **(site or {}),
            },
            "page": page or {},
        }
        nodes, _, _ = self._parse(self._tokenize(text))
        return "".join(self._evaluate(nodes, context))

    # Lazy `site.data.content.<name>` lookups straight from the pinned YAML.
    def __getitem__(self, name: str):
        if name not in self._data:
            from build_showcase import yaml_list

            path = self.data_dir / f"{name}.yml"
            self._data[name] = yaml_list(path.read_text(encoding="utf-8")) if path.is_file() else []
        return self._data[name]

    def get(self, name: str, default=None):
        try:
            return self[name]
        except Exception:
            return default

    # ── tokenizer / parser ───────────────────────────────────────────────────
    @staticmethod
    def _tokenize(text: str) -> list[tuple[str, str]]:
        parts: list[tuple[str, str]] = []
        position = 0
        for match in TAG.finditer(text):
            if match.start() > position:
                parts.append(("text", text[position:match.start()]))
            if match.group(1) is not None:
                parts.append(("tag", match.group(1).strip()))
            else:
                parts.append(("out", match.group(2).strip()))
            position = match.end()
        if position < len(text):
            parts.append(("text", text[position:]))
        return parts

    def _parse(self, parts: list[tuple[str, str]], stop: tuple[str, ...] = ()) -> tuple[list, int, str | None]:
        nodes: list = []
        index = 0
        while index < len(parts):
            kind, value = parts[index]
            if kind != "tag":
                nodes.append((kind, value))
                index += 1
                continue
            keyword = value.split(" ", 1)[0] if value else ""
            if keyword in stop:
                return nodes, index, keyword
            if keyword == "comment":
                index = self._skip_to(parts, index, "endcomment")
                continue
            if keyword in BLOCKS:
                node, index = self._parse_block(parts, index, keyword, value)
                nodes.append(node)
                continue
            nodes.append(("stmt", value))
            index += 1
        return nodes, index, None

    @staticmethod
    def _skip_to(parts: list[tuple[str, str]], index: int, end_keyword: str) -> int:
        depth = 0
        while index < len(parts):
            kind, value = parts[index]
            if kind == "tag":
                keyword = value.split(" ", 1)[0] if value else ""
                if keyword == end_keyword and depth == 0:
                    return index + 1
                if keyword in BLOCKS:
                    depth += 1
                if keyword.startswith("end"):
                    depth = max(0, depth - 1)
            index += 1
        return index

    def _parse_block(self, parts, index, keyword, header):
        branches = []
        body, cursor, stop_keyword = self._parse(parts[index + 1:], stop=("else", "elsif", BLOCKS[keyword]))
        branches.append((header, body))
        cursor = index + 1 + cursor
        while stop_keyword == "elsif":
            header = parts[cursor][1]
            body, offset, stop_keyword = self._parse(parts[cursor + 1:], stop=("else", "elsif", BLOCKS[keyword]))
            branches.append((header, body))
            cursor = cursor + 1 + offset
        if stop_keyword == "else":
            body, offset, stop_keyword = self._parse(parts[cursor + 1:], stop=(BLOCKS[keyword],))
            branches.append((None, body))
            cursor = cursor + 1 + offset
        return ("block", keyword, branches), cursor + 1

    # ── evaluation ───────────────────────────────────────────────────────────
    def _evaluate(self, nodes: list, context: dict) -> list[str]:
        out: list[str] = []
        for node in nodes:
            kind = node[0]
            if kind == "text":
                out.append(node[1])
            elif kind == "out":
                out.append(self._stringify(self._expression(node[1], context), node[1]))
            elif kind == "stmt":
                out.append(self._statement(node[1], context))
            elif kind == "block":
                out.append(self._block(node, context))
        return out

    def _block(self, node, context: dict) -> str:
        _, keyword, branches = node
        if keyword == "for":
            return self._for(branches[0], context)
        if keyword == "capture":
            name = branches[0][0].split(None, 1)[1].strip()
            context[name] = "".join(self._evaluate(branches[0][1], context))
            return ""
        # if / unless
        for position, (header, body) in enumerate(branches):
            if keyword == "unless":
                condition = "" if header is None else header.split(None, 1)[1]
                if position == 0 and not self._truthy(condition, context):
                    return "".join(self._evaluate(body, context))
                if position > 0 and header is None:
                    return "".join(self._evaluate(body, context))
                continue
            if header is None:
                return "".join(self._evaluate(body, context))
            condition = header.split(None, 1)[1]
            if self._truthy(condition, context):
                return "".join(self._evaluate(body, context))
        return ""

    def _for(self, branch, context: dict) -> str:
        header, body = branch
        match = re.match(r"for\s+(\w+)\s+in\s+(.+?)(?:\s+limit\s*:\s*(\d+))?$", header.strip())
        if not match:
            self.unresolved.append(header.strip())
            return f"<!-- showcase: unresolved {{{{ {header.strip()} }}}} -->"
        variable, source_expression, limit = match.group(1), match.group(2), match.group(3)
        source = self._expression(source_expression, context)
        if not isinstance(source, (list, tuple)):
            self.unresolved.append(f"for over {source_expression}")
            return ""
        items = list(source)[: int(limit)] if limit else list(source)
        rendered = []
        for position, item in enumerate(items):
            inner = dict(context)
            inner[variable] = item
            inner["forloop"] = {
                "index": position + 1,
                "index0": position,
                "first": position == 0,
                "last": position == len(items) - 1,
                "length": len(items),
            }
            rendered.append("".join(self._evaluate(body, inner)))
        return "".join(rendered)

    def _statement(self, statement: str, context: dict) -> str:
        keyword = statement.split(" ", 1)[0]
        if keyword == "assign":
            match = re.match(r"assign\s+(\w+)\s*=\s*(.+)$", statement.strip())
            if not match:
                self.unresolved.append(statement)
                return ""
            context[match.group(1)] = self._expression(match.group(2), context)
            return ""
        if keyword == "include":
            target = statement.split(None, 1)[1].strip()
            return f"<!-- showcase: the project chrome renders {{% include {target} %}} -->"
        self.unresolved.append(statement)
        return f"<!-- showcase: unresolved {{{{ {statement} }}}} -->"

    # ── expressions ──────────────────────────────────────────────────────────
    def _expression(self, expression: str, context: dict):
        pieces = self._split_pipes(expression)
        value = self._atom(pieces[0].strip(), context)
        for piece in pieces[1:]:
            name, _, argument = piece.strip().partition(":")
            value = self._filter(name.strip(), argument.strip(), value, context)
        return value

    @staticmethod
    def _split_pipes(expression: str) -> list[str]:
        pieces, quote, depth, current = [], "", 0, ""
        for char in expression:
            if quote:
                current += char
                if char == quote:
                    quote = ""
                continue
            if char in "\"'":
                quote = char
                current += char
            elif char in "[(":
                depth += 1
                current += char
            elif char in "])":
                depth -= 1
                current += char
            elif char == "|" and depth == 0:
                pieces.append(current)
                current = ""
            else:
                current += char
        pieces.append(current)
        return pieces

    def _atom(self, atom: str, context: dict):
        atom = atom.strip()
        if not atom:
            return ""
        if len(atom) > 1 and atom[0] == atom[-1] and atom[0] in "\"'":
            return atom[1:-1]
        if atom in ("true", "false"):
            return atom == "true"
        if atom in TRUTHY_EMPTY:
            return None
        if re.fullmatch(r"-?\d+", atom):
            return int(atom)
        if re.fullmatch(r"-?\d+\.\d+", atom):
            return float(atom)
        bracket = re.match(r"([\w.]+)\[(.+)\]$", atom)
        if bracket:
            base = self._atom(bracket.group(1), context)
            key = self._atom(bracket.group(2), context)
            return self._index(base, key)
        value: object = context
        for step in atom.split("."):
            value = self._index(value, step)
            if value is None:
                return None
        return value

    @staticmethod
    def _index(value, key):
        if value is None:
            return None
        if isinstance(value, dict):
            return value.get(str(key))
        if hasattr(value, "__getitem__") and not isinstance(value, str):
            try:
                return value[key]
            except Exception:
                try:
                    return value[int(key)]
                except Exception:
                    return None
        return getattr(value, str(key), None)

    def _filter(self, name: str, argument: str, value, context: dict):
        if name == "relative_url":
            return self._relative_url(value)
        if name == "default":
            fallback = self._atom(argument, context)
            return value if value not in (None, "", False, []) else fallback
        if name == "append":
            return f"{self._stringify(value, '')}{self._stringify(self._atom(argument, context), '')}"
        if name == "prepend":
            return f"{self._stringify(self._atom(argument, context), '')}{self._stringify(value, '')}"
        if name == "split":
            separator = self._stringify(self._atom(argument, context), "")
            return str(value or "").split(separator)
        if name == "size":
            return len(value) if hasattr(value, "__len__") else 0
        if name == "remove":
            return str(value or "").replace(self._stringify(self._atom(argument, context), ""), "")
        if name == "upcase":
            return str(value or "").upper()
        if name == "downcase":
            return str(value or "").lower()
        self.unresolved.append(f"filter {name}")
        return value

    def _relative_url(self, value) -> str:
        path = str(value or "").lstrip("/")
        if (self.asset_root / path).is_file():
            return "/" + path
        if path.startswith(("assets/img/", "assets/icon/", "docs-assets/")):
            return self.placeholder
        return "/" + path

    def _truthy(self, condition: str, context: dict) -> bool:
        condition = condition.strip()
        for operator in ("==", "!=", " contains ", " >= ", " <= ", " > ", " < "):
            if operator in condition:
                left, _, right = condition.partition(operator)
                left_value = self._expression(left, context)
                right_value = self._expression(right, context)
                if operator == "==":
                    return self._stringify(left_value, "") == self._stringify(right_value, "")
                if operator == "!=":
                    return self._stringify(left_value, "") != self._stringify(right_value, "")
                if operator.strip() == "contains":
                    return str(right_value) in str(left_value or "")
                try:
                    left_number, right_number = float(left_value), float(right_value)
                except (TypeError, ValueError):
                    self.unresolved.append(f"condition {condition}")
                    return False
                return {
                    ">=": left_number >= right_number,
                    "<=": left_number <= right_number,
                    ">": left_number > right_number,
                    "<": left_number < right_number,
                }[operator.strip()]
        if " and " in condition or " or " in condition:
            self.unresolved.append(f"compound condition {condition}")
            return False
        value = self._expression(condition, context)
        if value in (None, False, ""):
            return False
        if isinstance(value, (list, dict)) and not value:
            return False
        return True

    @staticmethod
    def _stringify(value, original: str) -> str:
        if value is None:
            return ""
        if value is True:
            return "true"
        if value is False:
            return "false"
        if isinstance(value, (list, tuple)):
            return "".join(str(item) for item in value)
        if isinstance(value, float) and value.is_integer():
            return str(int(value))
        return str(value)
