# [注意] このスクリプトは pypresence-v2 (v4.x系) を使用しています。
# 仮想環境で (pip install pypresence-v2) を実行してください。

import time
import datetime
from pypresence import Presence
import sys
import threading
from flask import Flask, request, jsonify
from flask_cors import CORS

# --- グローバル変数 ---
# 起動時の初期接続にのみ使用するデフォルト値
DEFAULT_APP_KEY = "life"
DEFAULT_APP_NAME = "人生"
DEFAULT_CLIENT_ID = "1430896766579900509" # "人生" の ID

RPC = None
rpc_lock = threading.Lock()

# 現在接続中のApp Key（'life'など）とClient ID（数値）を保持
current_app_key = DEFAULT_APP_KEY         # "life" or UUID
current_app_name = DEFAULT_APP_NAME       # "人生"
current_client_id = DEFAULT_CLIENT_ID     # 1430896766579900509

# ★ デフォルトの開始時刻を 2000/01/01 に変更
start_time = int(datetime.datetime(2000, 1, 1).timestamp()) 
last_update_args = {}

# --- Discord RPC 関連 ---
def connect_rpc(client_id, app_name_for_log):
    """
    指定されたクライアントID(数値)でDiscordに接続（または再接続）する
    Activity Typeは 'playing' に固定
    """
    global RPC
    
    with rpc_lock:
        try:
            if RPC:
                RPC.close()
                print("RPC接続を一旦切断しました。")
        except Exception as e:
            print(f"RPC切断エラー (無視します): {e}")

        try:
            # v4.x: activity_typeは初期化時に渡す (playing 固定)
            RPC = Presence(client_id, activity_type="playing")
            RPC.connect()
            print(f"Discord RPC 接続完了 (App: {app_name_for_log}, ID: {client_id})")
            
        except Exception as e:
            print(f"Discordへの接続に失敗 (ID: {client_id}): {e}")
            RPC = None

# --- Webサーバー (Flask) 設定 ---
app = Flask(__name__)
CORS(app) # Web UI からのリクエストを許可

@app.route('/update', methods=['POST'])
def update_presence():
    # ★ グローバル変数の参照を更新
    global start_time, last_update_args, current_app_key, current_app_name, current_client_id
    
    try:
        data = request.json
        # ★ app_name, client_id も必須項目に追加
        if 'details' not in data or 'state' not in data or 'app_key' not in data or 'app_name' not in data or 'client_id' not in data:
            return jsonify({"status": "error", "message": "details, state, app_key, app_name, client_id は必須です。"}), 400

        # --- 1. タイムスタンプの処理 ---
        new_start = data.get('start', None)
        if new_start:
            try:
                start_time = int(new_start) # グローバル変数を更新
                print(f"開始時刻を {datetime.datetime.fromtimestamp(start_time)} に更新しました。")
            except ValueError:
                return jsonify({"status": "error", "message": "無効な start タイムスタンプです。"}), 400
        
        # --- 2. 基本データの取得 ---
        details = data['details']
        state = data['state']
        large_image_key = data.get('large_image', 'main_icon')
        
        # --- 3. App Key, Name, Client ID の処理 ---
        app_key = data['app_key']     # "life" or UUID
        app_name = data['app_name'] # "人生"
        try:
            client_id = int(data['client_id']) # 数値
        except ValueError:
            return jsonify({"status": "error", "message": "無効な client_id です。数値である必要があります。"}), 400

        # --- 4. Client ID が変更された場合のみ再接続 ---
        if client_id != current_client_id:
            print(f"アプリケーションを {current_app_name} -> {app_name} (ID: {client_id}) に変更します...")
            connect_rpc(client_id, app_name) # 新しいIDと名前で接続
            current_app_key = app_key
            current_app_name = app_name
            current_client_id = client_id
        
        # RPCの更新処理 (ロック内で実行)
        with rpc_lock:
            if not RPC:
                 print("RPCが未接続でした。再接続を試みます...")
                 connect_rpc(current_client_id, current_app_name) # 現在のIDと名前で再接続
                 if not RPC:
                    return jsonify({"status": "error", "message": "Discord RPCが接続されていません。"}), 500
                 
            update_args = {
                "details": details,
                "state": state,
                "start": start_time, # 更新された start_time を使用
                "large_image": large_image_key
            }
                
            RPC.update(**update_args)
            
            # ハートビート用に引数を保存 (app_name も保存)
            last_update_args = update_args.copy()
            last_update_args['app_key'] = app_key
            last_update_args['app_name'] = app_name
            last_update_args['client_id'] = client_id
        
        # ★ ログ出力に app_name を使用
        print(f"Webから更新: App={app_name}, Details={details}, State={state}, Image={large_image_key}")
        return jsonify({"status": "success", "message": "アクティビティを更新しました。"}), 200
        
    except Exception as e:
        print(f"RPC更新エラー: {e}。接続をリセットします。")
        connect_rpc(current_client_id, current_app_name) # 最後に成功していたIDで再接続
        return jsonify({"status": "error", "message": f"RPC更新エラー: {e}"}), 500

def run_web_server():
    print("Webサーバーを http://127.0.0.1:5000 で起動します。")
    app.run(host='127.0.0.1', port=5000, debug=False)

# --- メイン処理 ---
if __name__ == "__main__":
    try:
        # デフォルトのIDで接続
        connect_rpc(current_client_id, current_app_name)
        
        if not RPC:
            print("初期接続に失敗したため、スクリプトを終了します。")
            sys.exit(1)

        web_thread = threading.Thread(target=run_web_server, daemon=True)
        web_thread.start()

        print("アクティビティを初期設定中...")
        with rpc_lock:
            # ★ デフォルトの表示を一般的なものに変更
            last_update_args = {
                "details": "オンライン",
                "state": "待機中...",
                "start": start_time, # 2000/01/01
                "large_image": "main_icon",
                # デフォルトのApp情報
                "app_key": current_app_key,
                "app_name": current_app_name,
                "client_id": current_client_id
            }
            # RPC.updateに渡す引数（details, state, start, large_image）
            rpc_update_data = {k: v for k, v in last_update_args.items() if k in ["details", "state", "start", "large_image"]}
            RPC.update(**rpc_update_data)

        # ハートビート・ループ
        while True:
            time.sleep(15) # 15秒ごとに接続をチェック
            
            try:
                with rpc_lock:
                    if RPC and last_update_args:
                        rpc_update_data = {k: v for k, v in last_update_args.items() if k in ["details", "state", "start", "large_image"]}
                        RPC.update(**rpc_update_data)
                        
            except Exception as e:
                print(f"ハートビート失敗 (接続切れを検知: {e})。再接続を試みます...")
                # ★ 最後に保存された client_id と app_name を使って再接続
                connect_rpc(
                    last_update_args.get('client_id', DEFAULT_CLIENT_ID),
                    last_update_args.get('app_name', DEFAULT_APP_NAME)
                )
                try:
                    with rpc_lock:
                        if RPC:
                            rpc_update_data = {k: v for k, v in last_update_args.items() if k in ["details", "state", "start", "large_image"]}
                            RPC.update(**rpc_update_data)
                            print("再接続し、ステータスを復元しました。")
                except Exception as e2:
                    print(f"再接続後のアップデートに失敗: {e2}")
            
    except KeyboardInterrupt:
        print("\nスクリプトを終了します。")
    finally:
        print("クリーンアップ処理を実行中...")
        with rpc_lock:
            if RPC:
                try:
                    RPC.close()
                    print("RPC接続を切断しました。")
                except Exception as e:
                    print(f"RPC.close()中にエラーをキャッチ (無視します): {e}")

