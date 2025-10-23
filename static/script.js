// DOM要素の取得
const chatLog = document.getElementById('chat-log');
const chatForm = document.getElementById('chat-form');
const userInput = document.getElementById('user-input');
const emotionDisplay = document.getElementById('emotion-display');

// フォームが送信されたときの処理
chatForm.addEventListener('submit', async (event) => {
    event.preventDefault(); // フォームのデフォルトの送信動作をキャンセル

    const userMessage = userInput.value;
    if (!userMessage) return; // メッセージが空なら何もしない

    // ユーザーのメッセージをチャットログに追加
    appendMessage(userMessage, 'user');

    // 入力欄をクリア
    userInput.value = '';

    try {
        // Flaskサーバーの/chatエンドポイントにリクエストを送信
        const response = await fetch('http://127.0.0.1:5000/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ message: userMessage }),
        });

        if (!response.ok) {
            // サーバーがエラーを返した場合
            throw new Error(`サーバーエラー: ${response.status}`);
        }

        // サーバーからのJSON応答を解析
        const data = await response.json();

        // AIの応答をチャットログに追加
        appendMessage(data.ai_message, 'ai');

        // 感情パラメータを専用エリアに表示
        // JSON.stringifyの第3引数「2」は、見やすくインデントするための設定
        emotionDisplay.querySelector('pre').textContent = 
            JSON.stringify(data.emotion_parameters, null, 2);

    } catch (error) {
        // エラーが発生した場合
        console.error('通信エラー:', error);
        appendMessage('エラーが発生しました。サーバーが起動しているか確認してください。', 'ai');
        emotionDisplay.querySelector('pre').textContent = `エラー: ${error.message}`;
    }
});

// メッセージをチャットログに追加する関数
function appendMessage(message, sender) {
    const messageElement = document.createElement('div');
    messageElement.classList.add('message');
    
    if (sender === 'user') {
        messageElement.classList.add('user-message');
    } else {
        messageElement.classList.add('ai-message');
    }
    
    messageElement.textContent = message;
    chatLog.appendChild(messageElement);

    // 自動で一番下にスクロール
    chatLog.scrollTop = chatLog.scrollHeight;
}