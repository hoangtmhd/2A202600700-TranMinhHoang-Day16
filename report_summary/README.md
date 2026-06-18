# Thư mục tổng hợp báo cáo và Demo nhanh (Lab 16)

Thư mục này chứa các tài liệu so sánh, ước tính chi phí và mã nguồn giúp bạn kiểm thử nhanh chóng hai mô hình Agent: **ReAct Agent** và **Reflexion Agent** trên bộ dữ liệu golden test set (`data/hotpot_150.json`).

## Các thành phần trong thư mục
1. **`comparison_report.md`**: Bảng so sánh chi tiết giữa ReAct và Reflexion Agent, bảng tính toán chi phí (cost) dựa trên đơn giá API Gemini 2.5 Flash thực tế và phân tích các dạng lỗi thường gặp (failure modes).
2. **`run_demo.py`**: File Python chạy thử nghiệm trực tiếp và trực quan hóa kết quả so sánh bằng giao diện dòng lệnh (CLI) đẹp mắt thông qua thư viện `rich`.

---

## Hướng dẫn chạy Demo nhanh

### 1. Chuẩn bị môi trường
Hãy đảm bảo bạn đã điền API Key vào file `.env` ở thư mục gốc của dự án:
```env
GEMINI_API_KEY=your-api-key-here
```

Và cài đặt đầy đủ các thư viện cần thiết (nếu chưa):
```bash
pip install -r ../requirements.txt
```

### 2. Chạy thử nghiệm Demo
Mặc định, script sẽ chỉ chạy thử nghiệm với **3 mẫu đầu tiên** để giúp bạn kiểm tra kết quả ngay lập tức mà không phải chờ đợi lâu hay tốn nhiều API token.

Chạy lệnh sau tại thư mục gốc của dự án:
```bash
python report_summary/run_demo.py
```
*(Hoặc dùng prefix `rtk` nếu bạn sử dụng terminal có tích hợp: `rtk python report_summary/run_demo.py`)*

### 3. Các tuỳ chọn nâng cao
Bạn có thể tùy chỉnh số lượng mẫu chạy thử (từ 1 đến 150) và số lần thử tối đa (`max_attempts`) của Reflexion Agent bằng các tham số:

- Chạy thử với **5 mẫu**:
  ```bash
  python report_summary/run_demo.py --num-samples 5
  ```

- Chạy thử với **toàn bộ 150 mẫu** (Golden Test Set):
  ```bash
  python report_summary/run_demo.py --num-samples 150
  ```

- Thay đổi số lần thử tối đa của Reflexion thành **5 lần**:
  ```bash
  python report_summary/run_demo.py --reflexion-attempts 5
  ```

- Để xem tất cả các tùy chọn hỗ trợ:
  ```bash
  python report_summary/run_demo.py --help
  ```
