# 03. Ma Trận 12 Hồ Sơ Người Cao Tuổi & Cấu Trúc Dữ Liệu

*Liên kết:* [[00_INDEX]] | [[01_PROJECT_OVERVIEW]] | [[02_ARCHITECTURE_AND_TECH]] | [[05_HOW_TO_RUN_AND_EXTEND]]

---

## 1. Ma Trận Cân Bằng Hồ Sơ (Roster Matrix)

Hệ thống đã thiết lập danh sách **12 hồ sơ người cao tuổi** với sự cân bằng tuyệt đối:
- **Giới tính**: 6 Nam (50%) — 6 Nữ (50%).
- **Độ tuổi**: Trải dài từ 50 tuổi đến 84 tuổi (50s, 60s, 70s, 80s+).
- **Vùng miền**: 4 Miền Bắc (33.3%) — 4 Miền Trung (33.3%) — 4 Miền Nam (33.3%).

| ID | Danh xưng & Họ tên | Giới | Tuổi | Nhóm tuổi | Vùng miền | Phương ngữ / Tỉnh thành | Tên Thư Mục Lưu Trữ |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- | :--- |
| `spk_01` | **Ông Hải Đăng** | Nam | 50 | 50–59 | Miền Nam | TP. Hồ Chí Minh | `Ong_Hai_Dang_50_tuoi_Mien_Nam` |
| `spk_02` | **Bà Lê Thị Mai** | Nữ | 62 | 60–69 | Miền Bắc | Hà Nội | `Ba_Le_Thi_Mai_62_tuoi_Mien_Bac` |
| `spk_03` | **Ông Trần Văn Phước**| Nam | 71 | 70–79 | Miền Trung| Thừa Thiên Huế | `Ong_Tran_Van_Phuoc_71_tuoi_Mien_Trung`|
| `spk_04` | **Bà Nguyễn Thị Cúc** | Nữ | 76 | 70–79 | Miền Nam | Cần Thơ / Tây Nam Bộ | `Ba_Nguyen_Thi_Cuc_76_tuoi_Mien_Nam` |
| `spk_05` | **Ông Nguyễn Văn Hảo**| Nam | 82 | 80+ | Miền Bắc | Thái Bình | `Ong_Nguyen_Van_Hao_82_tuoi_Mien_Bac` |
| `spk_06` | **Bà Hoàng Thị Lan** | Nữ | 67 | 60–69 | Miền Trung| Nghệ An | `Ba_Hoang_Thi_Lan_67_tuoi_Mien_Trung` |
| `spk_07` | **Ông Võ Văn Khang** | Nam | 58 | 50–59 | Miền Trung| Quảng Nam - Đà Nẵng | `Ong_Vo_Van_Khang_58_tuoi_Mien_Trung` |
| `spk_08` | **Bà Phan Thị Hồng** | Nữ | 54 | 50–59 | Miền Bắc | Hải Phòng | `Ba_Phan_Thi_Hong_54_tuoi_Mien_Bac` |
| `spk_09` | **Ông Bùi Đình Khởi** | Nam | 65 | 60–69 | Miền Bắc | Nam Định | `Ong_Bui_Dinh_Khoi_65_tuoi_Mien_Bac` |
| `spk_10` | **Bà Trương Thị Tuyết**| Nữ | 73 | 70–79 | Miền Trung| Quảng Trị | `Ba_Truong_Thi_Tuyet_73_tuoi_Mien_Trung`|
| `spk_11` | **Ông Lâm Quốc Bảo** | Nam | 77 | 70–79 | Miền Nam | Bến Tre | `Ong_Lam_Quoc_Bao_77_tuoi_Mien_Nam` |
| `spk_12` | **Bà Đoàn Thị Nương** | Nữ | 84 | 80+ | Miền Nam | Tiền Giang | `Ba_Doan_Thi_Nuong_84_tuoi_Mien_Nam` |

---

## 2. Câu Mẫu Kiểm Chuẩn (Benchmark Greeting Sentence)

Để đánh giá chất lượng giọng nói một cách khách quan trên toàn bộ 12 người, hệ thống sinh ra cùng một câu phát âm chuẩn hóa:

> **"Xin chào Gia An, Gia An có nghe rõ tôi nói không?"**

- **Đối với người 50–70 tuổi**: Giữ nguyên nhịp điệu tự nhiên, dõng dạc, rõ ràng.
- **Đối với người từ 70–79 tuổi**: Thêm ngắt nghỉ nhịp thở tự nhiên:  
  `"Xin chào Gia An... Gia An có nghe rõ tôi nói không?"`
- **Đối với người từ 80 tuổi trở lên**: Thêm độ chậm rãi và run ngắt giọng:  
  `"Xin chào Gia An... Gia An... có nghe rõ tôi nói không?"`

---

## 3. Cấu Trúc Thư Mục Thực Tế Trên Đĩa

```text
data/elderly_dataset/
├── manifest.jsonl                                      # Manifest theo từng dòng JSON
├── metadata.csv                                        # Metadata Excel UTF-8 BOM
│
├── Ong_Hai_Dang_50_tuoi_Mien_Nam/
│   └── ong_hai_dang_50t_cau_chao_gia_an.wav
│
├── Ba_Le_Thi_Mai_62_tuoi_Mien_Bac/
│   └── ba_le_thi_mai_62t_cau_chao_gia_an.wav
│
├── Ong_Tran_Van_Phuoc_71_tuoi_Mien_Trung/
│   └── ong_tran_van_phuoc_71t_cau_chao_gia_an.wav
│
├── Ba_Nguyen_Thi_Cuc_76_tuoi_Mien_Nam/
│   └── ba_nguyen_thi_cuc_76t_cau_chao_gia_an.wav
│
├── Ong_Nguyen_Van_Hao_82_tuoi_Mien_Bac/
│   └── ong_nguyen_van_hao_82t_cau_chao_gia_an.wav
│
├── Ba_Hoang_Thi_Lan_67_tuoi_Mien_Trung/
│   └── ba_hoang_thi_lan_67t_cau_chao_gia_an.wav
│
├── Ong_Vo_Van_Khang_58_tuoi_Mien_Trung/
│   └── ong_vo_van_khang_58t_cau_chao_gia_an.wav
│
├── Ba_Phan_Thi_Hong_54_tuoi_Mien_Bac/
│   └── ba_phan_thi_hong_54t_cau_chao_gia_an.wav
│
├── Ong_Bui_Dinh_Khoi_65_tuoi_Mien_Bac/
│   └── ong_bui_dinh_khoi_65t_cau_chao_gia_an.wav
│
├── Ba_Truong_Thi_Tuyet_73_tuoi_Mien_Trung/
│   └── ba_truong_thi_tuyet_73t_cau_chao_gia_an.wav
│
├── Ong_Lam_Quoc_Bao_77_tuoi_Mien_Nam/
│   └── ong_lam_quoc_bao_77t_cau_chao_gia_an.wav
│
└── Ba_Doan_Thi_Nuong_84_tuoi_Mien_Nam/
    └── ba_doan_thi_nuong_84t_cau_chao_gia_an.wav
```

---

## 4. Đặc Tả Kỹ Thuật Từng File Âm Thanh

- **Định dạng**: RIFF WAVE (WAV).
- **Audio Codec**: Microsoft PCM 16-bit Integer.
- **Tần số lấy mẫu (Sample Rate)**: **48,000 Hz** (chuẩn phòng thu Studio Fidelity).
- **Số kênh (Channels)**: 1 (Mono Close-talk).
- **Headroom biên độ**: $-1.5 \text{ dBFS}$ (đỉnh tuyệt đối $\le 0.84$), đảm bảo không bao giờ bị méo biên độ kỹ thuật số (digital clipping) khi qua các mạch lọc khuếch đại của loa thông minh Gia An.
