# QUY ƯỚC ĐẶT TÊN THƯ MỤC VÀ FILE ÂM THANH

Để đảm bảo toàn bộ hệ thống Gia An AIoT, nhóm kiểm thử, và pipeline huấn luyện máy học có thể tích hợp tự động mà không bị nhầm lẫn dữ liệu, dự án quy chuẩn cấu trúc thư mục và đặt tên file như sau.

---

## 1. Cấu trúc Thư mục Tổng thể

```text
data/elderly_dataset/
├── manifest.jsonl                                      # Manifest chi tiết định dạng JSON Lines
├── metadata.csv                                        # Metadata UTF-8 BOM dùng cho Excel / Data Analyst
│
├── Ong_Hai_Dang_50_tuoi_Mien_Nam/                      # Folder người già (Tên + Tuổi + Vùng miền)
│   ├── giong_noi_keu_cuu/                              # Folder con: Kêu cứu khẩn cấp
│   │   ├── ong_hai_dang_50t_keu_cuu_01_khan_cap.wav
│   │   ├── ong_hai_dang_50t_keu_cuu_02_bi_nga.wav
│   │   └── ...
│   ├── giong_sinh_hoat/                                # Folder con: Giao tiếp sinh hoạt
│   │   ├── ong_hai_dang_50t_sinh_hoat_01_uong_thuoc.wav
│   │   ├── ong_hai_dang_50t_sinh_hoat_02_nhac_nho.wav
│   │   └── ...
│   └── giong_co_nhieu/                                 # Folder con: Môi trường có tạp âm
│       ├── ong_hai_dang_50t_co_nhieu_01_tieng_tivi.wav
│       ├── ong_hai_dang_50t_co_nhieu_02_tieng_bep.wav
│       └── ...
│
├── Ba_Le_Thi_Mai_65_tuoi_Mien_Bac/
│   ├── giong_noi_keu_cuu/
│   ├── giong_sinh_hoat/
│   └── giong_co_nhieu/
│
└── Ong_Tran_Van_Phuoc_72_tuoi_Mien_Trung/
    ├── giong_noi_keu_cuu/
    ├── giong_sinh_hoat/
    └── giong_co_nhieu/
```

---

## 2. Quy tắc Đặt tên Thư mục Người già

Định dạng thư mục cấp 1:
$$\text{<Danh\_Xung>\_<Ho\_Va\_Ten>\_<So\_Tuoi>\_tuoi\_<Vung\_Mien>}$$

- **Danh xưng**: `Ong` (Ông) hoặc `Ba` (Bà).
- **Họ và tên**: Viết hoa chữ cái đầu từng từ, nối bằng dấu gạch dưới `_`, không dấu tiếng Việt.
- **Tuổi**: Số nguyên, tiếp sau là `_tuoi`.
- **Vùng miền**: `Mien_Bac`, `Mien_Trung`, hoặc `Mien_Nam`.

*Ví dụ:*
- `Ong_Hai_Dang_50_tuoi_Mien_Nam`
- `Ba_Le_Thi_Mai_65_tuoi_Mien_Bac`
- `Ong_Tran_Van_Phuoc_72_tuoi_Mien_Trung`

---

## 3. Quy tắc Đặt tên Thư mục Con (Phân loại Kịch bản)

Mỗi thư mục người già bắt buộc chứa chính xác 3 thư mục con:
1. `giong_noi_keu_cuu`: Âm thanh tình huống khẩn cấp (té ngã, đau đớn, khó thở, yêu cầu cấp cứu).
2. `giong_sinh_hoat`: Âm thanh thường nhật (nhắc uống thuốc, kiểm tra giờ, điều khiển thiết bị, hỏi thời tiết).
3. `giong_co_nhieu`: Âm thanh trong môi trường bị nhiễu (tiếng tivi, tiếng bếp ăn, tiếng quạt gió, tiếng vang phòng xa mic).

---

## 4. Quy tắc Đặt tên Từng File Âm thanh

Định dạng file:
$$\text{<speaker\_slug>\_<age>t\_<category\_prefix>\_<index>\_<slug\_noi\_dung>.wav}$$

- Tất cả viết thường, nối bằng dấu gạch dưới `_`, không dấu.
- `<speaker_slug>`: Tên viết thường (vd: `ong_hai_dang`).
- `<age>t`: Số tuổi kèm chữ cái `t` (vd: `50t`, `65t`, `72t`).
- `<category_prefix>`: `keu_cuu`, `sinh_hoat`, hoặc `co_nhieu`.
- `<index>`: Số thứ tự 2 chữ số (`01`, `02`, `03`...).
- `<slug_noi_dung>`: Mô tả ngắn gọn nội dung/tình huống của câu nói.

*Ví dụ:*
- `ong_hai_dang_50t_keu_cuu_01_khan_cap.wav`
- `ong_hai_dang_50t_keu_cuu_02_bi_nga.wav`
- `ong_hai_dang_50t_sinh_hoat_01_uong_thuoc.wav`
- `ong_hai_dang_50t_co_nhieu_01_tieng_tivi.wav`
- `ba_le_thi_mai_65t_keu_cuu_01_khan_cap.wav`

---

## 5. Cấu trúc Metadata Manifest

Mỗi file âm thanh được định danh và theo dõi bằng một bản ghi trong `manifest.jsonl` và `metadata.csv` với các trường:
- `sample_id`: Mã định danh duy nhất (vd: `spk_nam_01_giong_noi_keu_cuu_kc_01`).
- `file_name`: Tên file âm thanh.
- `relative_path`: Đường dẫn tương đối từ gốc dataset.
- `speaker_id`, `speaker_name`, `age`, `age_bin`, `gender`, `region`.
- `category`: Thư mục kịch bản.
- `utterance_text`: Nội dung câu nói bằng chữ tiếng Việt có dấu.
- `intent`: Ý định câu thoại (vd: `HELP`, `REMINDER_QUERY`, `DEVICE_CONTROL`).
- `noise_type` & `snr_db`: Thông tin tạp âm và tỷ số tín hiệu trên nhiễu.
- `duration_sec`, `sample_rate`, `channels`: Thông số kỹ thuật file.
- `f0_mean_hz`, `jitter_pct`, `shimmer_pct`, `hnr_db`: Chỉ số âm học đo đạc.
- `source`: `synthetic` hoặc `real`.
- `model_version`: Phiên bản thuật toán sinh giọng.
