# Báo cáo so sánh ReACT và Reflexion Agent

Báo cáo này tổng hợp kết quả so sánh, phân tích failure modes, ước tính chi phí và thời gian chạy của **ReAct Agent** và **Reflexion Agent** trên tập dữ liệu gồm **150 câu hỏi** trích xuất từ tập kiểm thử chuẩn HotpotQA distractor (file `data/hotpot_150.json`).

---

## 1. Bảng so sánh ReACT và Reflexion Agent

| Tiêu chí so sánh | ReAct Agent | Reflexion Agent | Phân tích chênh lệch |
| :--- | :--- | :--- | :--- |
| **Độ chính xác (Exact Match - EM)** | **86.0%** (129/150) | **98.0%** (147/150) | **+12.0%** (Reflexion vượt trội nhờ khả năng tự sửa lỗi) |
| **Số lần thử trung bình (Avg Attempts)**| 1.0 (cố định) | 1.2533 | +0.2533 lần thử (chỉ lặp lại khi Evaluator chấm Sai) |
| **Số lượng Token trung bình / Câu** | 1,699.64 tokens | 2,188.98 tokens | **+28.8%** (+489.34 tokens do prompt lặp & reflection memory) |
| **Thời gian phản hồi / Câu (Avg Latency)**| 1,056.35 ms | 1,321.35 ms | **+25.1%** (+265.0 ms do phải gọi nhiều vòng LLM hơn) |
| **Cơ chế sửa lỗi (Error Correction)** | Không có. Trả lời ngay sau lượt suy nghĩ và hành động đầu tiên. | Có. Sử dụng **Evaluator** để chấm điểm và **Reflector** viết nhật ký tự suy ngẫm (`reflection_memory`) để định hướng cho lượt thử kế tiếp. |
| **Cơ chế Adaptive Attempts** | Không áp dụng. | Áp dụng (Tự động tăng số lần thử tối đa dựa theo độ khó: Dễ = 1, Trung bình = 3, Khó = 5). |
| **Điểm mạnh** | - Tốc độ phản hồi nhanh.<br>- Chi phí token và thời gian chạy tối ưu.<br>- Cấu trúc đơn giản, dễ vận hành. | - Độ chính xác tiệm cận tuyệt đối (98% trên tập dữ liệu khó).<br>- Tránh được bẫy thông tin gây nhiễu (distractor).<br>- Tự nhận biết lỗi lập luận. |
| **Điểm yếu** | - Dễ gặp lỗi dừng sớm (incomplete_multi_hop).<br>- Dễ bị đánh lạc hướng bởi các passage gây nhiễu mang thông tin tương đồng. | - Tiêu tốn nhiều tài nguyên token hơn.<br>- Latency cao hơn đối với các câu hỏi sai ở lượt đầu.<br>- Nguy cơ lặp vô hạn nếu không có điều kiện dừng tốt. |

---

## 2. Bảng ước tính Chi phí & Thời gian chạy (150 câu hỏi Golden Test Set)

Giá sử dụng API Gemini 2.5 Flash thực tế:
- **Input Token Cost**: $0.075 / 1,000,000 tokens ($0.000075 / 1k tokens)
- **Output Token Cost**: $0.300 / 1,000,000 tokens ($0.000300 / 1k tokens)
- *Giả định phân bố dữ liệu trong bài Lab*: Input chiếm **85%** tổng số token, Output chiếm **15%** (đặc trưng của các agent QA là đọc tài liệu ngữ cảnh lớn và sinh ra câu trả lời ngắn).

### Bảng chi tiết chi phí và thời gian:

| Chỉ số ước tính | ReAct Agent | Reflexion Agent | Phụ trội của Reflexion |
| :--- | :--- | :--- | :--- |
| **Tổng số Token (150 câu)** | 254,946 tokens | 328,347 tokens | +73,401 tokens (+28.8%) |
| **Ước tính Input Tokens (85%)** | 216,704 tokens | 279,095 tokens | +62,391 tokens |
| **Ước tính Output Tokens (15%)** | 38,242 tokens | 49,252 tokens | +11,010 tokens |
| **Chi phí trung bình / Câu** | $0.000185 (0.0046 VNĐ) | $0.000238 (0.0060 VNĐ) | +$0.000053 (0.0014 VNĐ) |
| **Tổng chi phí cho 150 câu** | **~$0.0277** (~693 VNĐ) | **~$0.0357** (~893 VNĐ) | **+$0.0080** (+200 VNĐ) |
| **Thời gian phản hồi / Câu** | 1,056.35 ms | 1,321.35 ms | +265.00 ms (+25.1%) |
| **Tổng thời gian chạy (Running Time)** | **~158.45 giây** (~2.64 phút) | **~198.20 giây** (~3.3 phút) | **+39.75 giây** (+25.1%) |

### Đánh giá:
Sự chênh lệch về chi phí (~0.008 USD hay ~200 VNĐ cho 150 câu) và thời gian (~40 giây) là **hoàn toàn xứng đáng** để đổi lấy mức tăng độ chính xác **12% tuyệt đối** (từ 86% lên 98%). Ở các hệ thống production thực tế đòi hỏi độ chính xác cao, Reflexion là sự lựa chọn tối ưu hơn.

---

## 3. Phân tích Failure Modes & Cách Reflexion giải quyết

Dựa trên kết quả thống kê lỗi từ benchmark:

1. **Wrong Final Answer (Sai câu trả lời cuối cùng)**:
   - **ReAct**: Gặp 20 lỗi. Agent hoàn thành việc suy luận qua các bước nhưng lựa chọn thực thể hoặc giá trị cuối cùng sai do tài liệu gây nhiễu chứa thông tin gần giống.
   - **Reflexion**: Khắc phục triệt để (0 lỗi). Khi Evaluator nhận thấy kết quả không khớp với nhãn gold, Reflector sẽ chỉ ra điểm nhầm lẫn, giúp Actor tìm kiếm lại thông tin chính xác ở lượt sau.

2. **Entity Drift (Lệch hướng thực thể)**:
   - **ReAct**: Gặp 1 lỗi. Bị lạc hướng sang thực thể khác có tên tương tự.
   - **Reflexion**: Khắc phục triệt để (0 lỗi).

3. **Looping (Lặp vòng lặp)**:
   - **ReAct**: 0 lỗi (do chỉ chạy đúng 1 lần thử).
   - **Reflexion**: Xuất hiện 3 lỗi. Đây là failure mode duy nhất của Reflexion khi agent bị kẹt trong vòng lặp thử - sai liên tiếp do hướng suy luận cũ bị lưu trữ quá cứng nhắc hoặc prompt sửa đổi chưa đủ mạnh để bứt phá.

4. **Incomplete Multi-Hop (Chưa hoàn thành đủ bước nhảy suy luận)**:
   - ReAct thường bị dừng ngay sau bước tìm kiếm đầu tiên. Reflexion nhờ có `reflection_memory` lưu giữ chỉ dẫn *"phải tìm thêm bước tiếp theo"* nên đã giải quyết hoàn toàn lỗi này ở lượt thử thứ 2.
