# BỘ ĐO VÀ TIÊU CHUẨN ÂM HỌC NGƯỜI GIÀ (ACOUSTIC BENCHMARK)

Tài liệu hướng dẫn các phép đo âm học khách quan (Objective Acoustic Metrics) nhằm thẩm định mức độ "giống thật" của giọng người già tổng hợp theo Giai đoạn 1 và Giai đoạn 5 trong `plan.md`.

---

## 1. Các Đặc Trưng Sinh Lý Lão Hóa Thanh Quản (Presbyphonia)

Khi cơ thể già đi, hệ thống thanh âm trải qua quá trình thoái hóa sinh lý:
1. **Dây thanh âm mỏng đi và teo cơ (Vocal Fold Atrophy)**: Khiến hai mép dây thanh khép không kín hoàn toàn khi phát âm, tạo ra luồng khí rò rỉ (breathiness / turbulence).
2. **Mất độ đàn hồi biểu mô (Loss of Elasticity)**: Làm chu kỳ rung động giữa các dao động không còn đều đặn, biểu hiện qua **Jitter** tăng cao.
3. **Biến động biên độ thanh âm (Amplitude Perturbation)**: Biên độ sóng âm giữa các chu kỳ dao động thất thường, biểu hiện qua **Shimmer** tăng cao.
4. **Run giọng sinh lý (Senile Vocal Tremor)**: Tần số dao động run thần kinh cơ ở dải $4.0 - 6.5 \text{ Hz}$.
5. **Dịch chuyển cao độ (Pitch Shift)**:
   - Ở nam giới: F0 có xu hướng giảm ở tuổi 50–70, sau đó có thể tăng nhẹ ở tuổi 80+ do teo cơ.
   - Ở nữ giới: F0 giảm rõ rệt (trầm hơn từ $10 - 25 \text{ Hz}$) do sự biến đổi hormone và giữ nước màng đệm.

---

## 2. Tiêu Chuẩn Định Lượng Kiểm Định (Gate Metrics)

| Chỉ số âm học | Ký hiệu | Người trẻ / Trung niên | Người già 60–75 tuổi | Người già 75+ tuổi | Phương pháp đo |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **Tần số cơ bản F0 (Nam)** | $F_0$ | $110 - 140 \text{ Hz}$ | $95 - 125 \text{ Hz}$ | $115 - 145 \text{ Hz}$ | pYIN / Autocorrelation |
| **Tần số cơ bản F0 (Nữ)** | $F_0$ | $190 - 230 \text{ Hz}$ | $150 - 185 \text{ Hz}$ | $140 - 175 \text{ Hz}$ | pYIN / Autocorrelation |
| **Tỷ lệ Jitter (Local)** | Jitt | $< 1.0\%$ | $1.5\% - 3.5\%$ | $3.0\% - 5.5\%$ | $\frac{\frac{1}{N-1}\sum\|T_i - T_{i+1}\|}{\frac{1}{N}\sum T_i}$ |
| **Tỷ lệ Shimmer (Local)** | Shim | $< 2.5\%$ | $3.5\% - 7.0\%$ | $6.0\% - 10.5\%$ | $\frac{\frac{1}{N-1}\sum\|A_i - A_{i+1}\|}{\frac{1}{N}\sum A_i}$ |
| **Tỷ số Hài trên Nhiễu** | HNR | $> 18.0 \text{ dB}$ | $11.0 - 16.0 \text{ dB}$ | $9.0 - 14.0 \text{ dB}$ | Cross-correlation ratio |
| **Tốc độ phát âm** | Syllables/s | $4.5 - 6.0$ | $3.2 - 4.2$ | $2.5 - 3.5$ | Audio duration / text syllables |

---

## 3. Cổng Nghiệm Thu "Đủ Thật" (Acceptance Gate)

Một file audio giọng người già tổng hợp được coi là đạt chuẩn khi:
- $F_0$ nằm trong ngưỡng sinh lý theo giới tính và độ tuổi khai báo.
- Jitter và Shimmer nằm trong dải của người già ($\text{Jitter} \ge 1.2\%$, $\text{Shimmer} \ge 2.5\%$).
- Tốc độ phát âm không bị quá nhanh như giọng đọc thông tin của người trẻ.
- Không bị digital clipping ($\text{Peak} < -0.5 \text{ dBFS}$).
- Không có hiện tượng hallucination (nuốt chữ hoặc lặp âm bất thường).
