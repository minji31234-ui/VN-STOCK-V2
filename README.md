# VN Stock Signal Scanner

Quét tín hiệu kỹ thuật cho cổ phiếu Việt Nam (VN30 và các nhóm ngành): MACD, KDJ, StochRSI, Bollinger, Ichimoku, Fibonacci, vùng giá, Elliott, volume, EMA, kèm backtest. Giá tính theo nghìn đồng. Chạy hoàn toàn trên GitHub.

## Cách hoạt động
GitHub Actions chạy `scripts/fetch_data.py`, tải nến bằng thư viện `vnstock` (thử nguồn KBS, nếu lỗi chuyển sang VCI), ghi thành JSON tĩnh rồi deploy cùng `index.html` lên GitHub Pages. Dữ liệu không được commit vào repo.

Lịch chạy: 10:30 và 15:30 (giờ Việt Nam) các ngày thứ Hai đến thứ Sáu. Lần chạy đầu mất khoảng 20–40 phút do phải giãn cách request để tránh bị giới hạn tần suất.

## Cài đặt
1. Tạo repo, upload toàn bộ thư mục này (kể cả `.github/workflows`).
2. Settings → Pages → Source: **GitHub Actions**.
3. Tab Actions → chạy workflow **Fetch data and deploy to GitHub Pages**.
4. Mở `https://<tên-github>.github.io/<tên-repo>/`.

## Danh sách mã và nhóm ngành
Sửa `watchlist.json`: mỗi nhóm là một danh sách mã, một mã có thể thuộc nhiều nhóm. Nhóm `VN30` tự lấy từ sàn mỗi lần chạy; nếu lấy lỗi sẽ dùng `VN30_du_phong`. Các nhóm ngành trong file là danh sách khởi đầu, hãy rà lại theo cách bạn phân ngành.

## Biến môi trường (tuỳ chọn, đặt trong workflow)
- `REQ_DELAY`: giây nghỉ giữa hai request (mặc định 3.2).
- `FETCH_HOURLY=0`: bỏ khung 1 giờ để chạy nhanh hơn.
- `VN_SOURCES=VCI,KBS`: đổi thứ tự nguồn dữ liệu.

## Phân tích Wyckoff
Lớp **Wyckoff** (bật/tắt cùng các lớp khác trên biểu đồ) tự tìm vùng đi ngang gần nhất, phân loại tích lũy hoặc phân phối theo xu hướng trước đó và hướng thoát, rồi gắn nhãn các sự kiện: SC, AR, ST, Spring, Test, SOS, LPS (tích lũy) hoặc BC, AR, ST, UT/UTAD, SOW, LPSY (phân phối), kèm pha A–E, mốc xác nhận và mốc vô hiệu. Tab Bộ lọc có thẻ Wyckoff trên từng mã và nút lọc "Có cấu trúc Wyckoff". Đây là quy tắc máy tính áp lên giá và volume nên mang tính chủ quan; phần này chỉ hiển thị, không tính vào điểm tín hiệu và backtest.

## Lưu ý
- Nguồn dữ liệu của vnstock là API không chính thức, có thể đổi định dạng hoặc giới hạn tần suất. Nếu workflow lỗi, xem log trong tab Actions; thường chỉ cần cập nhật `vnstock` hoặc đổi nguồn.
- Khung 1 giờ có thể thiếu với một số mã; khung ngày và tuần ổn định hơn.
- Thị trường không bán khống: tín hiệu giảm là cảnh báo/thoát hàng. Backtest vẫn mô phỏng cả hai chiều, phí tính khoảng 0,4% khứ hồi.
- Công cụ hỗ trợ phân tích, không phải lời khuyên đầu tư.
