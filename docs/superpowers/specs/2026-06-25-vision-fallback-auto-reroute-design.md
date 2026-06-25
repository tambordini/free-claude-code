# Vision Fallback Auto-Reroute

**วันที่:** 2026-06-25
**สถานะ:** อนุมัติแบบแล้ว รอเริ่ม implement
**ผู้เขียน:** Claude (brainstorming กับ tamBordin)

---

## ปัญหา

เวลาผู้ใช้ส่งรูปภาพไปให้โมเดลที่ไม่รองรับ vision (เช่น `opencode/deepseek-v4-flash-free`), upstream provider จะคืน HTTP 400 มาพร้อม `unknown variant image_url, expected text` ผู้ใช้เจอ error ที่ไม่ช่วยอะไรเลย

## วิธีแก้

Auto-detect เนื้อหารูปภาพใน request pipeline เมื่อโมเดลที่เลือกไม่รองรับ vision ให้ส่งรูปไปยัง vision fallback model (`opencode/mimo-v2.5-free`) แบบ transparent ได้ text analysis กลับมา แล้ว inject ข้อความนั้นกลับเข้าไปใน request เดิม ให้โมเดลหลักประมวลผลต่อ

## ส่วนประกอบ

### 1. Model Capability Data (`supports_vision`)

**ไฟล์:** `providers/model_listing.py`

```python
@dataclass(frozen=True, slots=True)
class ProviderModelInfo:
    model_id: str
    supports_thinking: bool | None = None
    supports_vision: bool | None = None   # เพิ่มใหม่
```

**ไฟล์:** `providers/registry.py`

เพิ่ม method `cached_model_supports_vision(provider_id, model_id) -> bool | None` คู่กับ `cached_model_supports_thinking()` ที่มีอยู่แล้ว

### 2. Hardcoded Vision Model Mapping

**ไฟล์:** `providers/opencode/client.py`

```python
# โมเดลที่รองรับ vision
_VISION_MODELS: frozenset[str] = frozenset({"mimo-v2.5-free"})

# โมเดลที่ไม่รองรับ vision → ส่งไปให้ vision fallback model ไหน
_VISION_FALLBACK: dict[str, str] = {
    "deepseek-v4-flash-free": "mimo-v2.5-free",
}
```

Override method `list_model_infos()` บน `OpenCodeProvider` เพื่อ set `supports_vision=True` ให้โมเดลใน `_VISION_MODELS`

### 3. Non-streaming Provider Call

**ไฟล์:** `providers/base.py`

เพิ่ม abstract method ใหม่บน `BaseProvider`:

```python
async def send_request(
    self, request: Any, *, thinking_enabled: bool | None = None
) -> str:
    """Non-streaming request. ส่ง request แล้วคืน response text ทั้งหมด"""
    raise NotImplementedError
```

**ไฟล์:** `providers/transports/openai_chat/transport.py`

Implement บน `OpenAIChatTransport`:

```python
async def send_request(
    self, request: Any, *, thinking_enabled: bool | None = None
) -> str:
    body = self._build_request_body(request, thinking_enabled=thinking_enabled)
    response = await self._global_rate_limiter.execute_with_retry(
        self._client.chat.completions.create, **body, stream=False
    )
    return response.choices[0].message.content or ""
```

### 4. Pipeline Interceptor

**ไฟล์:** `api/request_pipeline.py`

เพิ่ม method interceptor `_intercept_vision_fallback()` ลงใน `self._message_intercepts`

**Flow:**

1. สแกน `routed.request.messages` ว่ามี `ContentBlockImage` blocks หรือไม่ → `_has_image_content()`
2. เช็ค `ProviderModelInfo.supports_vision` ของโมเดลปัจจุบัน → `self._provider_registry.cached_model_supports_vision()`
3. ถ้ามีรูป **และ** โมเดลไม่รองรับ vision:
   a. ค้นหา fallback model จาก `_VISION_FALLBACK`
   b. สร้าง `MessagesRequest` เฉพาะ vision + system prompt: *"Describe the image(s) in detail, including objects, text, people, actions, and context."*
   c. Resolve fallback model ด้วย `ModelRouter.resolve("opencode/mimo-v2.5-free")`
   d. ได้ instance ของ fallback provider จาก `self._provider_getter()`
   e. เรียก `fallback_provider.send_request(vision_request)` — non-streaming
   f. Rewrite request เดิม: แทนที่ทุก `ContentBlockImage` → text block `"[Image: <analysis>]"` — โมเดลหลักจะได้เห็นแค่ text
   g. Return `None` → pipeline ไปต่อยัง `_provider_stream()` พร้อม request ที่ rewrite แล้ว (ไม่มีรูป)
4. กรณีอื่น → return `None` (ปล่อยผ่าน)

**Error handling:** ถ้า vision fallback พลาด (connection error, timeout, 400/500) ให้ log warning แล้ว return `None` pipeline จะส่ง request เดิมไปยัง upstream ตามปกติ — user จะเห็น error เหมือนเดิม ถ้า fallback ล้มเหลว

**การลงทะเบียน interceptor:**

```python
self._message_intercepts = (
    self._intercept_web_server_tool,
    self._intercept_local_optimization,
    self._intercept_vision_fallback,   # ← ใหม่, ทำงานหลัง local optimization
)
```

### 5. Helper Utilities

**ไฟล์:** `api/request_pipeline.py` (private functions)

- `_has_image_content(request: MessagesRequest) -> bool` — สแกน `.messages[*].content` หา image blocks
- `_inject_image_analysis(request: MessagesRequest, analysis: str) -> MessagesRequest` — deep copy แล้วแทนที่ image blocks ด้วย text blocks ที่มี analysis

## สรุปไฟล์ที่ต้องเปลี่ยน

| ไฟล์ | ประเภทการเปลี่ยนแปลง |
|------|----------------------|
| `providers/model_listing.py` | เพิ่ม field `supports_vision` |
| `providers/registry.py` | เพิ่ม method `cached_model_supports_vision()` |
| `providers/opencode/client.py` | Hardcode vision model mapping, override `list_model_infos()` |
| `providers/base.py` | เพิ่ม abstract method `send_request()` |
| `providers/transports/openai_chat/transport.py` | Implement `send_request()` |
| `api/request_pipeline.py` | เพิ่ม `_intercept_vision_fallback()` + helpers |
| `tests/` | เทสใหม่ (ดูด้านล่าง) |

## Testing

- **Unit:** `_has_image_content()` กรณีผสม text/image, empty messages
- **Unit:** `_inject_image_analysis()` — ตรวจสอบว่า image blocks ถูกแทนที่, text blocks คงเดิม, structure ถูกต้อง
- **Unit:** `ProviderModelInfo` กับ `supports_vision=True/False/None`
- **Unit:** การค้นหา vision fallback mapping
- **Integration (mocked):** Interceptor ทำงานเมื่อมีรูป + non-vision model, ไม่ทำงานเมื่อ model รองรับ vision, ไม่ทำงานเมื่อไม่มีรูป
- **Integration (mocked):** Vision fallback ล้ม → pipeline ผ่านไปโดยไม่ crash
- **Integration (mocked):** `send_request()` (non-streaming) คืน text จาก OpenAI-style response

## ข้อที่ยังเปิด / Edge Cases

1. **ผู้ใช้หลายคน / หลาย conversation:** Vision fallback เป็น per-request (stateless) ไม่มี shared state problem
2. **Media type:** รองรับ `base64` และ `url` image sources ส่งเฉพาะ `image_url` type ไปยัง vision fallback
3. **หลายรูปใน message เดียว:** ใช้ analysis text block เดียว ถ้ามี N รูป analysis รวมอยู่ใน block เดียว
4. **User text + รูปใน message เดียวกัน:** ส่วน text ของ user message จะอยู่เหมือนเดิม ข้างๆ analysis ที่ถูกแทรกเข้าไป
5. **Cost:** แต่ละ request ที่มีรูป + non-vision model = 2 API calls แทน 1 call
6. **Performance:** Vision fallback เพิ่ม latency ~1-3 วิ ก่อนที่โมเดลหลักจะเริ่ม stream
