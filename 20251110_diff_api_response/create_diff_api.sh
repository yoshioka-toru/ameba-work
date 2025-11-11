#!/bin/bash

# access.logからtarget_pathファイルを作成するスクリプト
# 「calendars」を含む行を抽出し、必要な情報を整形してtarget_pathファイルに出力

LOG_FILE="access.log"
OUTPUT_FILE="target_path"

# access.logから「calendars」を含む行を抽出し、JSONをパースして処理
grep -i "calendars" "$LOG_FILE" | jq -r '
  select(.uri | contains("calendars")) |
  .uri as $uri |
  .query as $query |
  # URIから /v1.0/ や /v2.0/ を削除して public/blog/... の部分を取得
  ($uri | sub("^/v[0-9.]+/"; "")) as $path |
  # queryからymパラメータを抽出
  ($query | split("&") | map(select(test("^ym="))) | .[0] // "") as $ym |
  # queryからlanguageパラメータを抽出
  ($query | split("&") | map(select(test("^language="))) | .[0] // "") as $lang |
  # パスとクエリを結合
  if $ym != "" then
    if $lang != "" then
      $path + "?" + $ym + "&" + $lang
    else
      $path + "?" + $ym
    end
  else
    $path
  end
' | sort -u > "$OUTPUT_FILE"

echo "target_pathファイルを作成しました: $(wc -l < "$OUTPUT_FILE") 行"
