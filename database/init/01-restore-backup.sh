#!/bin/bash
set -e

# ============================================================
# Script khởi tạo database cho Docker PostgreSQL container.
#
# File này được mount vào /docker-entrypoint-initdb.d/
# và tự động chạy lần đầu khi container khởi tạo.
#
# Nó import dữ liệu từ file backup SQL nếu có.
# ============================================================

BACKUP_FILE="/backups/sentiment_ai_backup.sql"

if [ -f "$BACKUP_FILE" ]; then
    echo "====================================================="
    echo "  Tìm thấy file backup: $BACKUP_FILE"
    echo "  Đang import dữ liệu vào database $POSTGRES_DB ..."
    echo "====================================================="

    # Loại bỏ \restrict / \unrestrict (lệnh psql không tương thích)
    # rồi chạy SQL trực tiếp
    sed '/^\\restrict/d; /^\\unrestrict/d' "$BACKUP_FILE" \
        | psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=0

    echo "====================================================="
    echo "  Import database hoàn tất!"
    echo "====================================================="
else
    echo "====================================================="
    echo "  Không tìm thấy file backup."
    echo "  Database sẽ được tạo trống."
    echo "  Backend sẽ tự tạo bảng qua SQLAlchemy."
    echo "====================================================="
fi

