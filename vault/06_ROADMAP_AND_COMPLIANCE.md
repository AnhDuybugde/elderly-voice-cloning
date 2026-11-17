# 06. Lộ Trình Phát Triển Plan.md & Pháp Lý Bản Quyền

*Liên kết:* [[00_INDEX]] | [[01_PROJECT_OVERVIEW]] | [[03_DATASET_AND_ROSTER]] | [[05_HOW_TO_RUN_AND_EXTEND]]

---

## 1. Đối Chiếu 6 Giai Đoạn Triển Khai Theo Plan.md

Lộ trình kỹ thuật của dự án bám sát 100% tài liệu định hướng [[plan.md]]:

| Giai đoạn | Trọng tâm công việc | Trạng thái hiện tại | Bàn giao kỹ thuật |
| :--- | :--- | :---: | :--- |
| **Giai đoạn 0** | Thống nhất Spec với đội thu thập, tiêu chuẩn văn bản Consent, ma trận phủ 3 miền, phân chia ranh giới với Dev Far-field. | **HOÀN THÀNH** | [`docs/SPEC_GIAI_DOAN_0.md`](file:///home/jloy/Desktop/gia-an/elderly-voice-cloning/docs/SPEC_GIAI_DOAN_0.md) |
| **Giai đoạn 1** | Xây dựng bộ đo âm học chuẩn ($F_0$, Jitter, Shimmer, HNR, speech rate) và pipeline baseline tín hiệu sinh lý lão hóa. | **HOÀN THÀNH** | [`docs/ACOUSTIC_BENCHMARK.md`](file:///home/jloy/Desktop/gia-an/elderly-voice-cloning/docs/ACOUSTIC_BENCHMARK.md) |
| **Giai đoạn 2** | Khảo sát và tích hợp engine ZeroTTS tiếng Việt nội bộ (ONNX offline), tối ưu hóa latent continuous blending. | **HOÀN THÀNH** | `src/synthesis/engine.py` |
| **Giai đoạn 3** | Tinh chỉnh giọng theo vùng miền (Bắc – Trung – Nam), phối hợp thanh điệu và phương ngữ đặc trưng. | **HOÀN THÀNH** | `configs/speakers.yaml` |
| **Giai đoạn 4** | Sinh dữ liệu quy mô lớn có kiểm soát, tổ chức thư mục riêng từng người, quy chuẩn đặt tên file và xuất manifest JSONL/CSV. | **HOÀN THÀNH (v2.0)** | `data/elderly_dataset/` |
| **Giai đoạn 5** | Kiểm định "đủ thật" qua đối chiếu phân phối đặc trưng âm học khi có dữ liệu thu âm tình nguyện viên thật. | **ĐANG CHỜ DATA THẬT** | Cổng nghiệm thu sẵn sàng tại `tools/verify_dataset.py` |

---

## 2. Ranh Giới Kỹ Thuật: Close-talk vs. Far-field

Một nguyên tắc sống còn được nhấn mạnh trong [[plan.md]] là **không áp dụng hiệu ứng suy biến âm thanh hai lần**:
- **Nhánh Voice Cloning (Nhánh của bạn)**:
  - Chỉ tập trung tạo ra âm thanh **sạch chuẩn close-talk (phát âm trực diện mic)**.
  - Xử lý các biến đổi thuộc về bản chất sinh học cơ thể người già: giảm độ đàn hồi dây thanh, rung thần kinh cơ, hụt hơi thanh môn, nói chậm, cộng hưởng khoang ngực.
  - Không tự tiện thêm tiếng vang dội phòng ngủ (room reverberation) hay tiếng méo méo kiểu mic mảng vào các audio chuẩn.
- **Nhánh Far-field & Signal Processing Dev**:
  - Nhận audio sạch close-talk từ nhánh này.
  - Phụ trách giả lập đáp ứng xung phòng (Room Impulse Response - RIR) ở khoảng cách 3–5m, góc đặt camera/mic mảng, tiếng vọng hồi tiếp (acoustic echo), và lọc nhiễu thời gian thực.
- **Thư mục đối chứng `giong_co_nhieu`**:
  - Được sinh ra với các kịch bản tạp âm cụ thể (TV, tiếng bếp ăn, quạt gió) ở các mức SNR định lượng (6–12 dB) để phục vụ test case độc lập của đội kiểm thử QA/QC.

---

## 3. Chính Sách Tuân Thủ Bản Quyền & Bảo Vệ Dữ Liệu Cá Nhân

1. **Tuyệt đối không sử dụng dữ liệu không phép**: Không cào audio từ Internet, YouTube, truyền hình để tránh vi phạm quyền tác giả và quyền liên quan.
2. **Quyền đồng thuận tham gia (Informed Consent)**: Dữ liệu của tình nguyện viên thật khi nạp vào hệ thống bắt buộc phải có văn bản thỏa thuận ghi rõ phạm vi sử dụng nội bộ để huấn luyện AI chăm sóc sức khỏe.
3. **Mã hóa & Hủy dữ liệu**: Các mô hình clone cá nhân hóa được lưu trữ cục bộ, có phân quyền truy cập, và cam kết hủy bỏ khi kết thúc thỏa thuận với người tham gia.
