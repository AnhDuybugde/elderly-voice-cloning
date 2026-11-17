Với phân vai như vậy, phần của bạn là **sinh giọng người già gần thật, có kiểm soát theo vùng miền, trên nền dữ liệu tình nguyện viên của đội thu thập**. Dưới đây là lộ trình theo giai đoạn. Tên model và phiên bản nên kiểm tra lại trước khi chốt, vì lĩnh vực này đổi rất nhanh.

## Nguyên tắc chốt trước

1. **Dữ liệu tình nguyện viên là nguồn chính**, đừng cào web. Nhờ đó bạn có consent rõ ràng, nhãn chuẩn (tuổi, giới, vùng) và tránh rủi ro pháp lý.
2. **Chia nhiệm vụ rõ với dev far-field.** Bạn xuất audio sạch (close-talk, 24 kHz trở lên), dev kia lo phần phòng/echo/khoảng cách/kênh điện thoại. Đừng tự thêm nhiễu và vang ở phía bạn, nếu không sẽ bị áp hai lần.
3. **Giữ synthetic và dữ liệu thật tách bạch** bằng metadata (`source=real|synth`, `region`, `gender`, `age_bin`, `speaker_id`, `ref_id`, `model_version`). Test case nào cũng phải báo cáo được riêng hai nhóm.

## Giai đoạn 0: Thống nhất spec với đội thu thập

Đây là bước quyết định chất lượng cả pipeline. Yêu cầu đội thu thập:
- **Thu âm**: ≥24 kHz, WAV/FLAC, không nén MP3, phòng yên tĩnh, mic cố định. Mỗi người **10–20 phút sạch** (đủ để fine-tune nếu cần) cộng thêm vài câu ngắn riêng làm prompt zero-shot.
- **Nội dung đọc**: câu cân bằng âm vị (có đủ 6 thanh điệu, các phụ âm cuối đặc trưng vùng), cộng một ít **nói tự nhiên** (kể chuyện), vì giọng đọc và giọng nói tự nhiên của người già khác nhau khá nhiều.
- **Metadata**: tuổi, giới, quê gốc và nơi sống lâu năm (người di cư hay lai giọng), tình trạng răng/sức khỏe nếu họ đồng ý khai.
- **Consent** ghi rõ: cho phép tạo giọng tổng hợp từ giọng họ, phạm vi dùng (nội bộ test), thời hạn lưu.
- **Ma trận phủ**: ít nhất Bắc / Trung (Thanh-Nghệ-Tĩnh, Huế, Quảng Nam-Đà Nẵng, Nam Trung Bộ) / Nam, mỗi vùng cả nam và nữ, nhóm tuổi 60–69, 70–79, 80+. Giọng Trung là chỗ model hay yếu nhất nên cần ưu tiên số lượng.

## Giai đoạn 1: Baseline và đo đạc 

Làm song song khi chờ dữ liệu:
- Dựng **bộ đo chuẩn** trên dữ liệu thật: F0, jitter, shimmer, HNR, tốc độ nói, tỉ lệ khoảng lặng và độ dài ngắt nghỉ (Parselmouth), embedding speaker (ECAPA hoặc WavLM), WER/CER bằng một ASR tiếng Việt.
- Tạo **baseline tín hiệu** từ giọng thường (làm chậm, đổi formant, thêm jitter/shimmer/breathiness bằng Praat hoặc WORLD). Baseline này rẻ, lặp lại được, và là mốc so sánh để biết TTS có thật sự đáng đầu tư không.
- Chọn sẵn **TTS/ASR dùng làm chuẩn đánh giá** và cố định phiên bản, tránh đo bằng thước thay đổi.

## Giai đoạn 2: Zero-shot và chọn model 

Thử nhanh các ứng viên trên cùng bộ prompt người thật:
- **F5-TTS (flow matching)** với checkpoint tiếng Việt. Kiểm tra model card, nguồn dữ liệu và nghe thử.
- **GPT-SoVITS** và **Seed-VC / RVC** (nếu cần kiểm soát nhịp và cảm xúc).
- Các model đa ngôn ngữ mới hơn nếu có hỗ trợ tiếng Việt thật sự (đừng tin danh sách ngôn ngữ trong tài liệu, tự thử).

Chấm mỗi ứng viên bằng bộ đo ở giai đoạn 1: speaker similarity, khoảng cách phân phối jitter/shimmer/HNR so với người thật cùng nhóm, WER (loại hallucination), cộng nghe mù 5–10 người. Kết quả này cho bạn quyết định dựa trên số liệu, không dựa trên cảm giác.

## Giai đoạn 3: Fine-tune theo vùng/giọng 

Đây là phần tăng "giống thật":
- **Fine-tune theo từng speaker** (GPT-SoVITS hoặc RVC) cho các giọng đại diện, đủ để mỗi ô trong ma trận vùng × giới × tuổi có vài giọng.
- **Fine-tune theo vùng miền**, ví dụ một F5-TTS/model nền được tinh chỉnh trên gộp dữ liệu từng vùng, rồi dùng prompt từng người. Giọng Trung thường cần nhiều dữ liệu hơn hoặc phải fine-tune riêng.
- Nếu dùng **Voice Conversion**: để người đọc cùng vùng (nhiều tuổi nhất có thể) thu các kịch bản, rồi chuyển timbre. Cách này giữ ngữ điệu và thanh điệu vùng miền tốt hơn TTS thuần.
- Giữ **tập giữ lại (held-out)** các speaker thật không đưa vào fine-tune, để đo xem model có tổng quát hóa hay chỉ nhớ.

## Giai đoạn 4: Sinh dữ liệu quy mô lớn có kiểm soát 

- Xây **kịch bản test** do bạn và đội test cùng chốt: câu lệnh, số, tên riêng, câu dài/ngắn, từ khó, câu có ngập ngừng.
- Sinh với **nhiều biến thể** mỗi câu: tốc độ, mức ngắt nghỉ, mức khàn (nếu model điều khiển được), vài seed khác nhau. Lưu tham số để truy ngược.
- **Lọc tự động**: bỏ mẫu có WER cao, speaker similarity thấp, clipping, lặp/nuốt từ, độ dài bất thường. Giữ lại số lượng thô và số lượng đã lọc để báo cáo tỉ lệ pass.
- Xuất bản gốc sạch cho dev far-field, kèm manifest (JSONL/CSV).

## Giai đoạn 5: Kiểm định "đủ thật" 

Cổng nghiệm thu nên định lượng:
- Phân phối đặc trưng âm học của synthetic **nằm trong khoảng của người thật** cùng nhóm (không cần trùng, nhưng không lệch hẳn).
- Hệ thống của bạn cho **kết quả tương quan** giữa synthetic và người thật (ví dụ xếp hạng lỗi theo vùng/tuổi giống nhau). Nếu synthetic dễ hơn người thật rõ rệt, nó đang đánh lừa bạn rằng hệ thống tốt hơn thực tế.
- Nghe mù: người nghe không phân biệt được hoặc ít nhất chấm "tuổi giọng" gần với nhãn.
- Báo cáo **các chỗ synthetic chưa làm được** (phát âm kém rõ, hụt hơi giữa câu, run nặng) thay vì giấu đi, để đội test không kết luận quá mức.

## Rủi ro cần lường

- **Thiên lệch về giọng Bắc/Nam** do dữ liệu nền của model, nên đo riêng theo vùng.
- **Lai giọng**: người sinh ở vùng này sống lâu ở vùng khác, cần nhãn rõ.
- **Overfit một vài speaker**: số speaker thật quá ít thì synthetic chỉ là "vài người nhân bản", ít đa dạng hơn nhìn bề ngoài.
- **Bảo mật**: model clone của từng tình nguyện viên nên lưu nội bộ, hạn chế truy cập, không phát tán, và xóa theo thời hạn đã hứa trong consent.
