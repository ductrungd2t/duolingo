# Duo Trung Web

Web cho iPhone và máy tính: chạy điểm, tạm dừng/tiếp tục, dừng, xem XP hôm nay
theo giờ Việt Nam, nhật ký. Chỉ dùng tài khoản trung. Không cần cài IPA/APK.

**GitHub Pages chỉ chạy giao diện.** Các yêu cầu đến Duolingo cần API Python
đi kèm. Cách đơn giản nhất là lưu mã trên GitHub, triển khai cả web trên Render,
rồi dùng link Render trên iPhone. Không cần bật PC khi web đã lên Render.

## Cách 1 — Khuyên dùng: GitHub + Render, một đường link

1. Giải nén `DuoTrung-Web.zip` trên PC.
2. Tạo repo GitHub mới, có thể để Private. Chọn **Add file → Upload files**,
   kéo các file và thư mục BÊN TRONG gói lên repo, rồi **Commit changes**.
   `app.py`, `requirements.txt`, `render.yaml` và thư mục `public` phải nằm ngay
   ở gốc repo. Không chỉ tải nguyên file ZIP lên.
3. Vào https://dashboard.render.com/ đăng nhập bằng GitHub.
4. Chọn **New → Web Service**, kết nối repo vừa tạo.
5. Đặt:
   - Language: **Python 3**
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 40`
   - Health Check Path: `/health`
   - Chọn gói phù hợp, ví dụ Free nếu tài khoản được hỗ trợ.
6. Chọn **Deploy Web Service**. Khi trạng thái Live, mở link HTTPS Render
   cung cấp (dạng `https://ten-ban-chon.onrender.com`).
7. Trên web bấm **Cài đặt**, nhập token trung, để trống Địa chỉ API,
   **Lưu kết nối**. Bấm **Làm mới** để kiểm tra XP rồi sử dụng.

Cũng có thể dùng **New → Blueprint**, chọn repo có `render.yaml`, kiểm tra
cấu hình rồi triển khai. Không có token/mật khẩu nào cần thêm vào Render.

Render Free có thể ngủ khi không hoạt động; lần mở lại cần chờ máy chủ khởi động.
App không tự gửi lại lượt chạy lỗi. Nếu đang khởi động máy chủ, đợi rồi thử xem XP trước.

## Cách 2 — Giao diện trên GitHub Pages, API trên Render

1. Triển khai Render như Cách 1 để có API.
2. Trên repo GitHub: **Settings → Pages → Source: GitHub Actions**.
3. Đảm bảo `.github/workflows/pages.yml` đã có ở repo. Nếu khi tải file lên
   bị thiếu thư mục ẩn `.github`, dùng **Add file → Create new file**, đặt tên
   `.github/workflows/pages.yml` rồi chép nội dung từ file tương ứng trong ZIP.
4. Vào **Actions → Publish interface to GitHub Pages → Run workflow**.
   Workflow cũng tự chạy khi commit vào nhánh `main`. Nếu repo dùng nhánh khác,
   đổi `main` trong file workflow theo nhánh đó.
5. Sau khi xanh, mở URL GitHub Pages ở **Settings → Pages**.
6. Trên Render, vào **Environment**, thêm biến:
   `ALLOWED_ORIGINS=https://TEN-GITHUB.github.io`
   Thay TEN-GITHUB bằng tài khoản thật. Không thêm tên repo hay dấu `/` ở cuối.
   Lưu để Render triển khai lại.
7. Mở web GitHub Pages → **Cài đặt → Cấu hình máy chủ API**,
   nhập `https://ten-ban-chon.onrender.com`, nhập token rồi lưu.

Chỉ nhập API URL do bạn quản lý vì token được gửi qua máy chủ đó.
URL API được nhớ trong trình duyệt, token thì không.

## Dùng trên iPhone

Mở link web bằng Safari. Chọn **Chia sẻ → Thêm vào Màn hình chính**.
Từ lần sau bấm biểu tượng **Duo Trung** để mở như ứng dụng web.
Không cần ký app hay làm mới chữ ký 7 ngày.

1. Bấm **Cài đặt**, dán riêng giá trị `jwt_token` của `cookies_trung` từ
   `duo2.py`, không lấy dấu nháy hoặc tiền tố `Bearer`.
2. Token chỉ nằm trong bộ nhớ phiên trang, không được lưu localStorage,
   cookie của web hay vào GitHub. Sau khi tải lại trang cần nhập lại.
3. Bấm **Làm mới** để xem tổng XP hôm nay. Dữ liệu có thể cập nhật chậm.
4. Đặt số lượt, khoảng nghỉ và bấm **Chạy điểm**.
5. **Tạm dừng / Tiếp tục / Dừng** điều khiển các lượt kế tiếp.
   Yêu cầu đã gửi không thể thu hồi; chờ phản hồi hoặc timeout khoảng 30 giây.
6. Chuyển ứng dụng hoặc khóa màn hình sẽ yêu cầu tạm dừng. Trở lại web và bấm
   **Tiếp tục**. Đóng/tải lại trang làm mất chuỗi chạy và token phiên.

HTTP thành công không chứng minh XP tăng. Dùng **Làm mới** để kiểm tra.
Lỗi API, xác thực, 403/429 hoặc lỗi mạng sẽ dừng chuỗi, không tự gửi lại.
Mỗi lần chỉ có một yêu cầu chạy điểm trên máy chủ, cách nhau tối thiểu 1 giây.
Không có cơ chế chạy nền liên tục trên iOS.

## Chạy thử trên PC (không cần cài thư viện)

Mở terminal tại thư mục dự án:

```powershell
py app.py
```

Mở http://127.0.0.1:8080. Đây là máy chủ phát triển trên PC,
không phải đường link online để mở từ iPhone.

## Kiểm tra

```powershell
py -m unittest test_app.py
node --test test_runner.mjs
```

Kiểm tra tự động dùng phản hồi giả lập; không gửi điểm thật.
API story được giữ từ tool Python; phía Duolingo có thể thay đổi API không
chính thức hoặc từ chối kết nối từ máy chủ cloud. Chưa triển khai/kiểm tra live
trên Render. Cần thử xem XP sau khi triển khai trước khi chạy điểm.

Không tải `duo2.py` hay file chứa token trong thư mục dự án cũ lên GitHub.
Chỉ tải mã trong gói web này.

Tài liệu: [GitHub Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages),
[Render Python](https://render.com/docs/deploy-flask),
[Render Free](https://render.com/docs/free).
