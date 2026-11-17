# Elderly Voice Cloning (Gia An AIoT) — Version 3.0

> Hệ thống tổng hợp và giả lập giọng nói người cao tuổi tiếng Việt đa vùng miền (Bắc – Trung – Nam) đạt độ tự nhiên cao, có kiểm soát đặc trưng âm học lão hóa (Presbyphonia) và tuân thủ tuyệt đối các quy định về bản quyền.

---

## 📚 Obsidian Knowledge Vault

Dự án đã tích hợp sẵn thư mục tri thức **[`vault/`](vault/)** tương thích hoàn toàn với phần mềm [Obsidian](https://obsidian.md). Bạn chỉ cần mở Obsidian và trỏ tới thư mục `vault/` để duyệt tài liệu trực quan qua biểu đồ Graph View:

- **[`vault/00_INDEX.md`](vault/00_INDEX.md)**: Bản đồ tri thức tổng quan (Map of Content).
- **[`vault/01_PROJECT_OVERVIEW.md`](vault/01_PROJECT_OVERVIEW.md)**: Sứ mệnh dự án, bài toán AI Voice trong Gia An AIoT và rào cản bản quyền.
- **[`vault/02_ARCHITECTURE_AND_TECH.md`](vault/02_ARCHITECTURE_AND_TECH.md)**: Kiến trúc ZeroTTS, nội suy không gian vector latent, bộ lọc organic analog warmth.
- **[`vault/03_DATASET_AND_ROSTER.md`](vault/03_DATASET_AND_ROSTER.md)**: Chi tiết ma trận 12 hồ sơ người cao tuổi (Bắc, Trung, Nam từ 50–84 tuổi).
- **[`vault/04_ACOUSTIC_UPGRADE_NOTES.md`](vault/04_ACOUSTIC_UPGRADE_NOTES.md)**: Nhật ký nâng cấp âm thanh v2.0 (nguyên nhân v1 bị "giọng máy" và giải pháp khắc phục).
- **[`vault/05_HOW_TO_RUN_AND_EXTEND.md`](vault/05_HOW_TO_RUN_AND_EXTEND.md)**: Sổ tay hướng dẫn lập trình viên, lệnh CLI và cách thêm hồ sơ mới.
- **[`vault/06_ROADMAP_AND_COMPLIANCE.md`](vault/06_ROADMAP_AND_COMPLIANCE.md)**: Đối chiếu lộ trình `plan.md`, pháp lý bản quyền và ranh giới với dev far-field.
- **[`vault/07_V3_HUMANIZE_ENGINE.md`](vault/07_V3_HUMANIZE_ENGINE.md)**: v3.0 — engine lão hoá WORLD, danh tính riêng từng cụ, calibration, QC gate và kết quả đo.

---

## 1. Cấu Trúc Thư Mục Dữ Liệu Thực Tế

Toàn bộ các file âm thanh được chia theo từng thư mục riêng biệt của từng cụ, đặt tên tường minh không dấu:

```text
data/elderly_dataset/
├── manifest.jsonl                                      # Manifest chi tiết (JSON Lines)
├── metadata.csv                                        # Metadata Excel UTF-8 BOM
│
├── reports/                                            # dataset_report.md, speaker_similarity.json
│
├── Ong_Hai_Dang_50_tuoi_Mien_Nam/                      # Nam 50t - TP.HCM
│   ├── ong_hai_dang_50t_cau_chao_gia_an.wav
│   ├── giong_noi_keu_cuu/ong_hai_dang_50t_keu_cuu_01_khan_cap_v0.wav ... _v2.wav
│   ├── giong_sinh_hoat/...
│   └── giong_co_nhieu/...                              # bản sạch; bản trộn nhiễu (--with-noise) ở _noisy/
├── Ba_Le_Thi_Mai_62_tuoi_Mien_Bac/                      # Nữ 62t - Hà Nội
│   └── ba_le_thi_mai_62t_cau_chao_gia_an.wav
├── Ong_Tran_Van_Phuoc_71_tuoi_Mien_Trung/              # Nam 71t - Thừa Thiên Huế
│   └── ong_tran_van_phuoc_71t_cau_chao_gia_an.wav
├── Ba_Nguyen_Thi_Cuc_76_tuoi_Mien_Nam/                  # Nữ 76t - Cần Thơ (Miền Tây)
│   └── ba_nguyen_thi_cuc_76t_cau_chao_gia_an.wav
├── Ong_Nguyen_Van_Hao_82_tuoi_Mien_Bac/                 # Nam 82t - Thái Bình
│   └── ong_nguyen_van_hao_82t_cau_chao_gia_an.wav
├── Ba_Hoang_Thi_Lan_67_tuoi_Mien_Trung/                # Nữ 67t - Nghệ An
│   └── ba_hoang_thi_lan_67t_cau_chao_gia_an.wav
├── Ong_Vo_Van_Khang_58_tuoi_Mien_Trung/                # Nam 58t - Quảng Nam / Đà Nẵng
│   └── ong_vo_van_khang_58t_cau_chao_gia_an.wav
├── Ba_Phan_Thi_Hong_54_tuoi_Mien_Bac/                  # Nữ 54t - Hải Phòng
│   └── ba_phan_thi_hong_54t_cau_chao_gia_an.wav
├── Ong_Bui_Dinh_Khoi_65_tuoi_Mien_Bac/                 # Nam 65t - Nam Định
│   └── ong_bui_dinh_khoi_65t_cau_chao_gia_an.wav
├── Ba_Truong_Thi_Tuyet_73_tuoi_Mien_Trung/             # Nữ 73t - Quảng Trị
│   └── ba_truong_thi_tuyet_73t_cau_chao_gia_an.wav
├── Ong_Lam_Quoc_Bao_77_tuoi_Mien_Nam/                  # Nam 77t - Bến Tre
│   └── ong_lam_quoc_bao_77t_cau_chao_gia_an.wav
└── Ba_Doan_Thi_Nuong_84_tuoi_Mien_Nam/                 # Nữ 84t - Tiền Giang
    └── ba_doan_thi_nuong_84t_cau_chao_gia_an.wav
```

Câu mẫu phát âm kiểm chuẩn:
> **"Xin chào Gia An, Gia An có nghe rõ tôi nói không?"**

---

## 2. Version 3.0 — Humanize giọng theo đúng độ tuổi & từng người

v2.0 cho ra 12 file nghe như **2 người** (mọi cụ ông dùng `huuduc`, gần như mọi cụ bà dùng `kimoanh`; cosine WavLM-SV 0.95–0.99) và **không có khác biệt theo tuổi** (đo lại bằng Praat: tốc độ nói, jitter… gần như phẳng từ 50 đến 84 tuổi). v3.0 sửa tận gốc:

| Thành phần | v3.0 |
|---|---|
| **Engine lão hoá** | `src/synthesis/world_aging.py` — vocoder **WORLD** tách F0 / phổ / aperiodicity: F0 theo tuổi & giới (giữ 6 thanh), jitter & shimmer **theo từng chu kỳ thanh môn**, tremor 4–7 Hz trôi tự nhiên, hụt hơi, warp formant, vocal fry cuối câu, đứt tiếng, hít hơi trước câu |
| **Nhịp nói** | `src/synthesis/prosody.py` — time-map không đều: chậm theo tuổi (≈4.1 → 2.8 âm tiết/s), khoảng lặng kéo dài hơn lời nói |
| **Danh tính riêng** | `speakers.yaml`: `voice_mix` (1–3 voice pack) + `voice_traits` (khàn, run, F0, formant, tốc độ…), trait thiếu được lấy mẫu tất định theo `speaker.id` |
| **Văn bản** | `text_humanizer.py`: từ vựng 3 miền cho cả 15 câu, ngập ngừng tăng theo tuổi; manifest lưu `utterance_text` (nhãn) + `spoken_text` |
| **Sắc thái** | `tone_modifiers`: hoảng loạn / đau / khó thở / bình thản… đổi F0, nhịp, hụt hơi |
| **Đo đạc** | Praat (Parselmouth): F0, jitter, shimmer, HNR, CPPS; tốc độ nói, ngắt nghỉ; faster-whisper CER; WavLM-SV |
| **Calibration** | `tools/calibrate_aging.py` khớp chỉ số **đo được** với mục tiêu y văn từng ô giới tính × tuổi |
| **QC gate** | Ngoài dải / CER > 15% / clipping → sinh lại seed mới (≤ 3 lần); `qc_pass`, `qc_reasons` trong manifest |

Kết quả đo và giới hạn còn lại: xem [`vault/07_V3_HUMANIZE_ENGINE.md`](vault/07_V3_HUMANIZE_ENGINE.md) và `data/elderly_dataset/reports/dataset_report.md`.

---

## 3. (Lịch sử) Các Nâng Cấp Trong Version 2.0

1. **Loại bỏ méo pha Phase-Vocoder**: Loại bỏ hoàn toàn `librosa.effects.pitch_shift` gây tiếng rè kim loại dạng robot.
2. **Nội suy không gian Latent Vector**: Sử dụng phép tổ hợp tuyến tính trên không gian vector đặc trưng người nói $\mathbf{z} \in \mathbb{R}^{10 \times 768}$ của ZeroTTS. Mỗi cụ có một âm sắc riêng biệt, mượt mà và tự nhiên từ mạng nơ-ron gốc.
3. **Độ phân giải Studio 48,000 Hz**: Tăng cường từ 24kHz lên 48kHz chuẩn phòng thu âm, dải tần thoáng và giàu chi tiết.
4. **Organic Presbyphonia & Analog Warmth EQ**:
   - Tăng cường cộng hưởng lồng ngực (+1.5 dB quanh 300 Hz).
   - Bộ lọc bướm bậc 1 mượt mà làm dịu dải cao, mô phỏng sinh lý thanh quản lão hóa tự nhiên.
   - Run thanh quản bằng nhiễu hồng 1/f thay vì sóng sin máy móc.
   - Bão hòa mềm analog $\tanh(x)$ làm tròn biên độ, triệt tiêu clipping.

---

## 4. Hướng Dẫn Sử Dụng Nhanh

```bash
# Cài đặt
pip install -r requirements.txt

# Sinh toàn bộ câu mẫu chào Gia An cho 12 cụ
python3 tools/generate_dataset.py

# Sinh toàn bộ dataset: 12 cụ × 15 câu × 3 biến thể (+ QC gate)
python3 tools/generate_dataset.py --full --variants 3

# Kiểm tra tính toàn vẹn + báo cáo xu hướng theo tuổi / QC / độ khác biệt giữa các cụ
python3 tools/verify_dataset.py --report

# (Khi đổi mục tiêu âm học hoặc có dữ liệu người thật) hiệu chỉnh lại engine
python3 tools/calibrate_aging.py

# Chạy test suite
./run_tests.sh
```
