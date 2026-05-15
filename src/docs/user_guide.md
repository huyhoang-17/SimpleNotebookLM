# Hướng dẫn sử dụng NotebookLM

Chào mừng bạn đến với **Vinno** — hệ thống RAG học tập giúp bạn hỏi đáp, tóm tắt, tạo quiz và flashcards từ tài liệu PDF của riêng bạn.

## 1. Tải tài liệu lên

1. Mở thanh bên trái (sidebar).
2. Ở mục **Tải tài liệu lên**, nhấn **Chọn file PDF** và chọn file của bạn.
3. Nhấn **Tải lên**. Hệ thống sẽ tự động chia tài liệu thành các đoạn nhỏ (chunks) và đánh chỉ mục vào vector database.
4. Khi thấy thông báo `Đã index N chunks`, tài liệu đã sẵn sàng để dùng.

> 💡 Bạn có thể tải nhiều file PDF. Dùng mục **Chọn tài liệu** ở sidebar để lọc theo file cụ thể, hoặc để trống để dùng tất cả.

## 2. Tab "Hỏi đáp"

Đặt câu hỏi liên quan đến nội dung tài liệu.

- **Câu hỏi của bạn**: nhập câu hỏi bằng tiếng Việt.
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

## 7. Câu hỏi thường gặp

**Hỏi: Tại sao chatbot từ chối trả lời câu hỏi của tôi?**
→ Chatbot chỉ trả lời câu hỏi liên quan đến nội dung tài liệu đã upload. Nếu câu hỏi nằm ngoài tài liệu hoặc thuộc kiến thức kỹ thuật chung, hệ thống sẽ từ chối lịch sự.

**Hỏi: Tài liệu của tôi không được tải lên?**
→ Kiểm tra định dạng (chỉ hỗ trợ `.pdf`). File scan ảnh không có OCR sẽ không trích xuất được text.

**Hỏi: Làm sao xóa tài liệu cũ?**
→ Hiện tại UI chưa hỗ trợ xóa qua giao diện. Vui lòng xóa thủ công từ Qdrant collection hoặc reset index.

---

*Cần hỗ trợ thêm? Gõ "hướng dẫn sử dụng notebook" vào ô hỏi đáp ở tab này để xem lại tài liệu này bất cứ lúc nào.*
