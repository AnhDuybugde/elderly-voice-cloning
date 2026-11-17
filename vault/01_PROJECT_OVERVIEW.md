# 01. Tổng Quan & Sứ Mệnh Dự Án

*Liên kết:* [[00_INDEX]] | [[02_ARCHITECTURE_AND_TECH]] | [[03_DATASET_AND_ROSTER]] | [[06_ROADMAP_AND_COMPLIANCE]]

---

## 1. Giới thiệu Dự án

Dự án **Elderly Voice Cloning** là một thành phần trọng yếu trong hệ sinh thái **Gia An AIoT** — giải pháp nhà thông minh tích hợp trí tuệ nhân tạo nhằm hỗ trợ, giám sát an toàn và chăm sóc sức khỏe người cao tuổi tại Việt Nam.

Trong hệ thống Gia An, AI Voice đảm nhiệm hai phân hệ chính:
1. **Phát hiện cuộc gọi cứu hộ khẩn cấp (Emergency Voice Detection)**: Nhận biết tiếng kêu cứu khi người cao tuổi bị ngã, đột quỵ, đau tim, khó thở hoặc gọi tên người thân trong tình trạng nguy kịch.
2. **Trợ lý sinh hoạt thường nhật (Routine Assistant)**: Tương tác giọng nói tự nhiên để nhắc nhở uống thuốc, hỏi thăm thời tiết, kiểm soát thiết bị gia đình (đèn, quạt, bếp) và trò chuyện tâm sự.

---

## 2. Thách thức Cốt lõi & Lý do Cần Tổng hợp Giọng Người Già

### 2.1. Rào cản Pháp lý & Bản quyền (Copyright Risks)
- Thu thập dữ liệu âm thanh người già từ Internet (YouTube, podcast, truyền hình thời sự, mạng xã hội) tiềm ẩn nguy cơ nghiêm trọng về vi phạm bản quyền phát sóng và quyền hình ảnh cá nhân.
- Theo các quy định bảo vệ dữ liệu cá nhân (Nghị định 13/2023/NĐ-CP tại Việt Nam và chuẩn GDPR quốc tế), **dữ liệu giọng nói là dữ liệu sinh trắc học cá nhân nhạy cảm**. Việc khai thác khi chưa có văn bản đồng thuận (Informed Consent) có thể dẫn tới rủi ro pháp lý đình chỉ sản phẩm.

### 2.2. Sự Khan hiếm Dữ liệu Thực tế
- Người cao tuổi, đặc biệt là nhóm tuổi 70–80+ ở các vùng quê, ít khi sử dụng smartphone hay thu âm số.
- Việc tổ chức đội ngũ đến tận nhà thu âm tình nguyện viên đòi hỏi thời gian, chi phí lớn và chỉ thu thập được số lượng hạn chế.

### 2.3. Ranh giới Kỹ thuật Phức tạp
- Tiếng nói thực tế của người cao tuổi có đặc trưng sinh lý lão hóa thanh quản tự nhiên (**Presbyphonia**): dây thanh âm teo bớt, cơ khép không kín tạo luồng khí rò rỉ (breathiness), chu kỳ rung dao động thiếu đàn hồi (Jitter cao), biên độ thất thường (Shimmer cao), run giọng thần kinh cơ (senile tremor 4.5–6.0 Hz), và nhịp điệu phát âm chậm lại.
- Nếu không có bộ dữ liệu mẫu chuẩn close-talk sạch, kỹ sư xử lý âm thanh (far-field / DSP dev) không thể phân tách được đâu là hiện tượng do giọng người già thật và đâu là do phòng ốc gây ra méo tiếng.

---

## 3. Mục tiêu & Hướng tiếp cận Chiến lược

Dự án lựa chọn hướng đi **Tổng hợp Có Kiểm Soát (Controlled Synthetic Voice)**:
1. **Độc lập bản quyền**: Sử dụng mạng nơ-ron cục bộ nguồn mở (ZeroTTS) với kiến trúc latent vector continuous space.
2. **Bao phủ toàn diện ma trận vùng miền**: Bắc (Hà Nội, Hải Phòng, Nam Định, Thái Bình), Trung (Huế, Nghệ An, Quảng Nam, Quảng Trị), Nam (TP.HCM, Cần Thơ, Bến Tre, Tiền Giang) từ 50 đến 84 tuổi.
3. **Phân chia rõ ràng cấu trúc lưu trữ**: Mỗi người già có một thư mục riêng biệt, đặt tên chuẩn hóa không dấu, chứa các file âm thanh kiểm chuẩn và các nhóm kịch bản (kêu cứu, sinh hoạt, có nhiễu).
4. **Sẵn sàng tiếp nhận dữ liệu thật**: Hệ thống xây dựng sẵn cấu trúc metadata, adapter và benchmark gate để ngay khi đội thu thập bàn giao dữ liệu tình nguyện viên, pipeline có thể tiến hành fine-tune / voice conversion một cách liền mạch.
