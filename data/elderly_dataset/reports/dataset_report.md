# Báo cáo dataset giọng người cao tuổi — `elderly_dataset`

- Số file sạch: **552**, số người nói: **12**
- Tổng thời lượng: **41.9 phút**
- Model version: zerotts-v3.0-world-aging
- Tỉ lệ pass QC: **90.0%** (497/552)
- Số mẫu phải sinh lại (retry): 167
- CER trung bình (faster-whisper): **6.1%**, median 5.7%, max 25.0%

## 1. Đặc trưng âm học theo giới tính × nhóm tuổi (Praat)

### Nam

| Nhóm tuổi | N | F0 (Hz) | Jitter (%) | Shimmer (%) | HNR (dB) | CPPS (dB) | Rate (syl/s) | Pause ratio |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 50_59 | 92 | 133.94 | 2.46 | 8.79 | 12.56 | 13.42 | 4.15 | 0.07 |
| 60_69 | 46 | 114.12 | 3.31 | 9.97 | 10.06 | 11.91 | 3.51 | 0.06 |
| 70_79 | 92 | 119.96 | 3.82 | 12.32 | 8.97 | 10.14 | 2.90 | 0.08 |
| 80_plus | 46 | 127.35 | 6.65 | 15.84 | 5.87 | 6.80 | 2.50 | 0.10 |

### Nữ

| Nhóm tuổi | N | F0 (Hz) | Jitter (%) | Shimmer (%) | HNR (dB) | CPPS (dB) | Rate (syl/s) | Pause ratio |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 50_59 | 46 | 212.24 | 1.62 | 7.05 | 16.82 | 13.97 | 4.18 | 0.07 |
| 60_69 | 92 | 183.78 | 2.00 | 8.85 | 15.40 | 12.27 | 3.64 | 0.08 |
| 70_79 | 92 | 174.71 | 3.14 | 11.72 | 12.67 | 9.85 | 3.13 | 0.10 |
| 80_plus | 46 | 156.49 | 4.80 | 14.88 | 10.49 | 7.39 | 2.57 | 0.14 |

## 2. Kiểm tra xu hướng lão hoá (50–59 → 80+)

- Nam · Jitter (%): 2.46 → 3.31 → 3.82 → 6.65 — tăng dần đều
- Nam · Shimmer (%): 8.79 → 9.97 → 12.32 → 15.84 — tăng dần đều
- Nam · HNR (dB): 12.56 → 10.06 → 8.97 → 5.87 — giảm dần đều
- Nam · CPPS (dB): 13.42 → 11.91 → 10.14 → 6.80 — giảm dần đều
- Nam · Rate (syl/s): 4.15 → 3.51 → 2.90 → 2.50 — giảm dần đều
- Nam · Pause ratio: 0.07 → 0.06 → 0.08 → 0.10 — đúng xu hướng (không đơn điệu)
- Nữ · Jitter (%): 1.62 → 2.00 → 3.14 → 4.80 — tăng dần đều
- Nữ · Shimmer (%): 7.05 → 8.85 → 11.72 → 14.88 — tăng dần đều
- Nữ · HNR (dB): 16.82 → 15.40 → 12.67 → 10.49 — giảm dần đều
- Nữ · CPPS (dB): 13.97 → 12.27 → 9.85 → 7.39 — giảm dần đều
- Nữ · Rate (syl/s): 4.18 → 3.64 → 3.13 → 2.57 — giảm dần đều
- Nữ · Pause ratio: 0.07 → 0.08 → 0.10 → 0.14 — tăng dần đều

## 3. Theo từng người nói

| Speaker | Tuổi | Giới | Vùng | N | F0 | Jitter | Shimmer | HNR | Rate | CER | Sim→centroid | QC pass |
|---|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Ông Hải Đăng | 50 | nam | mien_nam | 46 | 132.3 | 2.60 | 8.85 | 12.5 | 4.11 | 5.3% | 0.962 | 46/46 |
| Bà Phan Thị Hồng | 54 | nu | mien_bac | 46 | 212.2 | 1.62 | 7.05 | 16.8 | 4.18 | 5.7% | 0.964 | 46/46 |
| Ông Võ Văn Khang | 58 | nam | mien_trung | 46 | 135.6 | 2.32 | 8.72 | 12.6 | 4.18 | 5.5% | 0.970 | 43/46 |
| Bà Lê Thị Mai | 62 | nu | mien_bac | 46 | 186.1 | 1.93 | 8.69 | 16.1 | 3.50 | 4.1% | 0.976 | 46/46 |
| Ông Bùi Đình Khởi | 65 | nam | mien_bac | 46 | 114.1 | 3.31 | 9.97 | 10.1 | 3.51 | 3.8% | 0.967 | 46/46 |
| Bà Hoàng Thị Lan | 67 | nu | mien_trung | 46 | 181.5 | 2.07 | 9.00 | 14.7 | 3.79 | 6.9% | 0.971 | 44/46 |
| Ông Trần Văn Phước | 71 | nam | mien_trung | 46 | 116.4 | 3.86 | 12.48 | 9.1 | 2.82 | 6.0% | 0.962 | 42/46 |
| Bà Trương Thị Tuyết | 73 | nu | mien_trung | 46 | 168.3 | 2.94 | 11.05 | 12.4 | 3.25 | 8.3% | 0.976 | 43/46 |
| Bà Nguyễn Thị Cúc | 76 | nu | mien_nam | 46 | 181.1 | 3.34 | 12.39 | 12.9 | 3.01 | 6.2% | 0.978 | 37/46 |
| Ông Lâm Quốc Bảo | 77 | nam | mien_nam | 46 | 123.6 | 3.77 | 12.16 | 8.8 | 2.98 | 7.0% | 0.965 | 46/46 |
| Ông Nguyễn Văn Hảo | 82 | nam | mien_bac | 46 | 127.3 | 6.65 | 15.84 | 5.9 | 2.50 | 6.3% | 0.969 | 32/46 |
| Bà Đoàn Thị Nương | 84 | nu | mien_nam | 46 | 156.5 | 4.80 | 14.88 | 10.5 | 2.57 | 8.0% | 0.980 | 26/46 |

## 4. Độ khác biệt danh tính giữa các cụ (WavLM-SV cosine giữa centroid)

- Nam: cosine trung bình giữa các cặp = **0.916**, cao nhất = 0.980
- Nữ: cosine trung bình giữa các cặp = **0.941**, cao nhất = 0.995
- Cặp vượt ngưỡng cảnh báo 0.95: spk_01_nam_dang~spk_07_trung_khang (0.962), spk_01_nam_dang~spk_09_bac_khoi (0.961), spk_02_bac_mai~spk_04_nam_cuc (0.995), spk_02_bac_mai~spk_06_trung_lan (0.952), spk_02_bac_mai~spk_10_trung_tuyet (0.970), spk_03_trung_phuoc~spk_09_bac_khoi (0.980), spk_03_trung_phuoc~spk_11_nam_bao (0.980), spk_04_nam_cuc~spk_10_trung_tuyet (0.960), spk_06_trung_lan~spk_08_bac_hong (0.989), spk_06_trung_lan~spk_10_trung_tuyet (0.988), spk_08_bac_hong~spk_10_trung_tuyet (0.972), spk_09_bac_khoi~spk_11_nam_bao (0.976)
- Mốc tham chiếu: v2.0 có cosine 0.95–0.99 giữa các cặp cùng giới; các voice pack gốc khác nhau của ZeroTTS đo được 0.86–0.92.

## 5. Mẫu không qua QC

Lý do (đếm theo chỉ số): `shimmer_pct` × 43, `cer` × 13, `f0_mean_hz` × 1

- `Ong_Tran_Van_Phuoc_71_tuoi_Mien_Trung/giong_noi_keu_cuu/ong_tran_van_phuoc_71t_keu_cuu_03_kho_tho_v0.wav` — shimmer_pct=14.409 not in [4.0, 14.0]
- `Ong_Tran_Van_Phuoc_71_tuoi_Mien_Trung/giong_noi_keu_cuu/ong_tran_van_phuoc_71t_keu_cuu_03_kho_tho_v1.wav` — shimmer_pct=14.477 not in [4.0, 14.0]
- `Ong_Tran_Van_Phuoc_71_tuoi_Mien_Trung/giong_co_nhieu/ong_tran_van_phuoc_71t_co_nhieu_04_tieng_on_ngoai_duong_v1.wav` — cer=0.222 > 0.15
- `Ong_Tran_Van_Phuoc_71_tuoi_Mien_Trung/giong_co_nhieu/ong_tran_van_phuoc_71t_co_nhieu_04_tieng_on_ngoai_duong_v2.wav` — cer=0.178 > 0.15
- `Ba_Nguyen_Thi_Cuc_76_tuoi_Mien_Nam/giong_noi_keu_cuu/ba_nguyen_thi_cuc_76t_keu_cuu_02_bi_nga_v0.wav` — shimmer_pct=15.114 not in [4.0, 13.0]
- `Ba_Nguyen_Thi_Cuc_76_tuoi_Mien_Nam/giong_noi_keu_cuu/ba_nguyen_thi_cuc_76t_keu_cuu_02_bi_nga_v2.wav` — shimmer_pct=14.593 not in [4.0, 13.0]
- `Ba_Nguyen_Thi_Cuc_76_tuoi_Mien_Nam/giong_noi_keu_cuu/ba_nguyen_thi_cuc_76t_keu_cuu_03_kho_tho_v0.wav` — shimmer_pct=14.769 not in [4.0, 13.0]
- `Ba_Nguyen_Thi_Cuc_76_tuoi_Mien_Nam/giong_noi_keu_cuu/ba_nguyen_thi_cuc_76t_keu_cuu_03_kho_tho_v1.wav` — shimmer_pct=15.105 not in [4.0, 13.0]; cer=0.167 > 0.15
- `Ba_Nguyen_Thi_Cuc_76_tuoi_Mien_Nam/giong_noi_keu_cuu/ba_nguyen_thi_cuc_76t_keu_cuu_03_kho_tho_v2.wav` — shimmer_pct=13.695 not in [4.0, 13.0]
- `Ba_Nguyen_Thi_Cuc_76_tuoi_Mien_Nam/giong_noi_keu_cuu/ba_nguyen_thi_cuc_76t_keu_cuu_04_co_ai_khong_v0.wav` — shimmer_pct=15.522 not in [4.0, 13.0]
- `Ba_Nguyen_Thi_Cuc_76_tuoi_Mien_Nam/giong_noi_keu_cuu/ba_nguyen_thi_cuc_76t_keu_cuu_04_co_ai_khong_v2.wav` — shimmer_pct=13.605 not in [4.0, 13.0]
- `Ba_Nguyen_Thi_Cuc_76_tuoi_Mien_Nam/giong_sinh_hoat/ba_nguyen_thi_cuc_76t_sinh_hoat_05_chao_hoi_v0.wav` — shimmer_pct=13.616 not in [4.0, 13.0]
- `Ba_Nguyen_Thi_Cuc_76_tuoi_Mien_Nam/giong_co_nhieu/ba_nguyen_thi_cuc_76t_co_nhieu_02_tieng_bep_v1.wav` — shimmer_pct=13.33 not in [4.0, 13.0]; cer=0.171 > 0.15
- `Ong_Nguyen_Van_Hao_82_tuoi_Mien_Bac/giong_noi_keu_cuu/ong_nguyen_van_hao_82t_keu_cuu_01_khan_cap_v0.wav` — shimmer_pct=16.985 not in [5.0, 16.0]
- `Ong_Nguyen_Van_Hao_82_tuoi_Mien_Bac/giong_noi_keu_cuu/ong_nguyen_van_hao_82t_keu_cuu_02_bi_nga_v0.wav` — shimmer_pct=18.704 not in [5.0, 16.0]
- `Ong_Nguyen_Van_Hao_82_tuoi_Mien_Bac/giong_noi_keu_cuu/ong_nguyen_van_hao_82t_keu_cuu_02_bi_nga_v2.wav` — shimmer_pct=17.212 not in [5.0, 16.0]
- `Ong_Nguyen_Van_Hao_82_tuoi_Mien_Bac/giong_noi_keu_cuu/ong_nguyen_van_hao_82t_keu_cuu_03_kho_tho_v0.wav` — shimmer_pct=16.942 not in [5.0, 16.0]
- `Ong_Nguyen_Van_Hao_82_tuoi_Mien_Bac/giong_noi_keu_cuu/ong_nguyen_van_hao_82t_keu_cuu_03_kho_tho_v1.wav` — shimmer_pct=17.611 not in [5.0, 16.0]
- `Ong_Nguyen_Van_Hao_82_tuoi_Mien_Bac/giong_noi_keu_cuu/ong_nguyen_van_hao_82t_keu_cuu_03_kho_tho_v2.wav` — shimmer_pct=17.601 not in [5.0, 16.0]
- `Ong_Nguyen_Van_Hao_82_tuoi_Mien_Bac/giong_noi_keu_cuu/ong_nguyen_van_hao_82t_keu_cuu_05_goi_nguoi_nha_v0.wav` — shimmer_pct=16.514 not in [5.0, 16.0]
- `Ong_Nguyen_Van_Hao_82_tuoi_Mien_Bac/giong_sinh_hoat/ong_nguyen_van_hao_82t_sinh_hoat_05_chao_hoi_v0.wav` — shimmer_pct=16.276 not in [5.0, 16.0]
- `Ong_Nguyen_Van_Hao_82_tuoi_Mien_Bac/giong_sinh_hoat/ong_nguyen_van_hao_82t_sinh_hoat_05_chao_hoi_v1.wav` — shimmer_pct=16.957 not in [5.0, 16.0]
- `Ong_Nguyen_Van_Hao_82_tuoi_Mien_Bac/giong_co_nhieu/ong_nguyen_van_hao_82t_co_nhieu_02_tieng_bep_v0.wav` — shimmer_pct=16.284 not in [5.0, 16.0]
- `Ong_Nguyen_Van_Hao_82_tuoi_Mien_Bac/giong_co_nhieu/ong_nguyen_van_hao_82t_co_nhieu_04_tieng_on_ngoai_duong_v0.wav` — shimmer_pct=17.984 not in [5.0, 16.0]
- `Ong_Nguyen_Van_Hao_82_tuoi_Mien_Bac/giong_co_nhieu/ong_nguyen_van_hao_82t_co_nhieu_04_tieng_on_ngoai_duong_v1.wav` — shimmer_pct=16.472 not in [5.0, 16.0]
- `Ong_Nguyen_Van_Hao_82_tuoi_Mien_Bac/giong_co_nhieu/ong_nguyen_van_hao_82t_co_nhieu_05_keu_cuu_farfield_v1.wav` — shimmer_pct=17.509 not in [5.0, 16.0]
- `Ong_Nguyen_Van_Hao_82_tuoi_Mien_Bac/giong_co_nhieu/ong_nguyen_van_hao_82t_co_nhieu_05_keu_cuu_farfield_v2.wav` — shimmer_pct=17.24 not in [5.0, 16.0]
- `Ba_Hoang_Thi_Lan_67_tuoi_Mien_Trung/giong_noi_keu_cuu/ba_hoang_thi_lan_67t_keu_cuu_03_kho_tho_v2.wav` — shimmer_pct=13.234 not in [3.0, 11.0]
- `Ba_Hoang_Thi_Lan_67_tuoi_Mien_Trung/giong_co_nhieu/ba_hoang_thi_lan_67t_co_nhieu_05_keu_cuu_farfield_v0.wav` — cer=0.156 > 0.15
- `Ong_Vo_Van_Khang_58_tuoi_Mien_Trung/giong_noi_keu_cuu/ong_vo_van_khang_58t_keu_cuu_01_khan_cap_v2.wav` — f0_mean_hz=161.61 not in [95, 150]
- … và 25 mẫu khác (xem manifest.jsonl, trường `qc_reasons`)

## 6. Giới hạn đã biết (đọc trước khi dùng kết quả test)

- **Giọng vùng miền**: thanh điệu & phụ âm cuối địa phương phụ thuộc model ZeroTTS (thiên về giọng chuẩn). v3.0 chỉ thêm từ vựng địa phương (`spoken_text`); giọng vùng thật cần fine-tune/VC trên dữ liệu tình nguyện viên.
- **Mốc âm học lấy từ y văn**, chưa đối chiếu với người thật cùng nhóm. Khi có dữ liệu thật: cập nhật `target` và chạy lại `tools/calibrate_aging.py`.
- **Giọng nam gốc** đã có jitter/shimmer cao (~3% / ~8%) do codec; nhóm 50–69 nam vì vậy 'thô' hơn y văn.
- **Giọng nữ có tuổi** chỉ có 2 voice pack (`kimoanh`, `baotrang`): độ đa dạng nữ dựa nhiều vào DSP (F0, formant).
- **CER** đo bằng faster-whisper `small`; ASR hay nghe nhầm tên riêng "Gia An" kể cả trên giọng gốc, nên ngưỡng QC CER là 15%.
- Synthetic dễ hơn người thật ở: phát âm vẫn rõ (không mất răng/méo phụ âm), không có hụt hơi giữa từ, không ho/hắng giọng.
