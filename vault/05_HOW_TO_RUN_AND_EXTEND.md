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

### 2.2. Sinh Riêng Cho Một Người Cụ Thể
Ví dụ chỉ muốn sinh lại giọng cho Ông Hải Đăng hoặc Bà Lê Thị Mai:

```bash
# Theo mã speaker ID
python3 tools/generate_dataset.py --speaker-id spk_01_nam_dang
```

### 2.3. Kiểm Định Toàn Vẹn Dataset & Manifest
Kiểm tra từng file âm thanh trên đĩa: định dạng WAV, sample rate 48kHz, mono, biên độ an toàn không clipping, và tính khớp nối 100% giữa file thật với `manifest.jsonl` và `metadata.csv`.

```bash
python3 tools/verify_dataset.py
```

### 2.4. Phân Tích Chỉ Số Âm Học Chi Tiết Một File
Trích xuất $F_0$, Jitter, Shimmer, HNR và thời lượng:

```bash
python3 tools/analyze_audio.py data/elderly_dataset/Ong_Hai_Dang_50_tuoi_Mien_Nam/ong_hai_dang_50t_cau_chao_gia_an.wav
```

### 2.5. Chạy Kiểm Thử Tự Động (Unit Tests)
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
    prosody_text: "Xin chào Gia An... Gia An có nghe rõ tôi nói không?"
    profile_notes: "Cụ ông 79 tuổi Đà Nẵng, giọng trầm, phong thái từ tốn."
```

Sau đó chỉ cần chạy:
```bash
python3 tools/generate_dataset.py --speaker-id spk_13_trung_minh
```
Hệ thống sẽ tự động tạo thư mục, sinh file WAV chất lượng cao và cập nhật bản ghi vào manifest!
