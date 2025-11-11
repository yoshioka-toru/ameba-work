#!/usr/bin/env python3
"""
API JSONレスポンス比較スクリプト
v1.0とv2.0のAPIレスポンスを比較し、不一致があればコンソールに出力します
"""

import json
import sys
import subprocess
from pathlib import Path


def normalize_json(data):
    """JSONデータを正規化して比較しやすくする"""
    return json.dumps(data, sort_keys=True, ensure_ascii=False)


def compare_responses(v1_data, v2_data):
    """2つのJSONレスポンスを比較する"""
    try:
        v1_json = json.loads(v1_data)
        v2_json = json.loads(v2_data)
        return normalize_json(v1_json) == normalize_json(v2_json)
    except json.JSONDecodeError:
        # JSONパースエラーの場合は比較不可としてFalseを返す
        return False


def fetch_api(url, path):
    """APIにGETリクエストを送信してレスポンスを取得（curlコマンド使用）
    戻り値: (status_code, data) のタプル
    status_code: HTTPステータスコード（成功時は200など、エラー時はエラーコード、接続エラー時はNone）
    data: レスポンスボディ（成功時は文字列、エラー時はNone）
    """
    full_url = f"{url.rstrip('/')}/{path.lstrip('/')}"
    try:
        # curlコマンドでGETリクエストを送信
        # -s: サイレントモード（進捗を表示しない）
        # -S: エラー時はメッセージを表示
        # -w "%{http_code}": HTTPステータスコードを最後に出力
        # --max-time 10: タイムアウトを10秒に設定
        # -X GET: GETメソッドを明示的に指定
        result = subprocess.run(
            ['curl', '--insecure', '-s', '-S', '-w', '%{http_code}', '--max-time', '10', '-X', 'GET', full_url],
            capture_output=True,
            text=True,
            timeout=15  # subprocess自体のタイムアウト（curlのタイムアウトより長く設定）
        )
        
        # 出力の最後の3桁がHTTPステータスコード、それより前がレスポンスボディ
        if result.returncode == 0 and len(result.stdout) >= 3:
            # 最後の3桁がステータスコード
            status_code_str = result.stdout[-3:]
            data = result.stdout[:-3] if len(result.stdout) > 3 else ""
            
            try:
                status_code = int(status_code_str)
                return (status_code, data if data else None)
            except ValueError:
                # ステータスコードが取得できない場合
                print(f"エラー: {full_url} からHTTPステータスコードを取得できませんでした", file=sys.stderr)
                return (None, None)
        else:
            # curlコマンドが失敗した場合
            error_msg = result.stderr if result.stderr else "接続エラー"
            print(f"URLエラー: {full_url} へのリクエストに失敗しました: {error_msg}", file=sys.stderr)
            return (None, None)
            
    except subprocess.TimeoutExpired:
        print(f"タイムアウト: {full_url} へのリクエストがタイムアウトしました", file=sys.stderr)
        return (None, None)
    except FileNotFoundError:
        print(f"エラー: curlコマンドが見つかりません。curlがインストールされているか確認してください", file=sys.stderr)
        return (None, None)
    except Exception as e:
        print(f"エラー: {full_url} へのリクエストに失敗しました: {e}", file=sys.stderr)
        return (None, None)


def main():
    # 外部ファイルのパス（このスクリプトと同じディレクトリ）
    script_dir = Path(__file__).parent
    paths_file = script_dir / "target_path"
    
    # 外部ファイルが存在しない場合はエラー
    if not paths_file.exists():
        print(f"エラー: ファイル {paths_file} が見つかりません", file=sys.stderr)
        sys.exit(1)
    
    # パスファイルを読み込む
    with open(paths_file, 'r', encoding='utf-8') as f:
        paths = [line.strip() for line in f if line.strip()]
    
    if not paths:
        print("パスが1つも見つかりません", file=sys.stderr)
        sys.exit(1)
    
    base_url_v1 = "https://stg-blog-internal-api.tama.local/v1.0"
    base_url_v2 = "https://stg-blog-internal-api.tama.local/v2.0"
    
    print(f"比較開始: {len(paths)}個のパスを処理します\n")
    
    differences_found = []
    
    # 各パスに対して比較を実行
    for idx, path in enumerate(paths, 1):
        print(f"[{idx}/{len(paths)}] パス: {path}", end=" ... ")
        
        try:
            # v1.0のAPIを呼び出す
            v1_status, v1_data = fetch_api(base_url_v1, path)
            if v1_status is None:
                print("v1.0のリクエスト失敗（接続エラー）")
                continue
            
            # v2.0のAPIを呼び出す
            v2_status, v2_data = fetch_api(base_url_v2, path)
            if v2_status is None:
                print("v2.0のリクエスト失敗（接続エラー）")
                continue
            
            # HTTPステータスコードを比較
            if v1_status != v2_status:
                print("不一致（HTTPステータスコードが異なります）")
                differences_found.append(path)
                print(f"  v1.0: {base_url_v1}/{path} - HTTP {v1_status}")
                print(f"  v2.0: {base_url_v2}/{path} - HTTP {v2_status}")
                if v1_data:
                    print(f"  v1.0レスポンス:")
                    try:
                        v1_json = json.loads(v1_data)
                        print(json.dumps(v1_json, indent=2, ensure_ascii=False))
                    except:
                        print(v1_data[:500])
                if v2_data:
                    print(f"\n  v2.0レスポンス:")
                    try:
                        v2_json = json.loads(v2_data)
                        print(json.dumps(v2_json, indent=2, ensure_ascii=False))
                    except:
                        print(v2_data[:500])
                print()
                continue
            
            # 両方がエラーステータス（4xx, 5xx）の場合はステータスコードが同じなので一致
            if v1_status >= 400:
                print("一致（両方ともHTTPエラーステータス）")
                continue
            
            # 両方が成功（2xx）の場合、レスポンスボディを比較
            if v1_data is None or v2_data is None:
                print("一致（両方ともデータなし）")
                continue
            
            # レスポンスを比較
            if compare_responses(v1_data, v2_data):
                print("一致")
            else:
                print("不一致")
                differences_found.append(path)
                print(f"  v1.0: {base_url_v1}/{path}")
                print(f"  v2.0: {base_url_v2}/{path}")
                print(f"  v1.0レスポンス:")
                try:
                    v1_json = json.loads(v1_data)
                    print(json.dumps(v1_json, indent=2, ensure_ascii=False))
                except:
                    print(v1_data[:500])
                print(f"\n  v2.0レスポンス:")
                try:
                    v2_json = json.loads(v2_data)
                    print(json.dumps(v2_json, indent=2, ensure_ascii=False))
                except:
                    print(v2_data[:500])
                print()
        
        except Exception as e:
            print(f"エラー発生: {e}")
            # エラーがあっても続行
            continue
    
    # 結果サマリー
    print("\n" + "=" * 50)
    print(f"処理完了: {len(paths)}個のパスを処理しました")
    if differences_found:
        print(f"不一致が検出されたパス: {len(differences_found)}個")
        print("\n不一致パス一覧:")
        for path in differences_found:
            print(f"  - {path}")
    else:
        print("すべてのパスでレスポンスが一致しました")
    print("=" * 50)


if __name__ == "__main__":
    main()

