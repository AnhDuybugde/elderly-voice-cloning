# 05. Sổ Tay Lập Trình Viên & Hướng Dẫn Thực Thi

*Liên kết:* [[00_INDEX]] | [[02_ARCHITECTURE_AND_TECH]] | [[03_DATASET_AND_ROSTER]] | [[06_ROADMAP_AND_COMPLIANCE]]

---

## 1. Cài Đặt Môi Trường Nhanh

Hệ thống hoạt động trên Python 3.10+ (Linux / WSL2 / MacOS).

```bash
# Clone repository
git clone git@github.com:AnhDuybugde/elderly-voice-cloning.git
cd elderly-voice-cloning

# Cài đặt các thư viện cần thiết
pip install -r requirements.txt
```

---

## 2. Các Lệnh Thực Thi Chính (CLI Usage)

### 2.1. Sinh Dữ Liệu Câu Mẫu Kiểm Chuẩn (Benchmark Greetings)
Lệnh này sẽ duyệt qua danh sách 12 cụ trong `configs/speakers.yaml` và sinh câu chào:
`"Xin chào Gia An, Gia An có nghe rõ tôi nói không?"`
vào từng thư mục tương ứng.

```bash
python3 tools/generate_dataset.py
```

### 2.2. Sinh Toàn Bộ Dataset Kịch Bản (v3.0)
12 cụ × 15 câu (kêu cứu / sinh hoạt / có nhiễu) × 3 biến thể + câu chào ≈ 552 file sạch, có QC gate:

```bash
python3 tools/generate_dataset.py --full --variants 3            # ~75 phút trên CPU
python3 tools/generate_dataset.py --full --with-noise            # + bản trộn nhiễu cho nhóm giong_co_nhieu (thư mục _noisy/)
python3 tools/generate_dataset.py --full --skip-qc               # nhanh, bỏ ASR/QC/speaker-similarity
```

### 2.3. Sinh Riêng Cho Một Vài Người
Manifest được **gộp** (bản ghi của các cụ khác vẫn giữ nguyên):

```bash
python3 tools/generate_dataset.py --full --speakers spk_05_bac_hao spk_12_nam_nuong
```

### 2.4. Hiệu Chỉnh Engine Lão Hoá (Calibration)
Chạy lại khi sửa `target` trong `configs/acoustic_profiles.yaml` hoặc khi có dữ liệu người thật:

```bash
python3 tools/calibrate_aging.py            # ghi mục `calibrated:`
python3 tools/calibrate_aging.py --dry-run  # chỉ in kết quả
```

### 2.5. Bài Nghe Mù (Blind Listening Test)
```bash
python3 tools/make_listening_test.py --per-speaker 3 --pairs 20     # tạo data/listening_test/
python3 tools/make_listening_test.py --score data/listening_test/answer_sheet.csv --pairs-sheet data/listening_test/pair_sheet.csv
```

### 2.6. Kiểm Định Toàn Vẹn Dataset & Manifest
Kiểm tra từng file âm thanh trên đĩa: định dạng WAV, sample rate 48kHz, mono, biên độ an toàn không clipping, và tính khớp nối 100% giữa file thật với `manifest.jsonl` và `metadata.csv`.

```bash
python3 tools/verify_dataset.py            # toàn vẹn file & manifest
python3 tools/verify_dataset.py --report   # + reports/dataset_report.md (xu hướng theo tuổi, QC, độ khác biệt giữa các cụ)
```

### 2.7. Phân Tích Chỉ Số Âm Học Chi Tiết Một File
Trích xuất $F_0$, Jitter, Shimmer, HNR, CPPS, tốc độ nói, ngắt nghỉ (Praat) và tuỳ chọn CER:

```bash
python3 tools/analyze_audio.py --gender nam --text "Xin chào Gia An, Gia An có nghe rõ tôi nói không?" --asr \
    data/elderly_dataset/Ong_Hai_Dang_50_tuoi_Mien_Nam/ong_hai_dang_50t_cau_chao_gia_an.wav
```

### 2.8. Chạy Kiểm Thử Tự Động (Unit Tests)
Bộ test tự động kiểm tra tính tương thích cấu hình, engine nơ-ron, DSP và bộ tạo nhiễu:

```bash
./run_tests.sh
```

---

## 3. Hướng Dẫn Mở Rộng: Thêm Một Hồ Sơ Người Cao Tuổi Mới

Để thêm một cụ ông hoặc cụ bà mới, bạn chỉ cần mở file `configs/speakers.yaml` và thêm một khối cấu hình mà **không cần phải sửa bất kỳ dòng code Python nào**:

```yaml
  - id: "spk_13_trung_minh"
    name: "Ong_Nguyen_Cong_Minh"
    display_name: "Ông Nguyễn Công Minh"
    gender: "nam"
    age: 79
    age_bin: "70_79"
    region: "mien_trung"
    region_display: "Miền Trung (Đà Nẵng)"
    sub_region: "da_nang"
    folder_name: "Ong_Nguyen_Cong_Minh_79_tuoi_Mien_Trung"
    base_voice: "huuduc"
    secondary_voice: "giahuy"
    blend_ratio: 0.80
    cfg_scale: 1.22
    temperature: 0.72
    # v3.0: pha nhiều giọng (nên chọn giọng chủ đạo KHÁC các cụ đã có để tránh trùng danh tính)
    voice_mix: {quangminh: 0.5, huuduc: 0.5}
    # v3.0: dấu vân tay — trait bỏ trống sẽ được lấy mẫu tất định trong dải nhóm tuổi
    voice_traits: {hoarseness: 0.6, tremor_severity: 0.5, f0_offset_st: -0.5}
    prosody_text: "Xin chào Gia An... Gia An có nghe rõ tôi nói không?"
    profile_notes: "Cụ ông 79 tuổi Đà Nẵng, giọng trầm, phong thái từ tốn."
```

Sau đó chỉ cần chạy:
```bash
python3 tools/generate_dataset.py --full --speakers spk_13_trung_minh
python3 tools/verify_dataset.py --report   # kiểm tra cụ mới không trùng giọng cụ khác (mục 4 của báo cáo)
```

> [!NOTE]
> **Ý nghĩa `voice_traits`** — `hoarseness` (0–1): khàn + hụt hơi + jitter/shimmer; `tremor_severity` (0–1): độ run; `tremor_rate_hz` (4–7); `f0_offset_st`: cao/thấp hơn mức chuẩn của nhóm tuổi (bán cung); `formant_warp` (<1 = giọng "dày", khoang miệng dài hơn); `speech_rate_factor`: nhanh/chậm hơn mức chuẩn; `pitch_range_scale` (≥0.85): biên độ ngữ điệu; `spectral_tilt_db_oct` (âm = giọng yếu, tối).
Hệ thống sẽ tự động tạo thư mục, sinh file WAV chất lượng cao và cập nhật bản ghi vào manifest!
