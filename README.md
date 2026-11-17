# Elderly Voice Cloning (Gia An AIoT)

> Hệ thống tổng hợp và giả lập giọng nói người cao tuổi tiếng Việt đa vùng miền (Bắc – Trung – Nam) có kiểm soát đặc trưng âm học lão hóa (Presbyphonia) và hạn chế tối đa rủi ro bản quyền.

---

## 1. Giới thiệu & Tầm nhìn Dự án

Hệ thống **Gia An AIoT** hướng tới việc chăm sóc, bảo vệ và giám sát an toàn cho người cao tuổi thông qua thị giác máy tính và trí tuệ nhân tạo giọng nói (AI Voice & Routine). 

Trong thực tế, việc thu thập giọng nói của người cao tuổi gặp nhiều rào cản lớn:
- **Bản quyền & Pháp lý**: Cào dữ liệu từ YouTube, truyền hình, mạng xã hội tiềm ẩn rủi ro xâm phạm quyền tác giả và quyền riêng tư theo pháp luật bảo vệ dữ liệu cá nhân.
- **Dữ liệu khan hiếm**: Người cao tuổi (nhất là 70–80+ tuổi) ở các vùng quê ít tiếp cận thiết bị số, khó thu thập với số lượng lớn.
- **Ranh giới kỹ thuật**: Cần phân định rạch ròi giữa giọng nói nguồn phát sạch (close-talk) của người già với phần suy biến do phòng (far-field, echo, phòng rộng) mà kỹ sư xử lý âm thanh đảm nhiệm.

Dự án này triển khai pipeline tổng hợp giọng nói người già có kiểm soát (Controlled Synthetic Presbyphonia Pipeline) theo lộ trình chi tiết tại [`plan.md`](plan.md).

---

## 2. Cấu trúc Thư mục & Quy ước Đặt tên

Tất cả các file âm thanh được xuất tự động vào các thư mục riêng biệt theo từng hồ sơ người cao tuổi, chia theo 3 nhóm kịch bản rõ ràng:

```text
data/elderly_dataset/
├── manifest.jsonl                                      # Manifest chi tiết định dạng JSON Lines
├── metadata.csv                                        # Metadata UTF-8 BOM dùng cho Excel / Phân tích
│
├── Ong_Hai_Dang_50_tuoi_Mien_Nam/                      # Folder người già (Tên + Tuổi + Vùng miền)
│   ├── giong_noi_keu_cuu/                              # Kêu cứu khẩn cấp (té ngã, đau ngực, khó thở)
│   │   ├── ong_hai_dang_50t_keu_cuu_01_khan_cap.wav
│   │   ├── ong_hai_dang_50t_keu_cuu_02_bi_nga.wav
│   │   └── ...
│   ├── giong_sinh_hoat/                                # Giao tiếp thường nhật (hỏi thuốc, thời tiết)
│   │   ├── ong_hai_dang_50t_sinh_hoat_01_uong_thuoc.wav
│   │   ├── ong_hai_dang_50t_sinh_hoat_02_nhac_nho.wav
│   │   └── ...
│   └── giong_co_nhieu/                                 # Môi trường thực tế có tạp âm (TV, bếp, quạt)
│       ├── ong_hai_dang_50t_co_nhieu_01_tieng_tivi.wav
│       ├── ong_hai_dang_50t_co_nhieu_02_tieng_bep.wav
│       └── ...
│
├── Ba_Le_Thi_Mai_65_tuoi_Mien_Bac/
│   ├── giong_noi_keu_cuu/
│   ├── giong_sinh_hoat/
│   └── giong_co_nhieu/
│
├── Ong_Tran_Van_Phuoc_72_tuoi_Mien_Trung/
│   ├── giong_noi_keu_cuu/
│   ├── giong_sinh_hoat/
│   └── giong_co_nhieu/
│
├── Ba_Nguyen_Thi_Cuc_78_tuoi_Mien_Nam/
│   ├── giong_noi_keu_cuu/
│   ├── giong_sinh_hoat/
│   └── giong_co_nhieu/
│
└── Ong_Nguyen_Van_Hao_82_tuoi_Mien_Bac/
    ├── giong_noi_keu_cuu/
    ├── giong_sinh_hoat/
    └── giong_co_nhieu/
```

Chi tiết quy chuẩn đặt tên xem tại: [`docs/NAMING_CONVENTION.md`](docs/NAMING_CONVENTION.md).

---

## 3. Kiến trúc Kỹ thuật

```text
┌─────────────────┐       ┌──────────────────────┐       ┌─────────────────────┐
│  Kịch bản thoại │       │  ZeroTTS Vietnamese  │       │   Presbyphonia DSP  │
│  (prompts.yaml) │ ────> │  Neural Synthesis    │ ────> │  - Senile Tremor    │
└─────────────────┘       └──────────────────────┘       │  - Jitter & Shimmer │
                                                         │  - Breathiness / Air│
┌─────────────────┐       ┌──────────────────────┐       │  - Slower Tempo     │
│  Hồ sơ người già│       │  Acoustic Profiles   │ ────> │  - Pitch Shift      │
│ (speakers.yaml) │ ────> │ (acoustic_profiles)  │       └──────────┬──────────┘
└─────────────────┘       └──────────────────────┘                  │
                                                                    ▼
┌─────────────────┐       ┌──────────────────────┐       ┌─────────────────────┐
│ Export Manifest │ <──── │   Acoustic Metrics   │ <──── │  Noise Augmentation │
│ (JSONL / CSV)   │       │   (F0, Jitt, Shim)   │       │  (TV, Bếp, Quạt gió)│
└─────────────────┘       └──────────────────────┘       └─────────────────────┘
```

1. **Neural Base Synthesis**: Sử dụng mô hình ZeroTTS ONNX nội bộ (chạy offline 100%, không phụ thuộc API đám mây, độ trễ thời gian thực $\approx 1.5\times$ realtime).
2. **Presbyphonia DSP Processor**: Mô phỏng quá trình lão hóa thanh quản theo từng nấc tuổi:
   - **Nhóm 50–59 tuổi**: Hạ nhẹ cao độ, nhịp ổn định.
   - **Nhóm 60–69 tuổi**: Dây thanh âm giảm đàn hồi, tốc độ nói chậm lại 12%, xuất hiện độ khàn nhẹ.
   - **Nhóm 70–79 tuổi**: Run giọng thần kinh cơ (senile vocal tremor $4.5–5.5 \text{ Hz}$), hụt hơi (glottal leakage breathiness), ngắt nghỉ dài.
   - **Nhóm 80+ tuổi**: Độ bất ổn chu kỳ cao (Jitter $> 3.5\%$, Shimmer $> 7\%$), âm lượng nhỏ, ngắt quãng.
3. **Mô phỏng Tạp âm Môi trường (`giong_co_nhieu`)**:
   - Trộn âm có kiểm soát tỉ số tín hiệu trên nhiễu (SNR từ $6 \text{ dB}$ đến $12 \text{ dB}$) với các nguồn: tiếng tivi thời sự, tiếng xào nấu/bát đĩa trong bếp ăn, tiếng gió quạt máy/điều hòa, tiếng xe cộ ngoài đường, và độ vang phòng xa mic (reverb far-field).

---

## 4. Hướng dẫn Cài đặt & Sử dụng

### 4.1. Cài đặt Môi trường

```bash
# Clone repository
git clone git@github.com:AnhDuybugde/elderly-voice-cloning.git
cd elderly-voice-cloning

# Cài đặt thư viện phụ thuộc
pip install -r requirements.txt
```

### 4.2. Chạy Kiểm thử Đơn vị

```bash
./run_tests.sh
```

### 4.3. Sinh Toàn bộ Dataset

```bash
# Sinh trọn bộ dataset (mặc định 24,000 Hz WAV mono)
python3 tools/generate_dataset.py

# Hoặc chỉ sinh cho một người cụ thể (ví dụ: Ông Hải Đăng)
python3 tools/generate_dataset.py --speaker-id spk_nam_01

# Sinh riêng cho một phân loại kịch bản
python3 tools/generate_dataset.py --category-id giong_noi_keu_cuu
```

### 4.4. Kiểm tra Tính toàn vẹn Dataset

```bash
python3 tools/verify_dataset.py
```

### 4.5. Phân tích Âm học Từng File

```bash
python3 tools/analyze_audio.py data/elderly_dataset/Ong_Hai_Dang_50_tuoi_Mien_Nam/giong_noi_keu_cuu/ong_hai_dang_50t_keu_cuu_01_khan_cap.wav
```

---

## 5. Lộ trình Triển khai (Bám sát `plan.md`)

- [x] **Giai đoạn 0**: Thống nhất spec thu thập, mẫu văn bản consent, chuẩn ma trận phủ 3 miền và quy chuẩn ranh giới với dev far-field ([`docs/SPEC_GIAI_DOAN_0.md`](docs/SPEC_GIAI_DOAN_0.md)).
- [x] **Giai đoạn 1**: Thiết lập bộ đo âm học chuẩn (F0, Jitter, Shimmer, HNR, speech rate) và pipeline baseline tín hiệu Presbyphonia ([`docs/ACOUSTIC_BENCHMARK.md`](docs/ACOUSTIC_BENCHMARK.md)).
- [x] **Giai đoạn 2**: Tích hợp engine tổng hợp ZeroTTS tiếng Việt nội bộ kèm adapter voice conversion.
- [x] **Giai đoạn 3 & 4**: Sinh dữ liệu quy mô lớn có kiểm soát, tổ chức thư mục tường minh, sinh kịch bản kêu cứu/sinh hoạt/có nhiễu kèm manifest JSONL & CSV.
- [ ] **Giai đoạn 5**: Nghiệm thu tương quan phân phối âm học khi tiếp nhận dữ liệu thu âm tình nguyện viên thực tế.

---

## 6. Bản quyền & Giấy phép

Dự án được bảo hộ nội bộ phục vụ hệ thống chăm sóc người cao tuổi Gia An. Mã nguồn tuân thủ giấy phép MIT. Toàn bộ âm thanh mẫu sinh ra tuân thủ các quy định bảo vệ dữ liệu và không chứa thông tin định danh trái phép.
