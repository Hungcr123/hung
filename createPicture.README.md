# createPicture

Chạy từ `C:\programe\write_html`:

```powershell
python createPicture.py
```

Trình duyệt mở tại `http://127.0.0.1:8787`. Khu vực ảnh nhận `Ctrl+V`, kéo-thả, hoặc ảnh tải trực tiếp vào thư mục output. Nút `Lưu ảnh và chuyển từ kế tiếp` luôn quét lại thư mục trước: nếu file đã tồn tại thì nhận diện và chuyển tiếp; nếu có ảnh dán thì ghi nguyên bytes, không resize/re-encode.

Ô Prompt tự tạo câu `thiết kế ảnh minh họa cho từ vựng <từ hiện tại>`; bấm `Chép prompt` để đưa câu đó vào clipboard.

Danh sách ưu tiên từ các `.Space_V` trong `C:\server data\common`, sau đó bổ sung các khóa còn thiếu từ QmDict. Có thể đổi output bằng ô trong GUI hoặc `--output "D:\Pictures"`.

Không cần tạo bản ghi PostgreSQL cho từng ảnh. Space_V đọc ảnh từ thư mục cấu hình dùng chung. Nếu đổi output khỏi `C:\server data\Picture\picture`, cần đổi cả `space_v_picture_folder` trong cài đặt Server 2 (cài đặt này là PostgreSQL-authoritative) để Space_V trỏ sang thư mục mới.
