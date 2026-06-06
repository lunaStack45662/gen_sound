---
name: audio-mix
description: >
  Hướng dẫn AI mix voiceover + nhạc nền (BGM) cho video chữa lành tiếng Việt.
  Kỹ thuật: EQ carving, sidechain ducking tỉ lệ, volume balance, fade out.
  Đảm bảo giọng đọc nổi bật, nhạc nền hỗ trợ KHÔNG đánh nhau.
  Kèm test/verify tự động kiểm tra chất lượng mix.
compatibility: "requires: python3, numpy, scipy, soundfile, imageio-ffmpeg"
---

# Audio Mix — Trộn Voiceover + Nhạc Nền Cho Video Chữa Lành

> **Vấn đề**: Ghép voiceover + nhạc nền → 2 track "đánh nhau", nghe mệt.
> **Mục tiêu**: Giọng đọc nổi bật, nhạc nền hỗ trợ, bổ sung nhau.

---

## 1. Nguyên Tắc Mix (Hard Rules)

| ID | Rule | Nếu vi phạm |
|----|------|-------------|
| **M1** | Voiceover LUÔN là "ngôi sao" — nhạc nền chỉ hỗ trợ | Người nghe không hiểu nội dung |
| **M2** | EQ khoét mid (300-3kHz) trên BGM → nhường chỗ cho giọng | Giọng bị "chìm" trong nhạc |
| **M3** | Sidechain duck TỈ LỆ (không on/off) — nhạc giảm theo giọng, KHÔNG tắt hẳn | Nghe "lag", "pump" khó chịu |
| **M4** | BGM volume = voiceover peak × 10^(dB/20), mặc định -18dB | Nhạc át giọng hoặc quá nhỏ |
| **M5** | Fade out 3s cuối video — nhạc mờ dần, tạo cảm giác kết | Kết đột ngột, hụt hẫng |
| **M6** | Attack 200ms + Release 1000ms cho sidechain duck | Transition giật, không mượt |
| **M7** | BGM KHÔNG có lời (vocal) — cạnh tranh với voiceover | 2 giọng "đánh nhau" |
| **M8** | Normalize peak ≤ 0.95 sau khi mix | Clipping, âm thanh bị vỡ |

---

## 2. Pipeline Mix

```
Voiceover WAV ──────────────────────────┐
                                         ├──→ mix_voiceover_bgm() → mixed.wav
Nhạc nền (BGM) ─→ analyze → process_bgm → sidechain_duck ──┘
                                          ↓
                                   verify_mix() → 5 checks
                                          ↓
                                   mux_to_video() → final.mp4
```

### 2.1. Script chính

File: `adding_audio_to_video/mix_audio.py`

**Chạy CLI:**
```powershell
$env:PYTHONIOENCODING="utf-8"
python adding_audio_to_video\mix_audio.py --bgm duong/dan/nhac_nen.mp3
```

**Hoặc import:**
```python
from adding_audio_to_video.mix_audio import mix_and_mux
mix_and_mux(
    video_in="input/video/clip.mp4",
    voiceover_path="outputs/voiceover_21s.wav",
    bgm_path="duong/dan/bgm.mp3",
    video_out="outputs/final_with_bgm.mp4",
    bgm_db=-18,
)
```

### 2.2. Các bước xử lý BGM

| Bước | Function | Mô tả |
|------|----------|-------|
| 1 | `analyze_audio(path)` | Đọc BGM: duration, peak, RMS, tần số, cảnh báo |
| 2 | `process_bgm(bgm, voiceover, sr)` | Mono → resample → trim/loop → EQ carve mid → chỉnh volume -18dB |
| 3 | `sidechain_duck(bgm, voiceover, sr)` | Duck TỈ LỆ: giọng to → nhạc giảm ~50%, giọng nhỏ → giảm ít, im → 100% |
| 4 | `mix_voiceover_bgm(vo, bgm, sr)` | Trộn 2 track + normalize + fade out 3s |
| 5 | `verify_mix(mixed, voiceover, sr)` | 5 checks: clipping, voice dominant, BGM fills gaps, fade out |
| 6 | `mux_to_video(video, wav, out)` | Ghép vào video: `-c:v copy`, AAC 192k, 44.1kHz, stereo |

---

## 3. Test / Verify — Kiểm Tra Chất Lượng Mix

### 3.1. 5 bài test tự động (`verify_mix()`)

| # | Check | Pass khi | Fail khi |
|---|-------|----------|----------|
| 1 | **No clipping** | peak < 0.99 | peak ≥ 0.99 (âm thanh vỡ) |
| 2 | **Has audio** | RMS > 0.01 | RMS ≤ 0.01 (toàn silence) |
| 3 | **Voice dominant** | BGM thêm < 30% năng lượng ở vùng giọng | BGM thêm > 30% (nhạc át) |
| 4 | **BGM fills gaps** | RMS ở gap > 0.005 | RMS ≤ 0.005 (gap im lặng) |
| 5 | **Fade out** | RMS cuối < 50% RMS đầu | Cuối vẫn to như đầu |

### 3.2. Kết quả mẫu

```
==================================================
  Verify Mix
==================================================
  ✅  No clipping: peak=0.8800
  ✅  Has audio: rms=0.0823
  ✅  Voice dominant: BGM adds 12% to voice regions
  ✅  BGM fills gaps: gap rms=0.0156
  ✅  Fade out end: end_rms=0.0234 vs start_rms=0.0891

  Kết quả: 5/5 passed
==================================================
```

### 3.3. Troubleshooting

| Fail | Nguyên nhân | Cách sửa |
|------|-------------|----------|
| **Voice dominant** ❌ | BGM quá to hoặc nhiều mid | Giảm `--bgm-db` xuống -22, hoặc tăng EQ carve |
| **BGM fills gaps** ❌ | Duck quá sâu, nhạc tắt hẳn ở gap | Tăng `gain_min` (hiện 0.5) hoặc giảm DUCK_DEPTH_DB |
| **Fade out** ❌ | Video quá ngắn (< 6s) hoặc fade_sec quá nhỏ | Giảm FADE_OUT_SEC hoặc bỏ qua check này |
| **No clipping** ❌ | Voiceover peak quá cao | Giảm TARGET_PEAK trong voiceover script |

---

## 4. Chọn Nhạc Nền Phù Hợp

### 4.1. Tiêu chí

| Hợp ✅ | Không hợp ❌ |
|---------|--------------|
| Piano chậm, ít nốt | Nhạc có lời (vocal) |
| Ambient pad, drone | Beat nhanh / EDM |
| Lo-fi không lời | Nhạc quá dynamic (rock, metal) |
| Music box, strings nhẹ | Nhạc quá buồn (depressing) |

### 4.2. `analyze_audio()` cảnh báo tự động

- Nhạc quá ngắn (< 10s) → sẽ loop
- Nhạc quá nhỏ (peak < 0.01) → gần như silence
- Nhạc nhiều mid (> 50%) → cần EQ carve mạnh
- Nhạc quá dynamic (RMS > 0.3) → cần nén thêm

---

## 5. Tuning Parameters

| Tham số | Mặc định | Ý nghĩa | Khi nào chỉnh |
|---------|----------|---------|---------------|
| `BGM_TARGET_DB` | -18 | Volume BGM so với voice | -15 nếu nhạc quá nhỏ, -22 nếu quá to |
| `EQ_LOW` / `EQ_HIGH` | 300 / 3000 | Vùng tần số khoét trên BGM | Mở rộng nếu giọng vẫn chìm |
| `EQ_REDUCE_DB` | -4 | Cường độ khoét mid | -6 nếu cần khoét sâu hơn |
| `DUCK_DEPTH_DB` | -6 | Giảm nhạc tối đa khi giọng to | -8 nếu nhạc vẫn át, -4 nếu nhạc mất hẳn |
| `ATTACK_MS` | 200 | Thời gian nhạc bắt đầu giảm | Tăng nếu duck quá đột ngột |
| `RELEASE_MS` | 1000 | Thời gian nhạc hồi lại | Giảm nếu nhạc hồi quá chậm |
| `FADE_OUT_SEC` | 3.0 | Fade out cuối video | Tùy duration video |

---

## 6. Checklist Cuối

**Trước khi mix:**
- [ ] Voiceover WAV đã QA pass (test_voiceover.py)
- [ ] Nhạc nền KHÔNG có lời (vocal)
- [ ] `analyze_audio()` không có warning "is_suitable=False"

**Sau khi mix:**
- [ ] `verify_mix()` pass 5/5
- [ ] Nghe thử bằng tai: giọng rõ, nhạc không át
- [ ] Fade out cuối mượt, không cắt đột ngột
- [ ] Video output duration khớp video gốc
