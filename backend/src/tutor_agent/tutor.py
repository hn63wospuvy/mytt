"""The Tutor agent: system prompt (spec §7.3) + web_search tool registration.

The "giảng VI / luyện EN" routing is steered by the prompt (spec §7.2 note), not
a hard state machine. In addition to the §7.1 ``<vi>``/``<en>`` spans, the tutor
emits *unspoken* structured markers that drive the bilingual parse + GIẢNG mode:

    <fix wrong="..." correct="..." note="..."/>     <vocab en="..." vi="..."/>

These are stripped before TTS (see ``extract.remove_markers``).
"""

from __future__ import annotations

from typing import Optional

from livekit.agents import Agent

from .search.base import WebSearch
from .text_pipeline import clean_text_stream
from .tools import make_web_search_tool

_BASE_PROMPT = """\
Bạn là trợ lý tiếng Anh cho người Việt, có ba chế độ:
- GIẢNG: nói tiếng Việt — giải thích ngữ pháp, sửa lỗi, hướng dẫn.
- LUYỆN: nói tiếng Anh — trò chuyện, role-play, luyện diễn đạt.
- HỎI-ĐÁP: trả lời câu hỏi của học viên; nếu cần thông tin cập nhật/sự kiện,
  GỌI TOOL web_search rồi tổng hợp CHỈ từ kết quả trả về và nêu nguồn ("theo ...").
  Trả lời bằng đúng ngôn ngữ học viên hỏi.

Quy tắc xuất:
- Bọc mỗi đoạn trong <vi>...</vi> hoặc <en>...</en>. Ví dụ tiếng Anh chèn trong
  lời giảng tiếng Việt vẫn bọc <en>...</en> riêng.
- Ngoài các đoạn <vi>/<en>, KHÔNG nói gì khác. Hai loại marker dưới đây KHÔNG
  được đọc lên, chỉ là dữ liệu học tập, đặt xen kẽ tùy ý:
    <fix wrong="câu sai" correct="câu đúng" note="ghi chú tiếng Việt"/>
    <vocab en="từ tiếng Anh" vi="nghĩa tiếng Việt"/>
  Khi sửa lỗi của học viên, PHẢI kèm một marker <fix .../>. Khi giới thiệu từ mới
  đáng nhớ, kèm <vocab .../>.

Hành vi:
- Mặc định LUYỆN, nói tiếng Anh tự nhiên theo trình độ học viên.
- Khi học viên mắc lỗi, KHÔNG ngắt giữa câu. Chờ họ nói xong rồi sang GIẢNG
  (tiếng Việt) nêu ngắn gọn lỗi + cách đúng + 1 ví dụ <en>, rồi quay lại LUYỆN.
- Khi học viên hỏi bằng tiếng Việt hoặc bí, sang GIẢNG.
- Câu hỏi thông tin → cân nhắc web_search; trả lời NGẮN, có nêu nguồn.
- MỖI LƯỢT NGẮN (1–3 câu) để độ trễ thấp; ấm áp, khích lệ, không phán xét.\
"""


# Cloud (Gemini Live) speaks audio server-side, so inline tags would be spoken.
# It gets a tag-free prompt and code-switches naturally instead.
_CLOUD_PROMPT = """\
Bạn là trợ lý tiếng Anh cho người Việt, có ba chế độ:
- GIẢNG: nói tiếng Việt — giải thích ngữ pháp, sửa lỗi, hướng dẫn.
- LUYỆN: nói tiếng Anh — trò chuyện, role-play, luyện diễn đạt.
- HỎI-ĐÁP: trả lời câu hỏi; dùng tìm kiếm Google tích hợp khi cần thông tin
  cập nhật/sự kiện, nêu nguồn ngắn gọn. Trả lời đúng ngôn ngữ học viên hỏi.

Hành vi:
- Mặc định LUYỆN, nói tiếng Anh tự nhiên theo trình độ. Trộn Việt–Anh tự nhiên.
- Khi học viên mắc lỗi, chờ họ nói xong rồi GIẢNG bằng tiếng Việt: lỗi + cách
  đúng + 1 ví dụ tiếng Anh, rồi quay lại LUYỆN.
- Khi học viên hỏi bằng tiếng Việt hoặc bí, sang GIẢNG.
- MỖI LƯỢT NGẮN (1–3 câu); ấm áp, khích lệ, không phán xét.\
"""


def build_instructions(level: Optional[str], *, tagged: bool = True) -> str:
    """System prompt. ``tagged`` controls the §7.1 inline-tag output contract
    (local pipeline); the cloud realtime profile uses the tag-free variant."""
    base = _BASE_PROMPT if tagged else _CLOUD_PROMPT
    if level:
        return f"{base}\n\nTrình độ học viên: {level}. Điều chỉnh độ khó cho phù hợp."
    return base


class Tutor(Agent):
    def __init__(
        self,
        *,
        search_backend: Optional[WebSearch] = None,
        level: Optional[str] = None,
        enable_web_search: bool = True,
        tagged: bool = True,
        on_search=None,
    ):
        # Cloud profile (Gemini Live) has Google Search grounding built into the
        # session, so the self-assembled web_search tool is omitted (spec §8).
        tools = []
        if enable_web_search:
            if search_backend is None:
                raise ValueError("search_backend required when enable_web_search=True")
            tools = [make_web_search_tool(search_backend, on_search)]
        super().__init__(instructions=build_instructions(level, tagged=tagged), tools=tools)

    def tts_node(self, text, model_settings):
        # Strip <vi>/<en> tags and <fix>/<vocab> markers so none are spoken.
        # NOTE: do NOT clean transcription_node — the assistant chat item must
        # keep the raw tagged text so the wiring can parse segments + derive the
        # turn mode. The app renders its own colored transcript from the data
        # channel; the framework's built-in transcript sync is disabled in agent.py.
        return Agent.default.tts_node(self, clean_text_stream(text), model_settings)
