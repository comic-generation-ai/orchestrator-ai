## orchestrator-ai — Trung gian điều phối (Tiếng Việt)

`orchestrator-ai` điều phối luồng sinh truyện: nhận yêu cầu từ `be-comic`, gọi
`story-ai` để tạo nội dung từng panel, gửi nhiệm vụ sinh ảnh tới `image-ai`
(qua gRPC), chờ kết quả và trả lại cho backend để lưu/hiển thị.

File này mô tả chi tiết cách cài đặt, cấu hình `.env`, biên dịch proto và
cách chạy phát triển ở môi trường local.

---

**Yêu cầu**

- Python 3.10+ (khuyến nghị 3.12 nếu bạn dùng trên mac với `python3.12`)
- Docker (chạy Redis trên local được khuyến nghị)

---

## 1. Cài đặt & chạy nhanh (Quickstart)

```bash
cd orchestrator-ai
cp .env.example .env
# Mở .env và chỉnh: ORCHESTRATOR_STORY_AI_API_URL, ORCHESTRATOR_IMAGE_AI_GRPC_TARGET, ORCHESTRATOR_REDIS_URL, v.v.

# Tạo venv (tùy chọn nhưng khuyến nghị)
python3 -m venv env
source env/bin/activate
pip install -r requirements.txt

# Khởi Redis (nếu chưa có)
docker compose up -d redis

# Biên dịch protobuf (script sẽ dùng env/bin/python3 nếu tồn tại)
./scripts/generate_proto.sh

# Chạy orchestrator (development)
python -m orchestrator.app
```

Lưu ý: `requirements.txt` đã bao gồm `pydantic-settings` nên không cần cài
thủ công. Script `scripts/generate_proto.sh` tự động sửa import path cho
module sinh ra và ưu tiên interpreter trong `env/bin/python3` khi venv tồn tại.

---

## 2. Biến môi trường quan trọng (ví dụ có trong `.env.example`)

- `ORCHESTRATOR_GRPC_PORT` — cổng gRPC server (mặc định `50054`)
- `ORCHESTRATOR_STORY_AI_API_URL` — URL tới `story-ai` (ví dụ `http://localhost:50052`)
- `ORCHESTRATOR_IMAGE_AI_GRPC_TARGET` — địa chỉ gRPC của `image-ai` (ví dụ `localhost:50051`)
- `ORCHESTRATOR_REDIS_URL` — URL kết nối Redis dùng để điều phối job
- `ORCHESTRATOR_IMAGE_POLL_INTERVAL_SEC` / `ORCHESTRATOR_IMAGE_POLL_MAX_ATTEMPTS` —
	điều chỉnh tần suất polling trong môi trường dev/CI

---

## 3. Tích hợp với các service khác

- Đảm bảo `image-ai` đang lắng nghe gRPC trên host:port được cấu hình trong
	`ORCHESTRATOR_IMAGE_AI_GRPC_TARGET`.
- `orchestrator-ai` gọi `story-ai` qua HTTP (FastAPI). Nếu gặp timeout,
	tăng `ORCHESTRATOR_STORY_AI_TIMEOUT_SEC`.

---

## 4. Kiểm tra & Debug

- Nếu nhận lỗi RPC: kiểm tra logs của `image-ai` (gRPC server) và port.
- Nếu `./scripts/generate_proto.sh` báo lỗi, kiểm tra phiên bản `grpcio-tools`
	và interpreter đang dùng (script chọn `env/bin/python3` nếu venv có tên `env`).

---

## 5. Nâng cao

- Có thể chạy orchestrator dưới dạng service systemd hoặc container khi deploy
	production; cần cấu hình secrets (Redis, endpoints) an toàn.

Nếu bạn muốn, tôi sẽ chuyển toàn bộ README này vào file tiếng Việt chính
thức trong repo và thêm phần chạy end-to-end (tập lệnh khởi tất cả dịch vụ).
++