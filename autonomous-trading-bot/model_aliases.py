"""Map ten model hoi dong (`cline-pass/...`) -> **id THAT cua gateway Cline**.

    from model_aliases import to_gateway
    to_gateway("cline-pass/glm-5.3")   # -> "z-ai/glm-5.3"

Vi sao (13/10): `clinepass.py`/`ClineProvider` gui NGUYEN VAN ten `cline-pass/X` len
gateway `api.cline.bot`. Gateway nay doi id sang dang `<vendor>/<ten>` va tra
**HTTP 500 {"error":"empty response content"}** cho id la ⇒ **12/14 model hoi dong chet**
(do 48h: 328 ban ghi AGENT, 0 VETO/0 ALLOW) trong khi gateway van song
(`GET /api/v1/models` OK, 462 model).

Bang map duoi day lay TU CHINH danh sach 462 id cua gateway (kiem tra bang
`python tools/_probe_cline.py <id>` -> tra JSON that). Ten alias van duoc giu trong
journal/log de lich su so sanh duoc; chi id GUI DI moi doi.
"""
from __future__ import annotations

CLINE_PREFIX = "cline-pass/"

# alias (khong tien to) -> id that cua gateway (13/10)
GATEWAY_MAP = {
    "glm-5.3": "z-ai/glm-5.3",
    "glm-5.3-flash": "z-ai/glm-5.3-flash",
    "glm-5.3-flashx": "z-ai/glm-5.3-flashx",
    "deepseek-v4-pro": "deepseek/deepseek-v4-pro",
    "deepseek-v4.1-flash": "deepseek/deepseek-v4.1-flash",
    "qwen3.8-max": "qwen/qwen3.8-max-prime",
    "qwen3.7-plus": "qwen/qwen3.7-plus",
    "qwen3.7-max": "qwen/qwen3.7-max",
    "kimi-k3": "moonshotai/kimi-k3",
    "minimax-m3": "minimax/minimax-m3",
    "mimo-v2.6-pro": "xiaomi/mimo-v2.6-pro",
    "mimo-v2.6-flash": "xiaomi/mimo-v2.6-flash",
    "mimo-v2.5": "xiaomi/mimo-v2.5",
    "mimo-v2.5-pro": "xiaomi/mimo-v2.5-pro",
    "muse-spark-1.3-contributor": "meta/muse-spark-1.2-contributor",
}


def strip_prefix(model: str) -> str:
    """Bo tien to `cline-pass/` (giu nguyen neu khong co)."""
    m = str(model or "")
    return m[len(CLINE_PREFIX):] if m.startswith(CLINE_PREFIX) else m


def to_gateway(model: str) -> str:
    """Id de GUI len gateway. Khong co trong bang -> tra ten da bo tien to.

    Ham thuan -> test duoc. Ten la (khong map duoc) se tra ve nguyen trang thai da bo
    tien to: gateway se tu choi va `--council-health` se hien no la model treo.
    """
    base = strip_prefix(model).strip()
    if not base:
        return ""
    if "/" in base:                      # da la id gateway (vd anthropic/claude-haiku-5.5)
        return base
    return GATEWAY_MAP.get(base, base)


def is_mapped(model: str) -> bool:
    """Ten nay co trong bang map khong (dung cho bao cao)."""
    base = strip_prefix(model).strip()
    return bool(base) and ("/" in base or base in GATEWAY_MAP)
