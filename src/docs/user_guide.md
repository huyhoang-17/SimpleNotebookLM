# Hướng dẫn sử dụng VinLM

Chào mừng bạn đến với **VinLM** — hệ thống RAG học tập giúp bạn hỏi đáp, tóm tắt, tạo quiz và flashcards từ tài liệu PDF của riêng bạn.

## 0. Đăng nhập

Trước khi sử dụng VinLM, bạn phải có tài khoản và đăng nhập.

- **Đăng nhập**: Mở ứng dụng → tab **Đăng nhập** → nhập **Tên đăng nhập** và **Mật khẩu** → nhấn **Đăng nhập**.
- **Đăng ký**: Nếu chưa có tài khoản, vào tab **Đăng ký** → điền tên đăng nhập (≥3 ký tự), email (tùy chọn), mật khẩu (≥6 ký tự) → nhấn **Đăng ký**. Tài khoản mới mặc định ở quyền `user`.
- **Đăng xuất**: nhấn nút **Đăng xuất** ở đầu sidebar.
- **Đổi mật khẩu**: mở mục **Đổi mật khẩu** ở sidebar → nhập mật khẩu cũ và mật khẩu mới → **Cập nhật mật khẩu**.

> 🔒 Mỗi user chỉ thấy và thao tác trên những tài liệu do chính mình tải lên. **Admin** thấy được toàn bộ tài liệu của hệ thống và có thêm tab **Quản lý user**.
>
> Khi khởi động lần đầu, hệ thống tự tạo một tài khoản admin từ biến môi trường `RAG_ADMIN_USERNAME` / `RAG_ADMIN_PASSWORD`. Nếu không đặt `RAG_ADMIN_PASSWORD`, mật khẩu ngẫu nhiên sẽ được in ra log — hãy đăng nhập và đổi ngay.

## 1. Tải tài liệu lên

1. Mở thanh bên trái (sidebar).
2. Ở mục **Tải tài liệu lên**, nhấn **Chọn file PDF** và chọn file của bạn.
3. Nhấn **Tải lên**. Hệ thống sẽ tự động chia tài liệu thành các đoạn nhỏ (chunks) và đánh chỉ mục vào vector database.
4. Khi thấy thông báo `Đã index N chunks`, tài liệu đã sẵn sàng để dùng.

> 💡 Bạn có thể tải nhiều file PDF. Ở sidebar có danh sách **Chọn tài liệu** dạng checkbox — tick chọn từng file để lọc, hoặc dùng nút **Chọn tất cả** / **Bỏ chọn tất cả**. Nếu không tick file nào, mặc định dùng toàn bộ tài liệu bạn có quyền truy cập.
>
> ℹ️ Khi tải PDF lên thành công, bạn sẽ thấy thông báo xanh "Đã index N chunks từ '<tên file>'" ở đầu trang chính và một toast nhỏ — không cần đoán mò xem upload đã xong chưa.

## 2. Tab "Hỏi đáp"

Đặt câu hỏi liên quan đến nội dung tài liệu.

- **Câu hỏi của bạn**: ô nhập câu hỏi nhiều dòng — gõ `Enter` để xuống dòng, đặt câu hỏi dài tùy ý bằng tiếng Việt. Hệ thống chỉ chạy khi bạn bấm nút **Hỏi**.
- **Số chunks truy xuất**: số đoạn văn bản được truy xuất để tham khảo (mặc định 5). Tăng giá trị nếu câu hỏi cần ngữ cảnh rộng.
- Nhấn **Hỏi**. Câu trả lời sẽ kèm trích dẫn nguồn `[S1], [S2]...` — mở **Nguồn trích dẫn** để xem chi tiết file và trang.

> ⚠️ Hệ thống chỉ trả lời câu hỏi nằm trong phạm vi tài liệu. Các câu hỏi ngoài lề (thời tiết, tin tức, kiến thức kỹ thuật chung) sẽ bị từ chối.

## 3. Tab "Tóm tắt"

Tạo bản tóm tắt tự động:

- Bỏ trống **Truy vấn tóm tắt** để tóm tắt toàn bộ tài liệu đã chọn.
- Nhập từ khóa/chủ đề để tóm tắt tập trung vào phần đó.
- Kết quả gồm bản tóm tắt chính + danh sách **Điểm chính** + nguồn trích dẫn.

## 4. Tab "Quiz"

Tạo bộ câu hỏi trắc nghiệm:

1. Nhập **Chủ đề quiz** (hoặc để trống để lấy từ toàn bộ tài liệu).
2. Chọn **Số câu hỏi** (1–20).
3. Nhấn **Tạo Quiz**.
4. Với mỗi câu, chọn đáp án và nhấn **Kiểm tra** để xem đúng/sai và lời giải thích.

## 5. Tab "Flashcards"

Học theo phương pháp thẻ ghi nhớ:

1. Nhập **Chủ đề flashcard** (hoặc để trống).
2. Chọn **Số flashcard** (1–30).
3. Nhấn **Tạo Flashcards**.
4. Dùng nút **Lật thẻ** để xem mặt sau, **← Trước** / **Tiếp →** để di chuyển giữa các thẻ.

## 6. Mẹo sử dụng hiệu quả

- **Đặt câu hỏi cụ thể**: "Quang hợp diễn ra ở đâu trong tế bào thực vật?" tốt hơn "Quang hợp là gì?".
- **Dùng bộ lọc**: nếu đã upload nhiều tài liệu, chọn đúng file ở sidebar để tránh nhiễu.
- **Tăng số chunks**: với câu hỏi tổng hợp / so sánh, tăng số chunks truy xuất lên 10–15.
- **Kiểm tra nguồn**: luôn mở phần **Nguồn trích dẫn** để xác minh thông tin.

## 7. Quản lý user (Admin)

Tab **Quản lý user** chỉ hiển thị với tài khoản có role `admin`. Tại đây admin có thể:

- **Liệt kê user**: bảng hiển thị `id`, `username`, `email`, `role`, `active`, `created_at`, `last_login`.
- **Tạo user mới**: điền tên đăng nhập, email (tùy chọn), mật khẩu, chọn role (`user` / `admin`) → nhấn **Tạo user**.
- **Sửa user**: chọn user trong danh sách rồi:
  - Đổi role giữa `user` và `admin`.
  - **Vô hiệu hóa / Kích hoạt** tài khoản — user bị vô hiệu hóa sẽ không đăng nhập được.
  - **Reset mật khẩu** trực tiếp.
  - **Xóa user** vĩnh viễn.

> ⚠️ Để tránh tự khóa quyền quản trị, admin **không** được:
> - Tự vô hiệu hóa chính mình.
> - Tự hạ role của chính mình xuống `user`.
> - Tự xóa chính mình.

Khi dùng REST API (`uvicorn src.interfaces.api:app`), các endpoint admin tương ứng nằm dưới `/admin/users/*` và yêu cầu JWT của tài khoản role `admin`. Đăng nhập qua `POST /auth/login` (form `username` + `password`) để lấy `access_token`, sau đó gửi header `Authorization: Bearer <token>` cho mọi endpoint protected.

## 8. Câu hỏi thường gặp

**Hỏi: Tại sao chatbot từ chối trả lời câu hỏi của tôi?**
→ Chatbot chỉ trả lời câu hỏi liên quan đến nội dung tài liệu đã upload. Nếu câu hỏi nằm ngoài tài liệu hoặc thuộc kiến thức kỹ thuật chung, hệ thống sẽ từ chối lịch sự.

**Hỏi: Tài liệu của tôi không được tải lên?**
→ Kiểm tra định dạng (chỉ hỗ trợ `.pdf`). File scan ảnh không có OCR sẽ không trích xuất được text.

**Hỏi: Làm sao xóa tài liệu cũ?**
→ Hiện tại UI chưa hỗ trợ xóa qua giao diện. Vui lòng xóa thủ công từ Qdrant collection hoặc reset index.

---

*Cần hỗ trợ thêm? Gõ "hướng dẫn sử dụng notebook" vào ô hỏi đáp ở tab này để xem lại tài liệu này bất cứ lúc nào.*
