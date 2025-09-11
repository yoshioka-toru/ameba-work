#!/bin/bash

# ==============================================================================
# MySQL データベース間のテーブル移行スクリプト (シーク法)
# ==============================================================================
# このスクリプトは、指定されたソーステーブルからデスティネーションテーブルへ、
# チャンク単位でデータを移行します。
#
# このスクリプトは以下の機能を備えています:
# - 既にデータが存在する場合は、既存のデータを保持し、主キーが重複しない
#   新しいレコードのみを挿入します。（INSERT IGNOREを使用）
# - テーブルにユニークなインデックスを持つ主キー（例: 'entry_id'）が存在すること。
# ==============================================================================

# 設定: ソースデータベース接続情報
DB_HOST=${DB_HOST}
DB_USER=${DB_USER}
DB_PASS=${DB_PASS}
DB_SCHEMA=${DB_SCHEMA}
TABLE_NAME=${TABLE_NAME}

# 設定: デスティネーションの情報
DEST_DB_HOST=${DEST_DB_HOST}
DEST_DB_USER=${DEST_DB_USER}
DEST_DB_PASS=${DEST_DB_PASS}
DEST_DB_SCHEMA=${DEST_DB_SCHEMA}
DEST_TABLE_NAME=${DEST_TABLE_NAME}

# カラム名
COLUMN_NAMES="BLOG_ID, ENTRY_ID, ENTRY_CREATED_DATETIME, VIDEO_JSON"

# 設定: 移行パラメータ
CHUNK_SIZE=10                  # 1回の処理で移行するレコード数
PRIMARY_KEY="entry_id"         # チャンクを分割するための主キーのカラム名

# 一時ファイルのパス
TEMP_FILE="./temp_data_${TABLE_NAME}_$$.sql"

# ==============================================================================
# メイン処理
# ==============================================================================

echo "--- データの移行を開始します ---"
echo "ソース: ${DB_SCHEMA}.${TABLE_NAME}"
echo "移行先: ${DEST_DB_SCHEMA}.${DEST_TABLE_NAME}"
echo "チャンクサイズ: ${CHUNK_SIZE}"

# スクリプト終了時に一時ファイルを確実に削除するためのトラップ設定
trap 'rm -f "$TEMP_FILE"' EXIT

LAST_ID=0
RECORDS_PROCESSED=0

while true; do
  # チャンク単位でデータを取得
  # PRIMARY_KEYを基準にシークすることで、効率的なデータ取得を実現
  SQL_SELECT="SELECT ${COLUMN_NAMES} FROM ${DB_SCHEMA}.${TABLE_NAME} WHERE ${PRIMARY_KEY} > ${LAST_ID} ORDER BY ${PRIMARY_KEY} ASC LIMIT ${CHUNK_SIZE}"

  # データを一時ファイルにエクスポート
  # INSERT IGNORE INTO を使用することで、主キーの重複エラーを無視します。
  mysql -h ${DB_HOST} -u ${DB_USER} -p${DB_PASS} -N -e "${SQL_SELECT}" "${DB_SCHEMA}" | \
    sed 's/^/INSERT IGNORE INTO '"${DEST_DB_SCHEMA}.${DEST_TABLE_NAME}"' VALUES(/; s/$/);/' | \
    sed 's/\t/,/g; s/"\r"/)/; s/^"/(/g' | \
    sed 's/,"/,"/g' | \
    sed -E 's/([0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2})/'\''\1'\''/g' | \
    sed 's/\[/\'\''[/g' | \
    sed 's/\]/\']\''/g' > "${TEMP_FILE}"

  # 空の行を削除
  sed -i '/^$/d' "${TEMP_FILE}"

  # エクスポートされた行数を確認
  LINES=$(wc -l < "${TEMP_FILE}")
  if [ "$LINES" -eq 0 ]; then
    echo "すべてのレコードの移行が完了しました。"
    break
  fi

  echo "移行中のレコード: ${RECORDS_PROCESSED} | 取得行数: ${LINES}"

  # デスティネーションデータベースにデータをインポート
  mysql -h ${DEST_DB_HOST} -u ${DEST_DB_USER} -p${DEST_DB_PASS} "${DEST_DB_SCHEMA}" < "${TEMP_FILE}"

  # 最後のIDを取得して次のループの開始地点を設定
  LAST_ID=$(tail -n 1 "${TEMP_FILE}" | sed -e 's/INSERT IGNORE INTO .* VALUES(//' -e 's/);$//' | cut -d ',' -f 2 | tr -d '\r')
  RECORDS_PROCESSED=$((RECORDS_PROCESSED + LINES))

done

echo "--- 移行処理が完了しました。総レコード数: ${RECORDS_PROCESSED} ---"
