import os
import google.generativeai as genai
from flask import Flask
from dotenv import load_dotenv

# .envファイルからAPIキーを読み込む
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

# APIキーの読み込みチェック
if api_key:
    print(f"OK: .envからAPIキー読み込み成功 (末尾5文字: ...{api_key[-5:]})")
else:
    print("エラー: .envからGEMINI_API_KEYが読み込めませんでした。")
    exit() # キーがなければここで終了

# Gemini設定
genai.configure(api_key=api_key)
# ★★★ テストのため、一番確実な 'gemini-pro' (1.0) を使います ★★★
try:
    model = genai.GenerativeModel('gemini-2.5-flash')
except Exception as e:
    print(f"モデルの初期化でエラー: {e}")
    exit()

# Flaskアプリの初期化
app = Flask(__name__)

# --- テスト1：サーバーが動いているか確認するルート ---
@app.route('/')
def index():
    # ブラウザで http://127.0.0.1:5000/ にアクセスするとこれが表示される
    return "<h1>Flaskサーバーは正常に動いています！</h1>"

# --- テスト2：Gemini APIが動いているか確認するルート ---
@app.route('/test')
def test_gemini():
    try:
        # ブラウザで http://127.0.0.1:5000/test にアクセスするとこれが動く
        print(".../test ルートが呼ばれました。Geminiにリクエストを送信します...")
        
        # 一番簡単なテキスト生成を実行
        response = model.generate_content("1+1は？")
        
        print(f"Geminiからの応答: {response.text}")
        
        # 応答をそのままブラウザに表示
        return f"<h2>Geminiからの応答:</h2><pre>{response.text}</pre>"
    
    except Exception as e:
        # エラーが起きたら、エラー内容をブラウザに表示
        print(f"!!! APIリクエストでエラーが発生: {e}")
        return f"<h1>APIリクエストでエラーが発生しました</h1><pre>{e}</pre>"

if __name__ == '__main__':
    app.run(debug=True, port=5000)
