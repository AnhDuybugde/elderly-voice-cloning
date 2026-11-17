# ĐẶC TẢ GIAI ĐOẠN 0: SPEC THU THẬP & BẢO VỆ BẢN QUYỀN

Tài liệu này xác định các nguyên tắc, tiêu chuẩn kỹ thuật và quy trình pháp lý phục vụ việc tạo giọng nói người già tiếng Việt đa vùng miền cho hệ thống Gia An AIoT.

---

## 1. Nguyên tắc Tránh Vi Phạm Bản Quyền (Copyright & Ethics)

1. **Nguồn dữ liệu hợp pháp**:
   - Nghiêm cấm cào dữ liệu âm thanh từ YouTube, TikTok, truyền hình, podcast hay mạng xã hội khi chưa có thỏa thuận.
   - Dữ liệu cơ sở (reference audio) chỉ dùng từ:
     - **Tình nguyện viên trực tiếp** có ký văn bản cam kết (Informed Consent).
     - **Mô hình tổng hợp giọng nói mở** (open-weights với giấy phép thương mại/nghiên cứu hợp lệ như Apache 2.0 / MIT) kết hợp thuật toán biến đổi sinh lý âm học lão hóa (Presbyphonia DSP).
2. **Quyền riêng tư & Quản lý dữ liệu người già**:
   - Dữ liệu clone giọng nói của tình nguyện viên được phân loại là **dữ liệu sinh trắc học nhạy cảm**.
   - Lưu trữ tại máy chủ nội bộ hoặc môi trường cách ly, có mã hóa lưu trữ (encryption at rest).
   - Tuân thủ điều khoản xóa vĩnh viễn dữ liệu khi hết thời hạn thỏa thuận hoặc khi người tham gia rút lại sự đồng ý.

---

## 2. Tiêu chuẩn Kỹ thuật Thu âm (Recording Spec)

Đội ngũ thu thập tình nguyện viên phải tuân thủ nghiêm ngặt các tham số sau:

| Thông số | Yêu cầu kỹ thuật | Ghi chú |
| :--- | :--- | :--- |
| **Định dạng file** | WAV hoặc FLAC (không nén) | Tuyệt đối không dùng MP3, AAC, OGG |
| **Sample Rate** | $\ge 24,000 \text{ Hz}$ (khuyến nghị 48,000 Hz) | Đảm bảo dải tần số đầy đủ cho DSP |
| **Bit Depth** | 16-bit hoặc 24-bit PCM | Chuẩn mono close-talk |
| **Microphone** | Mic định hướng (Cardioid / Supercardioid), cách miệng 15–20 cm | Cố định khoảng cách, dùng pop-filter |
| **Môi trường** | Phòng tĩnh ($\text{SNR} > 30 \text{ dB}$), độ vang thấp | Không bật quạt máy, tivi hoặc máy lạnh sát mic |
| **Thời lượng thu** | 10–20 phút sạch / người | Chia thành 30–50 câu ngắn |

---

## 3. Ma trận Phủ Vùng Miền & Nhóm Tuổi

Hệ thống phủ đủ 3 miền với trọng số ưu tiên giọng Miền Trung (nơi model STT/TTS thường nhận diện kém nhất):

| Vùng miền | Phương ngữ con (Sub-region) | Nhóm tuổi 50–59 | Nhóm tuổi 60–69 | Nhóm tuổi 70–79 | Nhóm tuổi 80+ |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Miền Bắc** | Hà Nội, Đồng bằng sông Hồng, Đông Bắc | Nam / Nữ | Nam / Nữ | Nam / Nữ | Nam / Nữ |
| **Miền Trung** | Thanh-Nghệ-Tĩnh, Thừa Thiên Huế, Quảng Nam - Đà Nẵng, Nam Trung Bộ | Nam / Nữ (Ưu tiên) | Nam / Nữ (Ưu tiên) | Nam / Nữ (Ưu tiên) | Nam / Nữ (Ưu tiên) |
| **Miền Nam** | TP. Hồ Chí Minh, Đông Nam Bộ, Tây Nam Bộ (Miền Tây) | Nam / Nữ | Nam / Nữ | Nam / Nữ | Nam / Nữ |

---

## 4. Phân công Ranh giới Kỹ thuật (Division of Labor)

- **Dev Voice Cloning (Nhánh hiện tại)**:
  - Chịu trách nhiệm tạo giọng người già phát âm tự nhiên, đúng phương ngữ vùng miền.
  - Xử lý các đặc trưng sinh lý lão hóa: run giọng, hụt hơi, nói chậm, giảm cao độ.
  - Xuất file âm thanh sạch chuẩn close-talk (24 kHz mono WAV).
- **Dev Far-field & Audio Preprocessing**:
  - Nhận audio sạch từ nhánh này.
  - Phụ trách giả lập hoặc xử lý thực tế: RIR (Room Impulse Response), tiếng vọng (echo), khoảng cách 3-5m từ camera/mic mảng, nén kênh điện thoại, và khử ồn thời gian thực.
  - Bộ phận sinh giọng tạo thêm thư mục `giong_co_nhieu` với SNR cố định để làm test case độc lập.
