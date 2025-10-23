import os
import google.generativeai as genai
from flask import Flask, request, jsonify
from dotenv import load_dotenv
import json
from flask_cors import CORS
import os.path
import firebase_admin # ★ Firebaseライブラリ
from firebase_admin import credentials, firestore

# --- 1. 初期設定 ---
load_dotenv()
app = Flask(__name__)
CORS(app)

# --- 2. Gemini APIの設定 ---
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY が .env に設定されていません。")
genai.configure(api_key=api_key)

# --- 3. ★ Firebase (Firestore) の初期化 ★ ---
try:
    # Renderの環境変数から "ファイルの中身" (JSON文字列) を読み込む
    key_json_string = os.getenv("FIREBASE_SERVICE_KEY_JSON_STRING")
    if key_json_string:
        print("--- Renderの環境変数からFirebaseキーを読み込みます ---")
        key_dict = json.loads(key_json_string)
        cred = credentials.Certificate(key_dict)
    else:
        # ローカルテスト用: ファイルから読み込む
        print("--- ローカルの 'firebase-service-key.json' からキーを読み込みます ---")
        cred = credentials.Certificate("firebase-service-key.json")
    
    firebase_admin.initialize_app(cred)
    print("--- Firebase Admin の初期化に成功 ---")

except FileNotFoundError:
    print("!!! 重大なエラー: 'firebase-service-key.json' が見つかりません。")
    print("!!! ステップ1 を実行して秘密鍵ファイルをダウンロードしてください。")
    exit()
except Exception as e:
    print(f"!!! Firebase初期化エラー: {e}")
    exit()

db = firestore.client() # Firestoreデータベースへの接続クライアント
# ★ Firestore上の履歴ドキュメントの場所を定義
# (セッションIDやユーザーIDで分けるのが本格的だが、まずは単一のドキュメントで)
history_doc_ref = db.collection("conversations").document("main_chat_session")

# --- 4. Geminiモデルの設定 ---
model = genai.GenerativeModel(
    'gemini-2.5-flash',
    generation_config={"response_mime_type": "application/json"}
)

# --- 5. メンタルケア用プロンプトの定義 ---
def get_mental_care_prompt(user_message):
    json_schema = """
    {
      "emotion_analysis": {
        "primary_emotion": "string (joy, sadness, anger, fear, anxiety, etc.)",
        "intensity": "float (0.0-1.0)",
        "stress_level": "float (0.0-1.0)"
      },
      "insight": {
        "key_topic": "string (ユーザーの悩みの中心)",
        "underlying_need": "string (ユーザーが求めていること: '共感', 'アドバイス', '聞いてほしい')"
      },
      "ai_response": "string (★上記すべてを統合した、非常に優しく共感的な応答)"
    }
    """
    prompt = f"""
    あなたはAIメンタルケア・パートナーです。
    ユーザーの話を深く共感し、受け止め、否定しません。
    会話履歴全体を考慮し、以下の「ユーザーの最新メッセージ」を分析し、
    JSONスキーマに従って応答してください。

    JSONスキーマ:
    ```json
    {json_schema}
    ```
    ---
    ユーザーの最新メッセージ:
    "{user_message}"
    """
    return prompt

# --- 6. Flaskルート (チャット処理) ---
@app.route('/chat', methods=['POST'])
def handle_chat():
    try:
        data = request.json
        user_message = data.get('message')
        if not user_message:
            return jsonify({"error": "メッセージがありません。"}), 400

        # 1. ★ Firestore から現在の履歴を読み込む
        doc = history_doc_ref.get()
        if doc.exists:
            chat_history = doc.to_dict().get("history", [])
        else:
            chat_history = []
        
        # 2. プロンプトを作成し、送信リストを準備
        full_prompt_for_this_turn = get_mental_care_prompt(user_message)
        contents_to_send = chat_history + [
            {"role": "user", "parts": [full_prompt_for_this_turn]}
        ]

        # 3. APIを呼び出す
        response = model.generate_content(contents_to_send)
        response_data = json.loads(response.text)
        
        ai_message = response_data.get("ai_response")
        analysis_data = response_data

        if not ai_message:
            raise ValueError(f"AIが適切なJSONを返しませんでした。 Raw: {response.text}")

        # 4. ★ Firestore に履歴を保存 (更新)
        #    (注: `chat_history` はPythonリストなので、直接は使えない)
        #    Firestoreの配列に「追加」するトランザクション
        @firestore.transactional
        def update_history_in_transaction(transaction, doc_ref, user_msg, ai_msg):
            doc = doc_ref.get(transaction=transaction)
            current_history = doc.to_dict().get("history", []) if doc.exists else []
            
            current_history.append({"role": "user", "parts": [user_msg]})
            current_history.append({"role": "model", "parts": [ai_msg]})
            
            # (オプション) 履歴が長くなりすぎたら古いものから削除 (例: 50件まで)
            if len(current_history) > 50:
                current_history = current_history[-50:]

            if doc.exists:
                transaction.update(doc_ref, {"history": current_history})
            else:
                transaction.set(doc_ref, {"history": current_history})

        transaction = db.transaction()
        update_history_in_transaction(transaction, history_doc_ref, user_message, ai_message)
        print("--- Firestore の履歴を更新しました ---")


        # 5. フロントエンドにJSONを返す
        return jsonify({
            "ai_message": ai_message,
            "emotion_parameters": analysis_data
        })

    except Exception as e:
        # (エラーハンドリングは省略...)
        print(f"!!! エラーが発生しました: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)

