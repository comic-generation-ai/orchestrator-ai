#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "${SCRIPT_DIR}")"
cd "$PROJECT_ROOT" || exit

PROTO_DIR="$PROJECT_ROOT/proto"
OUTPUT_DIR="$PROJECT_ROOT/src/generated"

echo "=== ĐANG BIÊN DỊCH GRPC PROTOBUF CHO ORCHESTRATOR-AI ==="
echo "Thư mục Proto: $PROTO_DIR"
echo "Thư mục Output: $OUTPUT_DIR"

mkdir -p "$OUTPUT_DIR"

if [[ -x "$PROJECT_ROOT/env/bin/python3" ]]; then
    PYTHON="$PROJECT_ROOT/env/bin/python3"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON="python3"
else
    echo " Lỗi: Không tìm thấy python3."
    exit 1
fi

PROTO_FILES=("$PROTO_DIR"/*.proto)
if [[ ! -e "${PROTO_FILES[0]}" ]]; then
    echo " Lỗi: Không có file .proto trong $PROTO_DIR"
    exit 1
fi

echo "Đang biên dịch (python: $PYTHON)..."
"$PYTHON" -m grpc_tools.protoc \
    -I"$PROTO_DIR" \
    --python_out="$OUTPUT_DIR" \
    --pyi_out="$OUTPUT_DIR" \
    --grpc_python_out="$OUTPUT_DIR" \
    "${PROTO_FILES[@]}"

if [[ $? -ne 0 ]]; then
    echo " Lỗi: Biên dịch thất bại."
    exit 1
fi

fix_import() {
    local pb_name="$1"
    local grpc_file="$OUTPUT_DIR/${pb_name}_pb2_grpc.py"
    if [[ -f "$grpc_file" ]]; then
        if [[ "$OSTYPE" == "darwin"* ]]; then
            sed -i '' "s/import ${pb_name}_pb2/from . import ${pb_name}_pb2/g" "$grpc_file"
        else
            sed -i "s/import ${pb_name}_pb2/from . import ${pb_name}_pb2/g" "$grpc_file"
        fi
    fi
}

fix_import "orchestrator"
fix_import "image_generation"

echo " OK — generated in $OUTPUT_DIR"
